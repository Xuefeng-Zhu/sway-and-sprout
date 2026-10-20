"""Generated fixtures only: no human images, real capture, or image files."""

import base64
from dataclasses import replace
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
from urllib.parse import urlencode
from uuid import UUID

from inference import OpenCVPose
from motion import Landmark, Observation
from run import camera_worker
from service import (MAX_PREVIEW_JPEG_BYTES, MAX_RESPONSE_BYTES, MotionService,
                     parse_control)
from test_service import control


def image_fixture():
    return {"jpeg": "data:image/jpeg;base64,/9j/2Q==", "width": 320, "height": 240,
            "visibility": {key: True for key in ("leftShoulder", "rightShoulder", "leftWrist", "rightWrist")},
            "confidence": .9}


def preview_target(item=None):
    fields = dict(item or control())
    fields["active"] = "1" if fields["active"] else "0"
    return "/motion/preview?" + urlencode(fields)


class PreviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = MotionService({"opencv": "5.0.0", "verified": True}, "camera",
                                     clock=lambda: self.now)
        self.service.poll(control())
        self.token = self.service.token()

    def publish(self):
        self.assertTrue(self.service.publish_preview(self.token, image_fixture(), self.now))

    def test_preview_never_starts_an_inactive_session(self):
        service = MotionService({}, "camera", clock=lambda: self.now)
        self.assertFalse(service.preview(control())["available"])
        self.assertIsNone(service.context)
        self.assertIsNone(service.token())
        self.assertEqual(service.last_poll, -float("inf"))
        self.assertFalse(service.publish_preview(None, image_fixture(), self.now))

    def test_exact_identity_echo_and_preview_does_not_ack_or_extend_lease(self):
        self.publish()
        before = (self.service.last_poll, self.service.seq, self.service.ack_seq,
                  self.service.machine.expected, self.service.machine.armed)
        self.now = 250
        packet = self.service.preview(control(after=999))
        self.assertTrue(packet["available"])
        self.assertEqual(packet["source"], "camera")
        for key in ("clientId", "roundId", "revision", "active", "mode"):
            self.assertEqual(packet[key], control()[key])
        self.assertEqual(before, (self.service.last_poll, self.service.seq, self.service.ack_seq,
                                 self.service.machine.expected, self.service.machine.armed))
        self.assertNotIn("capturedAt", packet)
        self.assertNotIn("token", packet)
        self.assertNotIn("landmarks", packet)

    def test_foreign_client_round_revision_mode_and_inactive_requests_have_no_image(self):
        self.publish()
        identity_changes = ({"clientId": str(UUID(int=42))}, {"roundId": str(UUID(int=43))},
                            {"revision": 1}, {"mode": "standing"}, {"active": False})
        for changed in identity_changes:
            with self.subTest(field=next(iter(changed))):
                packet = self.service.preview(control(**changed))
                self.assertFalse(packet["available"])
                self.assertNotIn("jpeg", packet)
        self.assertTrue(self.service.preview(control())["available"])

    def test_preview_stales_at_500ms_and_rejects_slow_frame_publication(self):
        self.publish()
        self.now = 500
        self.assertTrue(self.service.preview(control())["available"])
        self.now = 501
        packet = self.service.preview(control())
        self.assertFalse(packet["available"])
        self.assertEqual(packet["status"], "stale")
        self.assertIsNone(self.service.latest_preview)
        self.assertFalse(self.service.publish_preview(self.token, image_fixture(), 0))

    def test_repeated_previews_do_not_extend_capture_lease(self):
        for when in (250, 500, 1000, 1499):
            self.now = when
            self.service.preview(control())
        self.assertEqual(self.service.last_poll, 0)
        self.assertTrue(self.service.publish_preview(self.token, image_fixture(), self.now))
        self.now = 1501
        packet = self.service.preview(control())
        self.assertFalse(packet["available"])
        self.assertEqual(packet["status"], "expired")
        self.assertIsNone(self.service.latest_preview)
        self.assertIsNone(self.service.token())

    def test_pause_round_position_revision_and_client_changes_clear_cache(self):
        changes = ({"revision": 1, "active": False}, {"revision": 1},
                   {"revision": 1, "roundId": str(UUID(int=90))},
                   {"revision": 1, "mode": "standing"})
        for changed in changes:
            with self.subTest(change=changed):
                self.setUp()
                self.publish()
                self.service.poll(control(**changed))
                self.assertIsNone(self.service.latest_preview)
                self.assertFalse(self.service.publish_preview(self.token, image_fixture(), self.now))
        self.setUp()
        self.publish()
        self.now = 1501
        new = control(clientId=str(UUID(int=91)))
        self.service.poll(new)
        self.assertIsNone(self.service.latest_preview)
        self.assertFalse(self.service.preview(control())["available"])

    def test_idle_camera_error_and_stop_clear_cache(self):
        for action in (lambda: self.service.idle(),
                       lambda: self.service.camera_error("fixture failure"),
                       lambda: self.service.close()):
            self.setUp()
            self.publish()
            action()
            self.assertIsNone(self.service.latest_preview)
            self.assertFalse(self.service.preview(control())["available"])

    def test_synthetic_source_never_caches_or_returns_image(self):
        service = MotionService({}, "synthetic", clock=lambda: self.now)
        service.poll(control())
        self.assertFalse(service.publish_preview(service.token(), image_fixture(), self.now))
        packet = service.preview(control())
        self.assertFalse(packet["available"])
        self.assertEqual(packet["source"], "synthetic")
        self.assertEqual(packet["status"], "synthetic")
        self.assertNotIn("jpeg", packet)

    def test_bounded_dimensions_payload_and_metadata_fail_closed(self):
        changes = ({"jpeg": "data:image/jpeg;base64," + "A" * (210 * 1024)},
                   {"width": 321}, {"height": 641}, {"confidence": float("nan")},
                   {"visibility": {"leftWrist": True}}, {"jpeg": "data:image/png;base64,AAAA"})
        for changed in changes:
            with self.subTest(field=next(iter(changed))):
                image = dict(image_fixture(), **changed)
                self.assertFalse(self.service.publish_preview(self.token, image, self.now))
                self.assertIsNone(self.service.latest_preview)


