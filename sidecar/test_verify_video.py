"""Verification outcome regressions only: mocked inference, no camera or video."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
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


if __name__ == "__main__":
    unittest.main()
