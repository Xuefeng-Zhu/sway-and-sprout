"""File/backend/preview separation tests; no physical camera or human frames."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import threading
import unittest
from unittest import mock

from motion import synthetic_observation
from service import MotionService
from video_input import open_video, video_worker, wrist_gates


CONTROL = dict(clientId="12345678-0000-4000-8000-000000000001",
               roundId="12345678-0000-4000-8000-000000000002",
               revision=0, active=True, mode="standing", after=0)


class VideoInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "public-fixture.mp4"
        self.path.write_bytes(b"fixture")

    def cv(self, fps=10, opened=True):
        capture = mock.Mock()
        capture.isOpened.return_value = opened
        capture.get.return_value = fps
        return SimpleNamespace(VideoCapture=mock.Mock(return_value=capture),
                               CAP_FFMPEG=1900, CAP_PROP_FPS=5, CAP_PROP_POS_FRAMES=1), capture

    def test_existing_file_uses_explicit_ffmpeg_not_device_backend(self):
        cv, capture = self.cv()
        actual, fps = open_video(self.path, cv)
        cv.VideoCapture.assert_called_once_with(str(self.path.resolve()), cv.CAP_FFMPEG)
        self.assertIs(actual, capture)
        self.assertEqual(fps, 10)

    def test_device_numbers_urls_directories_and_empty_files_never_open_capture(self):
        cv, _ = self.cv()
        empty = self.path.with_name("empty.mp4")
        empty.write_bytes(b"")
        for path in (0, "https://example.invalid/video.mp4", self.path.parent, empty):
            with self.subTest(path=str(path)), self.assertRaises((TypeError, ValueError, FileNotFoundError)):
                open_video(path, cv)
        cv.VideoCapture.assert_not_called()

    def test_invalid_decode_or_timing_releases_file(self):
        for fps, opened in ((0, True), (float("nan"), True), (121, True), (10, False)):
            with self.subTest(fps=fps, opened=opened):
                cv, capture = self.cv(fps, opened)
                with self.assertRaises(ValueError):
                    open_video(self.path, cv)
                capture.release.assert_called_once()

    def test_inactive_worker_never_opens_file_or_camera(self):
        stop = threading.Event()
        cv, _ = self.cv()
        service = MotionService({"opencv": "5.0.0", "verified": True}, "video", clock=lambda: 0)
        service.poll({**CONTROL, "active": False})
        with mock.patch.object(stop, "wait", side_effect=lambda *_: stop.set()):
            video_worker(service, SimpleNamespace(cv=cv), stop, self.path)
        cv.VideoCapture.assert_not_called()
        self.assertTrue(service.stopped)

    def test_worker_uses_one_file_and_same_frame_inference_preview_then_clears(self):
        cv, capture = self.cv()
        frames = [object(), object(), object()]
        capture.read.side_effect = [(True, frame) for frame in frames]
        stop, seen = threading.Event(), []
        service = MotionService({"opencv": "5.0.0", "verified": True}, "video", clock=lambda: 0)
        service.poll(CONTROL)

        def infer(frame):
            seen.append(frame)
            return synthetic_observation(), "tracking", .1

        def preview(frame, observation, status):
            self.assertIs(frame, seen[-1])
            if len(seen) == 3:
                stop.set()
            return {"jpeg": "data:image/jpeg;base64,aGk=", "width": 2, "height": 2,
                    "visibility": {k: True for k in ("leftShoulder", "rightShoulder", "leftWrist", "rightWrist")},
                    "confidence": 1.0}

        video_worker(service, SimpleNamespace(cv=cv, infer=infer, preview=preview), stop, self.path)
        cv.VideoCapture.assert_called_once_with(str(self.path.resolve()), cv.CAP_FFMPEG)
        self.assertEqual(seen, frames)
        self.assertEqual(service.metrics["frames"], 3)
        self.assertTrue(service.stopped)
        self.assertIsNone(service.latest_preview)
        capture.release.assert_called_once()

    def test_video_preview_keeps_source_authentication_and_no_camera_claim(self):
        service = MotionService({"opencv": "5.0.0", "verified": True}, "video", clock=lambda: 0)
        packet = service.poll(CONTROL)
        self.assertEqual(packet["source"], "video")
        self.assertEqual(packet["runtime"]["source"], "video")
        image = {"jpeg": "data:image/jpeg;base64,aGk=", "width": 2, "height": 2,
                 "visibility": {k: True for k in ("leftShoulder", "rightShoulder", "leftWrist", "rightWrist")},
                 "confidence": 1.0}
        self.assertTrue(service.publish_preview(service.token(), image, 0))
        preview = service.preview(CONTROL)
        self.assertTrue(preview["available"])
        self.assertEqual(preview["source"], "video")
        self.assertFalse(service.preview({**CONTROL, "revision": 1})["available"])
        service.poll({**CONTROL, "revision": 1, "active": False})
        self.assertIsNone(service.latest_preview)

    def test_scalar_gates_match_actual_classifier_geometry(self):
        service = MotionService({"opencv": "5.0.0", "verified": True}, "video", clock=lambda: 0)
        config = service.machine.config
        for side, expected in (("neutral", "left-down/right-down"),
                               ("left", "left-up/right-down"), ("right", "left-down/right-up")):
            self.assertEqual(wrist_gates(synthetic_observation(side), config), expected)
        self.assertEqual(wrist_gates(None, config), "no-pose")
        self.assertEqual(wrist_gates(synthetic_observation(confidence=.4), config), "low-confidence")


if __name__ == "__main__":
    unittest.main()