class PreviewHTTPTests(unittest.TestCase):
    def setUp(self):
        from service import make_server
        self.now = 0
        self.service = MotionService({}, "camera", clock=lambda: self.now)
        self.service.poll(control())
        self.service.publish_preview(self.service.token(), image_fixture(), self.now)
        self.server = make_server(self.service, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_authorized_same_origin_preview_is_bounded_no_store_and_read_only(self):
        request = urllib.request.Request(self.base + preview_target(),
                                         headers={"Origin": "http://127.0.0.1:4173"})
        with patch.object(self.service, "poll", wraps=self.service.poll) as poll:
            with urllib.request.urlopen(request) as response:
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                data = response.read()
            poll.assert_not_called()
        self.assertLessEqual(len(data), MAX_RESPONSE_BYTES)
        self.assertTrue(json.loads(data)["available"])
        self.assertEqual(parse_control(preview_target()), control())

    def test_preview_enforces_query_origin_host_method_and_no_body(self):
        cases = [(preview_target() + "&extra=1", "GET", {}, None, 400),
                 (preview_target(), "GET", {"Origin": "https://foreign.invalid"}, None, 403),
                 (preview_target(), "GET", {"Host": "foreign.invalid"}, None, 403),
                 (preview_target(), "GET", {"Sec-Fetch-Site": "cross-site"}, None, 403),
                 (preview_target(), "POST", {}, None, 405),
                 (preview_target(), "GET", {}, b"x", 400)]
        for path, method, headers, body, status in cases:
            with self.subTest(status=status, method=method, headers=headers):
                request = urllib.request.Request(self.base + path, method=method,
                                                 headers=headers, data=body)
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, status)
                caught.exception.close()


class PreviewRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cv2
        import numpy
        cls.pipeline = OpenCVPose.__new__(OpenCVPose)
        cls.pipeline.cv, cls.pipeline.np = cv2, numpy

    def test_generated_large_frame_renders_aligned_markers_and_bounded_jpeg(self):
        pipeline, np, cv = self.pipeline, self.pipeline.np, self.pipeline.cv
        # Inference first normalizes a 1280px camera frame to 640px. These fixture
        # observations use that exact input space, as actual infer() does.
        frame = np.zeros((960, 1280, 3), np.uint8)
        observation = Observation(Landmark(400, 200, .9), Landmark(240, 200, .9),
                                  Landmark(400, 400, .9), Landmark(240, 400, .4), .9)
        preview = pipeline.preview(frame, observation, "tracking")
        self.assertEqual((preview["width"], preview["height"]), (320, 240))
        raw = base64.b64decode(preview["jpeg"].split(",", 1)[1], validate=True)
        self.assertLessEqual(len(raw), MAX_PREVIEW_JPEG_BYTES)
        decoded = cv.imdecode(np.frombuffer(raw, np.uint8), cv.IMREAD_COLOR)
        self.assertEqual(decoded.shape, (240, 320, 3))
        self.assertGreater(int(decoded[100, 200, 1]), 170)
        self.assertEqual(int(frame.sum()), 0)
        self.assertTrue(preview["visibility"]["leftShoulder"])
        self.assertFalse(preview["visibility"]["rightWrist"])
        self.assertEqual(preview["confidence"], .4)

    def test_no_person_frame_still_previews_without_fabricated_markers(self):
        pipeline = self.pipeline
        preview = pipeline.preview(pipeline.np.zeros((480, 640, 3), pipeline.np.uint8), None, "no-person")
        self.assertFalse(any(preview["visibility"].values()))
        self.assertEqual(preview["confidence"], 0)

    def test_encoding_failure_and_oversize_never_return_partial_preview(self):
        pipeline = self.pipeline
        frame = pipeline.np.zeros((20, 20, 3), pipeline.np.uint8)
        for output in ((False, None), (True, pipeline.np.empty(MAX_PREVIEW_JPEG_BYTES + 1, pipeline.np.uint8))):
            with patch.object(pipeline.cv, "imencode", return_value=output):
                with self.assertRaises(RuntimeError):
                    pipeline.preview(frame, None, "no-person")


class CameraWorkerPreviewTests(unittest.TestCase):
    def test_preview_uses_same_single_capture_and_stop_clears_it(self):
        service = MotionService({}, "camera", clock=lambda: 0)
        service.poll(control())
        stop = threading.Event()
        frame = object()
        observation = Observation(*[Landmark(10, 10)] * 4)
        cap = Mock()
        cap.isOpened.return_value = True

        def read_once():
            stop.set()
            return True, frame

        cap.read.side_effect = read_once
        cv = SimpleNamespace(VideoCapture=Mock(return_value=cap), CAP_AVFOUNDATION=1,
                             CAP_PROP_FRAME_WIDTH=2, CAP_PROP_FRAME_HEIGHT=3)
        pose = SimpleNamespace(cv=cv, infer=Mock(return_value=(observation, "tracking", 1)),
                               preview=Mock(return_value=image_fixture()))
        with patch.object(service, "publish_preview", wraps=service.publish_preview) as publish:
            camera_worker(service, pose, stop, 0)
            publish.assert_called_once()
        cv.VideoCapture.assert_called_once_with(0, cv.CAP_AVFOUNDATION)
        cap.read.assert_called_once()
        cap.release.assert_called_once()
        pose.infer.assert_called_once_with(frame)
        pose.preview.assert_called_once_with(frame, observation, "tracking")
        self.assertIsNone(service.latest_preview)
        self.assertIsNone(service.token())

    def test_pause_during_inference_rejects_its_late_preview(self):
        service = MotionService({}, "camera", clock=lambda: 0)
        service.poll(control())
        old_token = service.token()
        stop = threading.Event()
        frame = object()
        cap = Mock()
        cap.isOpened.return_value = True
        cap.read.return_value = (True, frame)

        def infer_with_pause(_):
            service.poll(control(revision=1, active=False))
            stop.set()
            return None, "no-person", 1

        cv = SimpleNamespace(VideoCapture=Mock(return_value=cap), CAP_AVFOUNDATION=1,
                             CAP_PROP_FRAME_WIDTH=2, CAP_PROP_FRAME_HEIGHT=3)
        pose = SimpleNamespace(cv=cv, infer=infer_with_pause,
                               preview=Mock(return_value=image_fixture()))
        accepted = []
        publish_original = service.publish_preview

        def publish(*args):
            result = publish_original(*args)
            accepted.append(result)
            return result

        with patch.object(service, "publish_preview", side_effect=publish):
            camera_worker(service, pose, stop, 0)
        self.assertEqual(accepted, [False])
        self.assertFalse(service.publish_preview(old_token, image_fixture(), 0))
        self.assertEqual(service.metrics["frames"], 0)
        self.assertIsNone(service.latest_preview)
        cap.read.assert_called_once()
        cap.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
