"""Diagnostic CLI/guard regressions; fake frames only, no model or camera use."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import service
from motion import synthetic_observation
import verify_video
import video_input

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyze-video-motion.py"
spec = importlib.util.spec_from_file_location("analyze_video_motion_cli", SCRIPT)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def scored():
    return {"target": 6, "count": 0, "completed": False, "acceptedGestures": [], "lastSeq": 0}


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.video = self.root / "fixture.mp4"
        self.video.write_bytes(b"fake fixture bytes, never decoded")
        self.manifest = self.root / "partial.json"
        self.manifest.write_text(json.dumps({"sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
                                             "expectedGestures": None, "naturalContinuousMovement": True}))
        self.output = self.root / "outputs-not-yet-created"
        self.argv = ["--project", str(self.root), "--video", str(self.video),
                     "--annotation", str(self.manifest), "--output", str(self.output)]


class DiagnosticTests(FixtureCase):
    def test_capture_guard_accepts_only_exact_file_and_backend_and_restores_constructor(self):
        original = mock.Mock(return_value="capture-sentinel")
        cv = SimpleNamespace(VideoCapture=original, CAP_FFMPEG=1900)
        attempts, opened = {"capture": 0, "socket": 0}, []
        other = self.root / "other.mp4"
        other.write_bytes(b"another file")
        with diagnostic.restricted_io(cv, self.video.resolve(), attempts, opened):
            self.assertEqual(cv.VideoCapture(str(self.video), 1900), "capture-sentinel")
            for value, backend in ((0, 1900), (str(other), 1900), (str(self.video), 0),
                                   ("https://example.invalid/video.mp4", 1900), (self.video, 1900)):
                with self.subTest(value=value), self.assertRaises(AssertionError):
                    cv.VideoCapture(value, backend)
        self.assertIs(cv.VideoCapture, original)
        original.assert_called_once_with(str(self.video), 1900)
        self.assertEqual(attempts, {"capture": 5, "socket": 0})
        self.assertEqual(opened, [{"kind": "local-file", "backend": "CAP_FFMPEG"}])

    def test_sockets_are_blocked_and_restored_even_when_scope_raises(self):
        original_socket, original_connection = socket.socket, socket.create_connection
        attempts = {"capture": 0, "socket": 0}
        cv = SimpleNamespace(VideoCapture=mock.Mock(), CAP_FFMPEG=1900)
        with self.assertRaisesRegex(RuntimeError, "sentinel"):
            with diagnostic.restricted_io(cv, self.video.resolve(), attempts, []):
                for call in (lambda: socket.socket(), lambda: socket.create_connection(("127.0.0.1", 8765))):
                    with self.assertRaises(AssertionError):
                        call()
                raise RuntimeError("sentinel")
        self.assertIs(socket.socket, original_socket)
        self.assertIs(socket.create_connection, original_connection)
        self.assertEqual(attempts["socket"], 2)

    def test_wrong_fixture_hash_fails_before_inference_or_creating_output_directory(self):
        self.video.write_bytes(b"same filename, different content")
        modules = SimpleNamespace(load_manifest=verify_video.load_manifest)
        with mock.patch.object(diagnostic, "load_project", return_value=modules), \
             mock.patch.object(diagnostic, "analyze_bound_video") as analyze, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                diagnostic.main(self.argv)
        self.assertEqual(raised.exception.code, 2)
        analyze.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_manifest_is_required_and_time_bound_is_checked_before_project_import(self):
        for seconds in ("0", "-1", "30.1", "nan", "inf"):
            with self.subTest(seconds=seconds), mock.patch.object(diagnostic, "load_project") as load, \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    diagnostic.main(self.argv + ["--seconds", seconds])
                self.assertEqual(raised.exception.code, 2)
                load.assert_not_called()
        without_manifest = self.argv[:4] + self.argv[6:]
        with mock.patch.object(diagnostic, "load_project") as load, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                diagnostic.main(without_manifest)
            load.assert_not_called()

    def test_valid_partial_binding_precedes_analysis_and_keeps_incomplete_goal_explicit(self):
        manifest = mock.Mock(side_effect=verify_video.load_manifest)
        modules = SimpleNamespace(load_manifest=manifest)

        def analyze(project, video, binding, seconds, selected):
            manifest.assert_called_once()
            self.assertEqual(binding["kind"], "partial-annotation")
            self.assertIsNone(binding["expectedGestures"])
            self.assertIs(selected, modules)
            summary = {"fixture": {"file": video.name}, "gateCounts": {},
                       "minimumObservedConfidence": None, "observedGestures": [], "game": scored(),
                       "gameScoringMatches": True, "gameAcknowledgmentMatches": True,
                       "eventTimingPassed": None,
                       "verificationOutcome": {"status": "observed-only", "completeGoalVerified": False},
                       "blockedApiAttempts": {"capture": 0, "socket": 0}, "physicalCameraUsed": False,
                       "savedOutputFrames": 0, "uploadedFrames": 0}
            return {"summary": summary, "frames": []}

        with mock.patch.object(diagnostic, "load_project", return_value=modules), \
             mock.patch.object(diagnostic, "analyze_bound_video", side_effect=analyze), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(diagnostic.main(self.argv + ["--require-complete-goal"]), 1)
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertFalse(summary["verificationOutcome"]["completeGoalVerified"])
        self.assertEqual(summary["verificationOutcome"]["status"], "observed-only")

    def test_intervals_do_not_mislabel_frame_coverage_as_observed_neutral_span(self):
        spans = diagnostic.intervals([True, True, True, False, True], bool, 30)
        self.assertEqual(spans[0]["endFrameExclusive"], 3)
        self.assertEqual(spans[0]["observedSpanMs"], 66.667)
        self.assertEqual(spans[0]["sampledCoverageMs"], 100)
        self.assertEqual(spans[1]["observedSpanMs"], 0)
        self.assertEqual(spans[1]["sampledCoverageMs"], 33.333)

    def test_nonfinite_values_become_explicit_null_in_standard_json(self):
        result = diagnostic.json_safe({"confidence": float("nan"), "roi": [float("inf"), 2.0]})
        self.assertEqual(result, {"confidence": None, "roi": [None, 2.0]})
        json.dumps(result, allow_nan=False)


class StubCapture:
    def __init__(self):
        self.reads = 0
        self.released = False

    def isOpened(self):
        return True

    def get(self, unused):
        return 30

    def read(self):
        self.reads += 1
        return True, object()  # No image pixels, camera or decoding.

    def release(self):
        self.released = True


class StubPose:
    runtime = {"opencv": "5.0.0", "verified": True}

    def __init__(self):
        self.detector = SimpleNamespace(infer=lambda frame: [])
        self.pose = SimpleNamespace(_preprocess=lambda frame, person: None)

    def infer(self, frame):
        self.detector.infer(frame)
        return None, "no-person", 1.2


class FullTraceGuardTests(FixtureCase):
    def test_bounded_fake_pipeline_releases_capture_and_scores_actual_service_packets(self):
        cap = StubCapture()
        cv = SimpleNamespace(VideoCapture=mock.Mock(return_value=cap), CAP_FFMPEG=1900, CAP_PROP_FPS=5)
        modules = SimpleNamespace(OpenCVPose=StubPose, MotionService=service.MotionService,
                                  open_video=video_input.open_video, wrist_gates=video_input.wrist_gates,
                                  game_scoring_matches=verify_video.game_scoring_matches,
                                  verification_outcome=verify_video.verification_outcome,
                                  evaluate_event_windows=verify_video.evaluate_event_windows)
        binding = verify_video.load_manifest(self.manifest, self.video, partial=True)
        binding.update({"expectedGestures": [], "eventWindows": []})  # Independently bounded negative-control contract.
        project = Path(service.__file__).resolve().parent.parent
        with mock.patch.dict(sys.modules, {"cv2": cv}), \
             mock.patch.object(diagnostic, "score_packets", return_value=scored()) as score:
            report = diagnostic.analyze_bound_video(project, self.video.resolve(), binding, .1, modules)
        self.assertEqual(cap.reads, 3)
        self.assertTrue(cap.released)
        self.assertEqual(len(report["frames"]), 3)
        self.assertEqual(report["summary"]["inferenceFailureStageCounts"], {"no-detection": 3})
        self.assertEqual(report["summary"]["blockedApiAttempts"], {"capture": 0, "socket": 0})
        self.assertTrue(report["summary"]["gameAcknowledgmentMatches"])
        self.assertTrue(report["summary"]["eventTimingPassed"])
        self.assertEqual(report["summary"]["verificationOutcome"]["status"], "negative-control-matched")
        self.assertFalse(report["summary"]["verificationOutcome"]["completeGoalVerified"])
        self.assertEqual(report["summary"]["savedOutputFrames"], 0)
        self.assertEqual(len(score.call_args.args[1]), 3)

    def test_temporal_window_failure_reaches_outcome_even_when_sequence_and_scoring_match(self):
        class RaisePose(StubPose):
            def __init__(self):
                super().__init__()
                self.index = 0

            def infer(self, frame):
                self.detector.infer(frame)
                observation = synthetic_observation("neutral" if self.index < 4 else "left")
                self.index += 1
                return observation, "tracking", 1.2

        cap = StubCapture()
        cap.get = lambda unused: 10
        cv = SimpleNamespace(VideoCapture=mock.Mock(return_value=cap), CAP_FFMPEG=1900, CAP_PROP_FPS=5)
        modules = SimpleNamespace(OpenCVPose=RaisePose, MotionService=service.MotionService,
                                  open_video=video_input.open_video, wrist_gates=video_input.wrist_gates,
                                  game_scoring_matches=verify_video.game_scoring_matches,
                                  verification_outcome=verify_video.verification_outcome,
                                  evaluate_event_windows=verify_video.evaluate_event_windows)
        self.manifest.write_text(json.dumps({"sha256": hashlib.sha256(self.video.read_bytes()).hexdigest(),
            "expectedGestures": ["left-raise"], "eventWindows": [{"gesture": "left-raise", "startMs": 0, "endMs": 100}]}))
        binding = verify_video.load_manifest(self.manifest, self.video)
        result = {"target": 6, "count": 1, "completed": False, "acceptedGestures": ["left-raise"], "lastSeq": 1}
        project = Path(service.__file__).resolve().parent.parent
        with mock.patch.dict(sys.modules, {"cv2": cv}), mock.patch.object(diagnostic, "score_packets", return_value=result):
            report = diagnostic.analyze_bound_video(project, self.video.resolve(), binding, .9, modules)
        summary = report["summary"]
        self.assertEqual(summary["events"][0]["atVideoMs"], 800)
        self.assertTrue(summary["expectedSequencePassed"])
        self.assertTrue(summary["gameScoringMatches"])
        self.assertTrue(summary["gameAcknowledgmentMatches"])
        self.assertFalse(summary["eventTimingPassed"])
        self.assertEqual(summary["verificationOutcome"]["status"], "failed")

    def test_fixture_changed_during_decode_fails_after_cleanup_before_scoring(self):
        video = self.video
        class ChangingPose(StubPose):
            def infer(self, frame):
                video.write_bytes(b"fixture changed while being decoded")
                return super().infer(frame)

        cap = StubCapture()
        cv = SimpleNamespace(VideoCapture=mock.Mock(return_value=cap), CAP_FFMPEG=1900, CAP_PROP_FPS=5)
        modules = SimpleNamespace(OpenCVPose=ChangingPose, MotionService=service.MotionService,
                                  open_video=video_input.open_video, wrist_gates=video_input.wrist_gates)
        binding = verify_video.load_manifest(self.manifest, self.video, partial=True)
        with mock.patch.dict(sys.modules, {"cv2": cv}), \
             mock.patch.object(diagnostic, "score_packets") as score, \
             self.assertRaisesRegex(ValueError, "changed after manifest"):
            diagnostic.analyze_bound_video(self.root, self.video.resolve(), binding, .1, modules)
        self.assertTrue(cap.released)
        score.assert_not_called()

    def test_model_initialization_cannot_open_a_camera_before_decode(self):
        cv = SimpleNamespace(VideoCapture=mock.Mock(), CAP_FFMPEG=1900)
        def forbidden_pose():
            cv.VideoCapture(0)
        modules = SimpleNamespace(OpenCVPose=forbidden_pose)
        with mock.patch.dict(sys.modules, {"cv2": cv}), self.assertRaisesRegex(AssertionError, "manifest-bound"):
            diagnostic.analyze_bound_video(self.root, self.video.resolve(), {}, 1, modules)
        cv.VideoCapture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
