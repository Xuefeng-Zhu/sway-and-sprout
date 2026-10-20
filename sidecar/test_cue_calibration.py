"""Calibration feedback is a snapshot of synthetic classifier state; no camera/socket."""

from dataclasses import replace
import unittest

from motion import synthetic_observation
from service import MotionService


class CueCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.control = dict(clientId="12345678-0000-4000-8000-000000000001",
                            roundId="12345678-0000-4000-8000-000000000002",
                            revision=0, active=True, mode="seated", after=0)
        self.service = MotionService({"opencv": "5.0.0", "verified": True}, "synthetic",
                                     clock=lambda: self.now)
        self.packet = self.service.poll(self.control)

    def feed(self, observation, count=1):
        for _ in range(count):
            self.service.observe(self.service.token(), observation, "tracking")
            self.now += 50
            self.packet = self.service.poll(self.control)

    def arm(self):
        self.feed(synthetic_observation(), 7)
        self.assertTrue(self.packet["metrics"]["armed"])

    def test_cue_metric_waits_for_neutral_and_survives_expected_transition(self):
        self.assertIs(self.packet["metrics"]["armed"], False)
        self.feed(synthetic_observation(), 6)
        self.assertFalse(self.packet["metrics"]["armed"])
        self.feed(synthetic_observation())
        calibrated = self.packet
        self.assertTrue(calibrated["metrics"]["armed"])
        fixture = synthetic_observation()
        self.feed(replace(fixture, left_wrist=replace(fixture.left_wrist, y=.40)), 2)
        self.assertEqual(self.packet["status"], "neutral")
        self.assertTrue(self.packet["metrics"]["armed"])
        self.feed(synthetic_observation("left"), 2)
        self.assertEqual(self.packet["status"], "hold")
        self.assertTrue(self.packet["metrics"]["armed"])
        self.feed(synthetic_observation("left"), 6)
        self.assertEqual(self.packet["events"][0]["gesture"], "left-raise")
        self.assertFalse(self.packet["metrics"]["armed"])
        self.assertTrue(calibrated["metrics"]["armed"])  # Earlier packet was a snapshot.

    def test_wrong_side_and_low_confidence_clear_the_cue_metric(self):
        for observation, status in ((synthetic_observation("right"), "neutral"),
                                    (synthetic_observation(confidence=.4), "low-confidence")):
            with self.subTest(status=status):
                self.setUp()
                self.arm()
                self.feed(observation)
                self.assertEqual(self.packet["status"], status)
                self.assertFalse(self.packet["metrics"]["armed"])

    def test_pause_resume_and_new_round_require_fresh_calibration(self):
        self.arm()
        for revision, active in ((1, False), (2, True)):
            self.control = {**self.control, "revision": revision, "active": active}
            packet = self.service.poll(self.control)
            self.assertFalse(packet["metrics"]["armed"])
        self.arm()
        self.control = {**self.control, "revision": 3,
                        "roundId": "12345678-0000-4000-8000-000000000003"}
        self.assertFalse(self.service.poll(self.control)["metrics"]["armed"])

    def test_gap_resets_metric_without_poll_or_metric_read_arming_it(self):
        self.arm()
        self.now += 301
        self.feed(synthetic_observation())
        self.assertFalse(self.packet["metrics"]["armed"])
        for _ in range(10):
            self.assertFalse(self.service.poll(self.control)["metrics"]["armed"])
        self.assertNotIn("armed", self.service.metrics)  # Recomputed from classifier each poll.


if __name__ == "__main__":
    unittest.main()
