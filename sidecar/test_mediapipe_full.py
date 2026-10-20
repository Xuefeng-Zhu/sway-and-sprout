"""Mapping, confidence and lifecycle contracts without optional packages/capture."""
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from mediapipe_full import MediaPipeFullPose
from pose_backend import create_pose
import run
import verify_video


def landmark(x=.5, y=.5, visibility=.9, presence=.8):
    return NS(x=x, y=y, visibility=visibility, presence=presence)


class FullPoseTests(unittest.TestCase):
    def setUp(self):
        self.points = [landmark() for _ in range(33)]
        self.graph = mock.Mock()
        self.graph.detect.return_value = NS(pose_landmarks=[self.points])
        self.pose = MediaPipeFullPose.__new__(MediaPipeFullPose)
        self.pose.threshold = .65
        self.pose.landmarker = self.graph
        self.pose.cv = NS(COLOR_BGR2RGB=4, cvtColor=lambda frame, _: frame)
        self.pose.mp = NS(ImageFormat=NS(SRGB=1), Image=lambda **kw: kw)
        self.frame = NS(shape=(360, 640, 3))

    def test_anatomical_mapping_top_left_pixels_and_minimum(self):
        for index, x, y in ((11,.2,.3),(12,.8,.4),(15,.1,.1),(16,.9,.9)):
            self.points[index] = landmark(x,y,.7,.95)
        observation,status,_ = self.pose.infer(self.frame)
        self.assertEqual(status,"tracking")
        self.assertEqual(observation.confidence,.65)
        self.assertAlmostEqual(observation.left_shoulder.x,128)
        self.assertAlmostEqual(observation.right_shoulder.y,144)
        self.assertAlmostEqual(observation.left_wrist.y,36)
        self.assertAlmostEqual(observation.right_wrist.x,576)
        self.assertEqual(observation.left_wrist.confidence,.7)

    def test_nan_presence_cannot_hide_behind_finite_visibility(self):
        self.points[15] = landmark(presence=float("nan"))
        obs,_,_ = self.pose.infer(self.frame)
        self.assertEqual(obs.left_wrist.confidence,0)

    def test_invalid_values_are_not_usable_landmarks(self):
        for field,value in (("x",-0.01),("x",1),("y",float("inf")),
                            ("presence",1.01),("visibility",-.1),("presence",None)):
            with self.subTest(field=field,value=value):
                p=landmark();setattr(p,field,value);self.points[15]=p
                obs,_,_ = self.pose.infer(self.frame)
                self.assertEqual(obs.left_wrist.confidence,0)

    def test_zero_multiple_or_malformed_poses_are_rejected(self):
        for poses,status in (([],"no-person"),([self.points,self.points],"low-confidence"),
                             ([self.points[:32]],"low-confidence")):
            self.graph.detect.return_value=NS(pose_landmarks=poses)
            obs,actual,_=self.pose.infer(self.frame)
            self.assertIsNone(obs);self.assertEqual(actual,status)

    def test_stateless_detect_and_idempotent_close(self):
        self.pose.infer(self.frame);self.pose.infer(self.frame)
        self.assertEqual(self.graph.detect.call_count,2)
        self.graph.detect_for_video.assert_not_called()
        self.pose.close();self.pose.close();self.graph.close.assert_called_once()

    def test_model_pin_is_checked_before_optional_dependency_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'bad.task').write_bytes(b'changed')
            (root/'mediapipe-full.lock.json').write_text(json.dumps({'model':{
                'path':'bad.task','bytes':7,'sha256':'0'*64}}))
            with mock.patch('mediapipe_full.ROOT',root), mock.patch.dict(sys.modules,{'mediapipe':None}):
                with self.assertRaisesRegex(RuntimeError,'bytes/SHA256'):
                    MediaPipeFullPose()

    def test_pinned_cpu_image_options_and_honest_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=b'verified';(root/'full.task').write_bytes(data)
            pin={'model':{'path':'full.task','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},
                 'packages':{'mediapipe':'1.1.1','opencv':'5.0.0','numpy':'2.5.4'},
                 'runningMode':'IMAGE','delegate':'CPU','admissionThreshold':.65}
            (root/'mediapipe-full.lock.json').write_text(json.dumps(pin))
            opts=mock.Mock(side_effect=lambda **kw:kw);base=mock.Mock(side_effect=lambda **kw:kw)
            base.Delegate=NS(CPU='cpu')
            mp=NS(__version__='1.1.1',tasks=NS(BaseOptions=base,vision=NS(
                PoseLandmarkerOptions=opts,RunningMode=NS(IMAGE='image'),
                PoseLandmarker=NS(create_from_options=mock.Mock(return_value=self.graph)))))
            cv=NS(__version__='5.0.0',setNumThreads=mock.Mock());np=NS(__version__='2.5.4')
            with mock.patch('mediapipe_full.ROOT',root),mock.patch.dict(sys.modules,{'cv2':cv,'numpy':np,'mediapipe':mp}):
                pose=MediaPipeFullPose();options=opts.call_args.kwargs
                self.assertEqual(options['num_poses'],2)
                self.assertEqual(options['running_mode'],'image')
                self.assertEqual(base.call_args.kwargs['model_asset_buffer'],data)
                for key in ('min_pose_detection_confidence','min_pose_presence_confidence','min_tracking_confidence'):
                    self.assertEqual(options[key],.65)
                self.assertNotIn('zooCommit',pose.runtime)
                self.assertIn('lower bound',pose.runtime['confidenceMeaning'])
                pose.close()
                mp.__version__='changed'
                with self.assertRaisesRegex(RuntimeError,'separate lock'):
                    MediaPipeFullPose()

    def test_default_factory_keeps_optional_import_lazy(self):
        with mock.patch('pose_backend.OpenCVPose',return_value='default') as factory:
            with mock.patch.dict(sys.modules,{'mediapipe_full':None}):
                self.assertEqual(create_pose(),'default');factory.assert_called_once()
        with self.assertRaisesRegex(ValueError,'Unknown'):
            create_pose('not-a-backend')

    def test_optional_backend_rejects_nonvideo_modes_before_initialization(self):
        for mode in ('--synthetic','--verify','--camera','--camera-smoke'):
            argv=['run.py',mode]+(['0'] if mode in ('--camera','--camera-smoke') else [])
            argv += ['--pose-backend','mediapipe-full']
            with self.subTest(mode=mode),mock.patch.object(sys,'argv',argv),redirect_stderr(io.StringIO()):
                with mock.patch('run.create_pose') as full,mock.patch('run.OpenCVPose') as default:
                    with self.assertRaises(SystemExit) as error:run.main()
                    self.assertEqual(error.exception.code,2);full.assert_not_called();default.assert_not_called()

    def test_invalid_local_file_rejected_before_native_graph(self):
        with tempfile.TemporaryDirectory() as tmp,mock.patch('verify_video.create_pose') as factory:
            with self.assertRaises(ValueError):
                verify_video.verify(tmp,pose_backend='mediapipe-full')
            factory.assert_not_called()

    def test_verifier_selected_factory_is_closed_on_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'mock.mp4';path.write_bytes(b'not decoded in this test')
            for failure in (False,True):
                pose=mock.Mock()
                with mock.patch('verify_video.create_pose',return_value=pose) as factory, \
                     mock.patch('verify_video._verify_with_pose',side_effect=ValueError('decode failed') if failure else None,return_value='report'):
                    if failure:
                        with self.assertRaisesRegex(ValueError,'decode failed'):
                            verify_video.verify(path,pose_backend='mediapipe-full')
                    else:
                        self.assertEqual(verify_video.verify(path,pose_backend='mediapipe-full'),'report')
                    factory.assert_called_once_with('mediapipe-full');pose.close.assert_called_once()

    def test_startup_output_failure_stops_worker_before_graph_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/'mock.mp4';video.write_bytes(b'not decoded')
            pose=mock.Mock(runtime={});worker=mock.Mock();stop=mock.Mock();server=mock.Mock()
            order=mock.Mock();order.attach_mock(worker.join,'join');order.attach_mock(pose.close,'close')
            argv=['run.py','--video',str(video),'--pose-backend','mediapipe-full']
            with mock.patch.object(sys,'argv',argv),mock.patch('run.create_pose',return_value=pose), \
                 mock.patch('run.threading.Thread',return_value=worker),mock.patch('run.threading.Event',return_value=stop), \
                 mock.patch('run.make_server',return_value=server),mock.patch('run.signal.signal'), \
                 mock.patch('builtins.print',side_effect=[BrokenPipeError('closed output'),None]):
                with self.assertRaises(SystemExit):run.main()
            stop.set.assert_called_once();server.server_close.assert_called_once()
            self.assertEqual(order.mock_calls,[mock.call.join(timeout=None),mock.call.close()])


if __name__=='__main__':
    unittest.main()
