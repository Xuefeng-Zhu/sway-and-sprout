"""Verification outcome regressions only: mocked inference, no camera or video."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import verify_video


GESTURES = ["left-raise", "right-raise"] * 3


def game(count=6, **changes):
    return {"target": 6, "count": count, "completed": count == 6,
            "acceptedGestures": GESTURES[:count], "lastSeq": count, **changes}


class VerifyOutcomeTests(unittest.TestCase):
    def invoke(self, *, scored=None, expected_pass=True, ack=True, manifest=True, complete=False):
        scored = game() if scored is None else scored
        report = {"source": "video", "evidenceType": "mocked-outcome-only", "fixture": {},
                  "observedGestures": GESTURES, "expectedGestures": GESTURES if manifest else None,
                  "expectedSequencePassed": expected_pass if manifest else None,
                  "game": scored, "gameAcknowledgmentMatches": ack,
                  "gameScoringMatches": verify_video.game_scoring_matches(GESTURES, scored),
                  "armedTransitions": 6, "previewResponses": 0, "physicalCameraOpens": 0}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "scalar-report.json"
            expected = Path(directory) / "expected.json"
            video = Path(directory) / "not-decoded.mp4"
            video.write_bytes(b"mocked CLI fixture bytes; no decode")
            expected.write_text(json.dumps({"expectedGestures": GESTURES,
                                           "sha256": hashlib.sha256(video.read_bytes()).hexdigest()}))
            argv = ["verify_video.py", str(video), "--output", str(output)]
            if manifest:
                argv.extend(["--expected", str(expected)])
            if complete:
                argv.append("--require-complete-goal")
            with mock.patch.object(verify_video, "verify", return_value=report), \
                 mock.patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()):
                try:
                    verify_video.main()
                    code = 0
                except SystemExit as error:
                    code = error.code
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(output.read_text())["game"], scored)
            return code

    def test_game_rejection_fails_even_when_semantic_sequence_and_ack_match(self):
        self.assertEqual(self.invoke(scored=game(0, lastSeq=6)), 1)

    def test_game_ack_mismatch_fails_even_when_scoring_and_semantic_sequence_match(self):
        self.assertEqual(self.invoke(ack=False), 1)

    def test_bad_game_without_expected_manifest_cannot_exit_successfully(self):
        self.assertEqual(self.invoke(scored=game(0, lastSeq=6), manifest=False), 1)

    def test_model_expectation_failure_still_fails_with_correct_game_scoring(self):
        self.assertEqual(self.invoke(expected_pass=False), 1)

    def test_matching_semantics_game_and_ack_pass(self):
        self.assertEqual(self.invoke(), 0)

    def test_goal_gate_needs_independent_sequence_even_with_consistent_scoring(self):
        self.assertEqual(self.invoke(manifest=False), 0)  # Observations only.
        self.assertEqual(self.invoke(manifest=False, complete=True), 1)
        self.assertEqual(self.invoke(complete=True), 0)

    def test_partial_game_can_match_partial_observations_without_false_completion(self):
        self.assertTrue(verify_video.game_scoring_matches(GESTURES[:1], game(1)))
        self.assertFalse(verify_video.game_scoring_matches(GESTURES[:1], game(1, completed=True)))

    def test_game_count_accepted_side_and_target_are_checked_independently(self):
        for changes in ({"count": 0}, {"completed": False}, {"target": 5},
                        {"acceptedGestures": ["right-raise"] * 6}):
            with self.subTest(changes=changes):
                self.assertFalse(verify_video.game_scoring_matches(GESTURES, game(**changes)))

    def test_score_cap_matches_first_goal_but_extra_events_still_need_ack_consistency(self):
        self.assertTrue(verify_video.game_scoring_matches(GESTURES + ["left-raise"], game()))


class ExpectationBindingTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.video = Path(self.directory.name) / "same-name.mp4"
        self.video.write_bytes(b"reviewed fixture")
        self.manifest = Path(self.directory.name) / "expectation.json"
        self.digest = hashlib.sha256(self.video.read_bytes()).hexdigest()

    def write(self, **changes):
        value = {"sha256": self.digest, "expectedGestures": GESTURES, **changes}
        self.manifest.write_text(json.dumps(value))

    def test_selected_bytes_must_match_not_only_filename(self):
        self.write()
        self.video.write_bytes(b"a different fixture with same name")
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_video.load_manifest(self.manifest, self.video)

    def test_missing_or_invalid_digest_is_rejected(self):
        for digest in (None, "", "f" * 63, "z" * 64):
            with self.subTest(digest=digest):
                self.write(sha256=digest)
                with self.assertRaisesRegex(ValueError, "pin the fixture"):
                    verify_video.load_manifest(self.manifest, self.video)

    def test_binding_rejection_happens_before_inference(self):
        self.write(sha256="0" * 64)
        argv = ["verify_video.py", str(self.video), "--expected", str(self.manifest),
                "--output", str(Path(self.directory.name) / "result.json")]
        with mock.patch("sys.argv", argv), mock.patch.object(verify_video, "verify") as inference, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                verify_video.main()
        self.assertEqual(error.exception.code, 2)
        inference.assert_not_called()

    def test_partial_annotation_carries_no_invented_sequence(self):
        self.write(expectedGestures=None, naturalContinuousMovement=True)
        binding = verify_video.load_manifest(self.manifest, self.video, partial=True)
        self.assertIsNone(binding["expectedGestures"])
        self.assertEqual(binding["kind"], "partial-annotation")
        with self.assertRaisesRegex(ValueError, "explicit gesture list"):
            verify_video.load_manifest(self.manifest, self.video)

    def test_partial_annotation_cannot_smuggle_complete_expectations(self):
        self.write()
        with self.assertRaisesRegex(ValueError, "must not declare"):
            verify_video.load_manifest(self.manifest, self.video, partial=True)

    def test_observed_zero_is_not_complete_goal_verification(self):
        outcome = verify_video.verification_outcome({"gameScoringMatches": True,
            "gameAcknowledgmentMatches": True, "expectedGestures": None,
            "expectedSequencePassed": None, "game": game(0)})
        self.assertTrue(outcome["pipelineConsistent"])
        self.assertFalse(outcome["completeGoalVerified"])
        self.assertIsNone(outcome["expectedSequenceMatched"])
        self.assertEqual(outcome["status"], "observed-only")

    def test_explicit_empty_negative_control_does_not_verify_goal(self):
        outcome = verify_video.verification_outcome({"gameScoringMatches": True,
            "gameAcknowledgmentMatches": True, "expectedGestures": [],
            "expectedSequencePassed": True, "game": game(0)})
        self.assertEqual(outcome["status"], "negative-control-matched")
        self.assertFalse(outcome["completeGoalVerified"])


class EventWindowTests(unittest.TestCase):
    """Authored file-time windows; all inference/decode/scoring is mocked."""

    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.video = Path(self.directory.name) / "never-decoded.mp4"
        self.video.write_bytes(b"independently selected mock fixture")
        self.manifest = Path(self.directory.name) / "expected.json"
        self.output = Path(self.directory.name) / "result.json"
        self.digest = hashlib.sha256(self.video.read_bytes()).hexdigest()

    def write(self, expected=None, **fields):
        value = {"sha256": self.digest,
                 "expectedGestures": GESTURES if expected is None else expected, **fields}
        self.manifest.write_text(json.dumps(value))
        return value

    @staticmethod
    def window(gesture="left-raise", start=100, end=200):
        return {"gesture": gesture, "startMs": start, "endMs": end}

    def invoke(self, events, expected, *, seconds=30, complete=False, annotation=False):
        observed = [event["gesture"] for event in events]
        scored = {"target": 6, "count": min(len(observed), 6), "completed": len(observed) >= 6,
                  "acceptedGestures": observed[:6], "lastSeq": len(observed)}
        report = {"source": "video", "evidenceType": "mocked-outcome-only", "fixture": {},
                  "observedGestures": observed, "expectedGestures": expected,
                  "expectedSequencePassed": observed == expected if expected is not None else None,
                  "events": events, "game": scored, "gameAcknowledgmentMatches": True,
                  "gameScoringMatches": True, "armedTransitions": 0, "previewResponses": 0,
                  "physicalCameraOpens": 0}
        argv = ["verify_video.py", str(self.video), "--annotation" if annotation else "--expected",
                str(self.manifest), "--seconds", str(seconds), "--output", str(self.output)]
        if complete:
            argv.append("--require-complete-goal")
        with mock.patch.object(verify_video, "verify", return_value=report) as inference, \
             mock.patch.object(verify_video, "OpenCVPose", side_effect=AssertionError("DNN prohibited")) as pose, \
             mock.patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            try:
                verify_video.main()
                code = 0
            except SystemExit as error:
                code = error.code
        pose.assert_not_called()
        return code, inference, json.loads(self.output.read_text()) if self.output.exists() else None

    def test_absence_preserves_order_only_contract(self):
        self.write(["left-raise"])
        binding = verify_video.load_manifest(self.manifest, self.video)
        self.assertIsNone(binding["eventWindows"])
        code, _, report = self.invoke([{"gesture": "left-raise", "atVideoMs": 25000}], ["left-raise"])
        self.assertEqual(code, 0)
        self.assertIsNone(report["eventTimingPassed"])
        self.assertFalse(report["verificationOutcome"]["eventTimingExpectationPresent"])

    def test_binding_freezes_exact_optional_windows(self):
        windows = [self.window(start=0, end=30000.0)]
        self.write(["left-raise"], eventWindows=windows)
        binding = verify_video.load_manifest(self.manifest, self.video)
        self.assertEqual(binding["eventWindows"], windows)
        self.assertEqual(binding["sha256"], hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_null_nonlists_and_wrong_counts_are_invalid(self):
        for windows in (None, {}, "", [], [self.window(), self.window()]):
            with self.subTest(windows=windows):
                self.write(["left-raise"], eventWindows=windows)
                with self.assertRaisesRegex(ValueError, "one window"):
                    verify_video.load_manifest(self.manifest, self.video)

    def test_exact_window_shape_and_expected_gesture_order_required(self):
        for windows in ([None], [{"gesture": "left-raise", "startMs": 100}],
                        [{**self.window(), "note": "unexpected"}], [self.window("right-raise")]):
            with self.subTest(windows=windows):
                self.write(["left-raise"], eventWindows=windows)
                with self.assertRaises(ValueError):
                    verify_video.load_manifest(self.manifest, self.video)
        self.write(["left-raise", "right-raise"],
                   eventWindows=[self.window("right-raise"), self.window("left-raise")])
        with self.assertRaisesRegex(ValueError, "gesture order"):
            verify_video.load_manifest(self.manifest, self.video)

    def test_invalid_times_and_reversed_bounds_fail_before_inference(self):
        for value in (True, False, "100", None, float("nan"), float("inf"),
                      -float("inf"), -.001, 30000.001, 10**400):
            for field in ("startMs", "endMs"):
                with self.subTest(value=value, field=field):
                    window = {**self.window(), field: value}
                    self.write(["left-raise"], eventWindows=[window])
                    code, inference, report = self.invoke([], ["left-raise"])
                    self.assertEqual(code, 2)
                    inference.assert_not_called()
                    self.assertIsNone(report)
        self.write(["left-raise"], eventWindows=[self.window(start=201, end=200)])
        with self.assertRaisesRegex(ValueError, "finite, ordered"):
            verify_video.load_manifest(self.manifest, self.video)

    def test_partial_annotation_cannot_carry_even_empty_windows(self):
        self.write(expectedGestures=None, eventWindows=[])
        code, inference, report = self.invoke([], None, annotation=True)
        self.assertEqual(code, 2)
        inference.assert_not_called()
        self.assertIsNone(report)

    def test_inclusive_boundaries_and_unrounded_just_outside_times(self):
        windows = [self.window()]
        for at, passed, reason in ((100, True, "within-window"), (200, True, "within-window"),
                                   (99.999, False, "early"), (200.001, False, "late")):
            with self.subTest(at=at):
                result = verify_video.evaluate_event_windows([{"gesture": "left-raise", "atVideoMs": at}], windows)
                self.assertIs(result["passed"], passed)
                self.assertEqual(result["checks"][0]["reason"], reason)
                self.assertEqual(result["checks"][0]["atVideoMs"], at)

    def test_zero_duration_and_global_endpoints_are_inclusive(self):
        for at in (0, 10.125, 30000):
            with self.subTest(at=at):
                self.write(["left-raise"], eventWindows=[self.window(start=at, end=at)])
                code, _, report = self.invoke([{"gesture": "left-raise", "atVideoMs": at}], ["left-raise"])
                self.assertEqual(code, 0)
                self.assertTrue(report["eventTimingPassed"])

    def test_frame_loop_preserves_unrounded_emission_time_without_dnn(self):
        from motion import synthetic_observation

        capture = mock.Mock()
        capture.read.side_effect = [(True, index) for index in range(24)]
        pose = mock.Mock()
        pose.runtime = {"verified": True}
        pose.cv = SimpleNamespace(VideoCapture=mock.Mock(), CAP_FFMPEG=1900)
        pose.infer.side_effect = lambda index: (synthetic_observation("neutral" if index < 11 else "left"),
                                               "tracking", 0.0)
        pose.preview.return_value = {"jpeg": "data:image/jpeg;base64,AA==", "width": 1, "height": 1,
            "visibility": {key: True for key in ("leftShoulder", "rightShoulder", "leftWrist", "rightWrist")},
            "confidence": 1.0}
        with mock.patch.object(verify_video, "OpenCVPose", return_value=pose), \
             mock.patch.object(verify_video, "open_video", return_value=(capture, 24)), \
             mock.patch.object(verify_video.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(game(1)))):
            report = verify_video.verify(self.video, seconds=1, expected=["left-raise"])
        at = 20 * 1000 / 24
        self.assertEqual(report["events"][0]["atVideoMs"], at)
        self.assertNotEqual(at, round(at, 2))
        exact = [self.window(start=at, end=at)]
        self.assertTrue(verify_video.evaluate_event_windows(report["events"], exact)["passed"])
        capture.release.assert_called_once()

    def test_missing_extra_wrong_side_and_invalid_timestamps_fail(self):
        windows = [self.window()]
        valid = {"gesture": "left-raise", "atVideoMs": 150}
        for events, reason in (([], "missing-event"), ([valid, valid], "unexpected-event"),
                               ([{**valid, "gesture": "right-raise"}], "gesture-mismatch")):
            with self.subTest(events=events):
                result = verify_video.evaluate_event_windows(events, windows)
                self.assertFalse(result["passed"])
                self.assertIn(reason, [check["reason"] for check in result["checks"]])
        for at in (None, True, "150", float("nan"), float("inf"), -1, 30001, 10**400):
            with self.subTest(at=at):
                result = verify_video.evaluate_event_windows([{**valid, "atVideoMs": at}], windows)
                self.assertFalse(result["passed"])
                self.assertEqual(result["checks"][0]["reason"], "invalid-timestamp")
                self.assertIsNone(result["checks"][0]["atVideoMs"])
                json.dumps(result, allow_nan=False)

    def test_empty_negative_control_accepts_only_zero_events(self):
        self.write([], eventWindows=[])
        code, _, report = self.invoke([], [])
        self.assertEqual(code, 0)
        self.assertTrue(report["eventTimingPassed"])
        self.assertEqual(report["expectation"]["eventWindows"], [])
        self.assertEqual(report["verificationOutcome"]["status"], "negative-control-matched")
        self.assertFalse(report["verificationOutcome"]["completeGoalVerified"])
        self.assertFalse(verify_video.evaluate_event_windows([{"gesture": "left-raise", "atVideoMs": 150}], [])["passed"])

    def test_wrong_timing_independently_fails_sequence_scoring_and_ack_success(self):
        windows = [self.window(gesture, 1000 * index, 1000 * index + 100)
                   for index, gesture in enumerate(GESTURES)]
        events = [{"gesture": gesture, "atVideoMs": 1000 * index + 50}
                  for index, gesture in enumerate(GESTURES)]
        self.write(eventWindows=windows)
        events[2]["atVideoMs"] = 2200
        code, _, report = self.invoke(events, GESTURES, complete=True)
        self.assertEqual(code, 1)
        self.assertTrue(report["expectedSequencePassed"])
        self.assertTrue(report["gameScoringMatches"])
        self.assertTrue(report["gameAcknowledgmentMatches"])
        self.assertFalse(report["eventTimingPassed"])
        self.assertEqual(report["eventTiming"]["checks"][2]["reason"], "late")
        self.assertEqual(report["verificationOutcome"]["status"], "failed")
        self.assertFalse(report["verificationOutcome"]["completeGoalVerified"])
        self.assertEqual(report["expectation"]["eventWindows"], windows)

    def test_matched_six_windows_verify_goal_and_survive_shorter_requested_bound(self):
        windows = [self.window(gesture, 1000 * index, 1000 * index + 100)
                   for index, gesture in enumerate(GESTURES)]
        events = [{"gesture": gesture, "atVideoMs": 1000 * index + 50}
                  for index, gesture in enumerate(GESTURES)]
        self.write(eventWindows=windows)
        code, _, report = self.invoke(events, GESTURES, complete=True)
        self.assertEqual(code, 0)
        self.assertTrue(report["eventTimingPassed"])
        self.assertTrue(report["verificationOutcome"]["completeGoalVerified"])
        self.output.unlink()
        code, _, report = self.invoke([], GESTURES, seconds=1)
        self.assertEqual(code, 1)
        self.assertFalse(report["eventTimingPassed"])
        self.assertEqual(report["expectation"]["eventWindows"], windows)


if __name__ == "__main__":
    unittest.main()
