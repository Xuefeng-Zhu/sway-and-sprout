"""Fixture-boundary tests only: no OpenCV import, video decode or media access."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify-permitted-activity-video.py"
SPEC = importlib.util.spec_from_file_location("permitted_activity_evidence", SCRIPT)
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)


class FixtureBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "sidecar").mkdir()
        self.asset_root = self.root / "existing-assets"
        self.asset_root.mkdir()
        self.video = self.root / "synthetic-test-bytes.mp4"
        self.video.write_bytes(b"not media: synthetic pin-verification fixture")
        self.sha = hashlib.sha256(self.video.read_bytes()).hexdigest()
        asset = self.asset_root / "model.bin"
        asset.write_bytes(b"not a model: synthetic pin-verification fixture")
        lock = {"files": [{"path": "model.bin", "bytes": asset.stat().st_size,
                            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest()}]}
        for p in (self.root / "sidecar/models.lock.json", self.asset_root / "models.lock.json"):
            p.write_text(json.dumps(lock))
        self.expected = self.root / "expected.json"
        self.source = {"author": "Taco Fleur", "license": "CC BY-SA 4.0", "permissionConfirmation": "fixture-only"}
        self.expected.write_text(json.dumps({"sha256": self.sha, "bytes": self.video.stat().st_size, "source": self.source}))
        self.patch = patch.multiple(EVIDENCE, ROOT=self.root, EXPECTED=self.expected, VIDEO_SHA=self.sha,
                                    VIDEO_BYTES=self.video.stat().st_size, source_pins=lambda: {"fixture": "test-only"})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def validate(self):
        return EVIDENCE.validate_fixture(self.video, self.asset_root)

    def test_frozen_local_pins_preserve_unknown_activity_expectation(self):
        result = self.validate()
        self.assertFalse(result["activityExpectationKnown"])
        self.assertTrue(result["historicalStrictExpectationUnchanged"])
        self.assertEqual(result["source"]["license"], "CC BY-SA 4.0")

    def test_modified_or_unrelated_video_is_rejected(self):
        self.video.write_bytes(b"different media")
        with self.assertRaisesRegex(ValueError, "exact frozen"):
            self.validate()

    def test_missing_attribution_is_rejected(self):
        frozen = json.loads(self.expected.read_text())
        frozen["source"]["permissionConfirmation"] = ""
        self.expected.write_text(json.dumps(frozen))
        with self.assertRaisesRegex(ValueError, "attribution"):
            self.validate()

    def test_wrong_model_root_lock_is_rejected(self):
        (self.asset_root / "models.lock.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "different model lock"):
            self.validate()

    def test_modified_model_asset_is_rejected(self):
        (self.asset_root / "model.bin").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "asset mismatch"):
            self.validate()

    def test_path_escape_in_model_lock_is_rejected(self):
        lock = {"files": [{"path": "../outside.bin", "bytes": 1, "sha256": "0" * 64}]}
        for p in (self.root / "sidecar/models.lock.json", self.asset_root / "models.lock.json"):
            p.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, "Unsafe model path"):
            self.validate()

    def test_game_ipc_is_bounded_before_reading_a_missing_reply(self):
        adapter = EVIDENCE.GameAdapter.__new__(EVIDENCE.GameAdapter)
        adapter.process = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO())
        with patch.object(EVIDENCE.select, "select", return_value=([], [], [])):
            with self.assertRaisesRegex(TimeoutError, "three seconds"):
                adapter.request({"op": "context"})

    def test_partial_game_reply_is_bounded_without_waiting_for_newline(self):
        adapter = EVIDENCE.GameAdapter.__new__(EVIDENCE.GameAdapter)
        adapter.output_buffer = bytearray()
        incoming, outgoing, errors = Mock(), Mock(), Mock()
        adapter.process = SimpleNamespace(stdin=outgoing, stdout=incoming, stderr=errors)
        ready = [([], [outgoing], []), ([incoming], [], []), ([], [], [])]
        with patch.object(EVIDENCE.select, "select", side_effect=ready), \
                patch.object(EVIDENCE.os, "write", side_effect=lambda fd, value: len(value)), \
                patch.object(EVIDENCE.os, "read", return_value=b'{"partial":'):
            with self.assertRaisesRegex(TimeoutError, "three seconds"):
                adapter.request({"op": "context"})
        incoming.readline.assert_not_called()

    def test_broken_pipe_on_close_still_reaps_adapter(self):
        adapter = EVIDENCE.GameAdapter.__new__(EVIDENCE.GameAdapter)
        stdin, stdout, stderr = Mock(), Mock(), Mock()
        stdin.close.side_effect = BrokenPipeError()
        adapter.process = SimpleNamespace(stdin=stdin, stdout=stdout, stderr=stderr, wait=Mock(return_value=0))
        adapter.close()
        adapter.process.wait.assert_called_once_with(timeout=2)
        stdout.close.assert_called_once()
        stderr.close.assert_called_once()

    def test_capture_guard_only_allows_the_pinned_file_and_explicit_backend(self):
        calls = []
        cv = SimpleNamespace(CAP_FFMPEG=1900, VideoCapture=lambda *args: calls.append(args))
        guard = EVIDENCE.PrivacyGuards(self.video)
        guard.install_capture(cv)
        try:
            cv.VideoCapture(str(self.video), cv.CAP_FFMPEG)
            for source, backend in ((0, 1900), (str(self.video), 0), ('https://example.invalid/video', 1900)):
                with self.assertRaises(PermissionError):
                    cv.VideoCapture(source, backend)
        finally:
            guard.restore()
        self.assertEqual(len(calls), 1)
        self.assertEqual(guard.blocked_capture_calls, 3)

    def test_socket_guard_denies_creation_without_opening_a_socket(self):
        import socket
        guard = EVIDENCE.PrivacyGuards(self.video)
        guard.install_sockets()
        try:
            for operation in (socket.socket, socket.create_connection, socket.socketpair):
                with self.assertRaises(PermissionError):
                    operation()
        finally:
            guard.restore()
        self.assertEqual(guard.python_socket_attempts, 3)

    def test_initialization_failure_is_preserved_as_a_failed_artifact(self):
        fake = SimpleNamespace(OpenCVPose=lambda: (_ for _ in ()).throw(RuntimeError("fixture initialization failed")))
        versions = {"opencv-python-headless": "5.0.0.93", "numpy": "2.5.4"}
        cv = SimpleNamespace(CAP_FFMPEG=1900, VideoCapture=lambda *args: None)
        with patch.dict("sys.modules", {"inference": fake, "cv2": cv}), patch("importlib.metadata.version", side_effect=versions.__getitem__):
            result = EVIDENCE.run(self.validate(), self.root / "unused-node", 10)
        self.assertEqual(result["status"], "failed")
        self.assertIn("fixture initialization failed", result["error"])
        self.assertEqual(result["decodedFrames"], 0)
        self.assertTrue(result["gameAdapterStopped"])
        self.assertTrue(result["sourceUnchanged"])


if __name__ == "__main__":
    unittest.main()
