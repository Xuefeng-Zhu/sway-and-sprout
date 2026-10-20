"""Verification outcome regressions only: mocked inference, no camera or video."""
import contextlib
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
    def invoke(self, *, scored=None, expected_pass=True, ack=True, manifest=True):
        scored = game() if scored is None else scored
        report = {"source": "video", "evidenceType": "mocked-outcome-only", "fixture": {},
                  "observedGestures": GESTURES, "expectedGestures": GESTURES,
                  "expectedSequencePassed": expected_pass if manifest else None,
                  "game": scored, "gameAcknowledgmentMatches": ack,
                  "gameScoringMatches": verify_video.game_scoring_matches(GESTURES, scored),
                  "armedTransitions": 6, "previewResponses": 0, "physicalCameraOpens": 0}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "scalar-report.json"
            expected = Path(directory) / "expected.json"
            expected.write_text(json.dumps({"expectedGestures": GESTURES}))
            argv = ["verify_video.py", "never-opened.mp4", "--output", str(output)]
            if manifest:
                argv.extend(["--expected", str(expected)])
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


if __name__ == "__main__":
    unittest.main()
