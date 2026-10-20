"""Restoration/launcher failure gates, without downloads, subprocesses or capture."""
from contextlib import redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fetch_mediapipe_model as fetch


ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('local_pose_launcher',ROOT/'scripts/run-local-pose.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


class OptionalToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.video=self.root/'test.mp4';self.video.write_bytes(b'explicit file')
        python=self.root/'.toolchain/mediapipe-venv/bin/python';python.parent.mkdir(parents=True);python.write_text('not executed')
        self.payload=b'pinned-model'
        self.pin={'path':'models/pose_landmarker_full.task','url':fetch.MODEL_URL,'bytes':len(self.payload),
                  'sha256':hashlib.sha256(self.payload).hexdigest()}
        self.write_pin()

    def write_pin(self):
        (self.root/'mediapipe-full.lock.json').write_text(json.dumps({'model':self.pin}))

    def launch(self,args):
        with mock.patch.object(launcher.sys,'platform','darwin'),mock.patch.object(launcher.shutil,'which',return_value='/usr/bin/sandbox-exec'):
            return launcher.command(args,root=self.root)[1]

    def test_launcher_enforces_sandbox_and_cannot_forward_camera_mode(self):
        with mock.patch.object(launcher.sys,'platform','linux'),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):launcher.command(['replay',str(self.video)],root=self.root)
        for args in (['camera',str(self.video)],['replay',str(self.video),'--camera','0'],
                     ['verify',str(self.video)],['replay',str(self.video),'--seconds','1'],['replay',str(self.root)]):
            with self.subTest(args=args),redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):self.launch(args)

    def test_launcher_explicit_video_and_selected_backend(self):
        cmd=self.launch(['replay',str(self.video)])
        self.assertEqual(cmd[0],'/usr/bin/sandbox-exec')
        self.assertIn(str(self.root/'sidecar/local-model.sb'),cmd)
        self.assertIn('--video',cmd);self.assertIn(str(self.video.resolve()),cmd)
        self.assertEqual(cmd[cmd.index('--pose-backend')+1],'mediapipe-full')
        self.assertNotIn('--camera',cmd)

    def test_existing_matching_model_never_downloads(self):
        target=self.root/self.pin['path'];target.parent.mkdir();target.write_bytes(self.payload)
        with mock.patch.object(fetch.urllib.request,'urlopen') as network:
            fetch.restore(self.root);network.assert_not_called()

    def test_existing_mismatch_is_preserved_without_download(self):
        target=self.root/self.pin['path'];target.parent.mkdir();target.write_bytes(b'preserve')
        with mock.patch.object(fetch.urllib.request,'urlopen') as network:
            with self.assertRaisesRegex(ValueError,'refusing to overwrite'):fetch.restore(self.root)
            network.assert_not_called();self.assertEqual(target.read_bytes(),b'preserve')

    def test_only_official_expected_location_can_download(self):
        for field,value in (('url','https://example.org/model.task'),('path','../escape.task')):
            original=self.pin[field];self.pin[field]=value;self.write_pin()
            with mock.patch.object(fetch.urllib.request,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'Unexpected'):fetch.restore(self.root)
                network.assert_not_called()
            self.pin[field]=original

    def test_download_corruption_rejected_before_any_model_is_installed(self):
        for payload in (b'short',self.payload+b'extra'):
            response=io.BytesIO(payload);response.geturl=lambda:fetch.MODEL_URL
            with mock.patch.object(fetch.urllib.request,'urlopen',return_value=response):
                with self.assertRaisesRegex(ValueError,'does not match'):fetch.restore(self.root)
            self.assertFalse((self.root/self.pin['path']).exists())

    def test_verified_payload_is_restored_exactly(self):
        response=io.BytesIO(self.payload);response.geturl=lambda:fetch.MODEL_URL
        with mock.patch.object(fetch.urllib.request,'urlopen',return_value=response):fetch.restore(self.root)
        self.assertEqual((self.root/self.pin['path']).read_bytes(),self.payload)


if __name__=='__main__':unittest.main()
