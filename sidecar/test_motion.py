import math
import unittest
from dataclasses import replace

from motion import Config, GestureMachine, Landmark, synthetic_observation


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.machine = GestureMachine()
        self.now = 0

    def feed(self, side, milliseconds, confidence=1.0):
        events = []
        for _ in range(milliseconds // 50 + 1):
            event = self.machine.update(synthetic_observation(side, confidence), self.now)
            self.now += 50
            if event:
                events.append(event)
        return events

    def step_wrists(self, left_y, right_y, interval_ms=75):
        fixture = synthetic_observation("neutral")
        observation = replace(fixture,
                              left_wrist=replace(fixture.left_wrist, y=left_y),
                              right_wrist=replace(fixture.right_wrist, y=right_y))
        event = self.machine.update(observation, self.now)
        self.now += interval_ms
        return event

    def test_neutral_then_hold_emits_once_not_per_frame(self):
        self.assertEqual(self.feed("left", 1000), [])
        self.feed("neutral", 300)
        self.assertEqual(self.feed("left", 300), [])
        event = self.feed("left", 100)
        self.assertEqual([e["gesture"] for e in event], ["left-raise"])
        self.assertEqual(self.feed("left", 1000), [])

    def test_alternation_and_both_up_or_wrong_side_require_neutral(self):
        self.feed("neutral", 350)
        self.assertEqual(self.feed("both", 500), [])
        self.assertEqual(self.feed("left", 500), [])
        self.feed("neutral", 350)
        self.assertEqual(self.feed("right", 500), [])
        self.feed("neutral", 350)
        self.assertEqual([e["gesture"] for e in self.feed("left", 400)], ["left-raise"])
        self.feed("neutral", 500)
        self.assertEqual([e["gesture"] for e in self.feed("right", 400)], ["right-raise"])

    def test_gradual_left_and_right_raises_cross_transition_band(self):
        # At 75 ms/frame, a natural raise takes several frames to cross the
        # shoulder-height band between resting (> .46) and raised (< .31).
        for side in ("left", "right"):
            with self.subTest(side=side):
                self.machine.new_round()
                if side == "right":
                    self.feed("neutral", 350)
                    self.assertEqual(len(self.feed("left", 400)), 1)
                self.feed("neutral", 500)
                for height in (.65, .52, .44, .40, .36, .32, .28, .22, .15):
                    left, right = (height, .75) if side == "left" else (.75, height)
                    self.assertIsNone(self.step_wrists(left, right))
                events = self.feed(side, 400)
                self.assertEqual([e["gesture"] for e in events], [side + "-raise"])

    def test_transition_without_prior_neutral_cannot_arm_or_score(self):
        for height in (.44, .40, .36, .32):
            self.assertIsNone(self.step_wrists(height, .75))
            self.assertFalse(self.machine.armed)
        self.assertEqual(self.feed("left", 1000), [])

    def test_transition_cancels_partial_hold_before_full_new_hold(self):
        self.feed("neutral", 350)
        self.assertEqual(self.feed("left", 200), [])
        self.assertEqual(self.machine.held_ms, 200)
        for height in (.40, .36):
            self.assertIsNone(self.step_wrists(height, .75))
            self.assertEqual(self.machine.held_ms, 0)
            self.assertIsNone(self.machine.hold_since)
        self.assertEqual(self.feed("left", 300), [])
        self.assertEqual([e["gesture"] for e in self.feed("left", 50)], ["left-raise"])

    def test_wrong_side_transition_disarms_until_fresh_neutral(self):
        self.feed("neutral", 350)
        for height in (.44, .40, .36, .28, .15):
            self.assertIsNone(self.step_wrists(.75, height))
        self.assertFalse(self.machine.armed)
        self.assertEqual(self.feed("left", 1000), [])
        self.feed("neutral", 350)
        self.assertEqual(len(self.feed("left", 400)), 1)

    def test_both_transition_or_raised_need_fresh_neutral(self):
        for height in (.40, .15):
            with self.subTest(height=height):
                self.machine.new_round()
                self.feed("neutral", 350)
                self.assertIsNone(self.step_wrists(height, height))
                self.assertFalse(self.machine.armed)
                self.assertEqual(self.feed("left", 1000), [])
                self.feed("neutral", 350)
                self.assertEqual(len(self.feed("left", 400)), 1)

    def test_loss_discards_partial_hold(self):
        self.feed("neutral", 350)
        self.feed("left", 250)
        self.machine.update(None, self.now)
        self.now += 50
        self.assertEqual(self.machine.status, "no-person")
        self.assertEqual(self.feed("left", 500), [])
        self.feed("neutral", 350)
        self.assertEqual(len(self.feed("left", 400)), 1)

    def test_low_confidence_discards_armed_state(self):
        self.feed("neutral", 350)
        self.feed("neutral", 50, 0.2)
        self.assertEqual(self.machine.status, "low-confidence")
        self.assertEqual(self.feed("left", 500), [])

    def test_pause_preserves_side_but_requires_neutral(self):
        self.feed("neutral", 350)
        self.feed("left", 400)
        self.machine.reset_temporal()
        self.assertEqual(self.machine.expected, "right")
        self.assertEqual(self.feed("right", 500), [])
        self.feed("neutral", 350)
        self.assertEqual(len(self.feed("right", 400)), 1)
        self.machine.new_round()
        self.assertEqual(self.machine.expected, "left")

    def test_long_frame_gap_cannot_complete_hold(self):
        self.feed("neutral", 350)
        self.feed("left", 250)
        self.now += 1000
        self.assertEqual(self.feed("left", 500), [])

    def test_cooldown_cannot_be_bypassed_with_short_custom_hold(self):
        self.machine = GestureMachine(Config(hold_ms=50, neutral_ms=50, cooldown_ms=500))
        self.feed("neutral", 50)
        self.assertEqual(len(self.feed("left", 50)), 1)
        self.feed("neutral", 50)
        self.assertEqual(self.feed("right", 50), [])
        self.assertEqual(len(self.feed("right", 500)), 1)

    def test_nonfinite_or_degenerate_landmarks_rejected(self):
        self.feed("neutral", 350)
        fixture = synthetic_observation("left")
        self.machine.update(replace(fixture, left_wrist=Landmark(math.nan, 0.1)), self.now)
        self.assertEqual(self.machine.status, "low-confidence")
        self.now += 50
        self.machine.update(replace(fixture, left_shoulder=fixture.right_shoulder), self.now)
        self.assertEqual(self.machine.status, "low-confidence")

    def test_time_reversal_rejected(self):
        self.feed("neutral", 350)
        with self.assertRaises(ValueError):
            self.machine.update(synthetic_observation(), 0)


if __name__ == "__main__":
    unittest.main()
