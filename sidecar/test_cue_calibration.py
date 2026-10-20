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

    def test_neutral_dwell_reports_actual_frames_not_time_spent_polling(self):
        self.feed(synthetic_observation(), 4)
        snapshot = self.packet["metrics"]["calibration"]
        self.assertEqual(snapshot["reason"], "settling-neutral")
        self.assertEqual(snapshot["neutralMs"], 150)
        self.assertEqual(snapshot["requiredNeutralMs"], 300)
        self.assertEqual(snapshot["gates"], {"left": "down", "right": "down"})
        self.now += 700
        for _ in range(4):
            packet = self.service.poll(self.control)
            self.assertEqual(packet["metrics"]["calibration"]["neutralMs"], 0)
            self.assertEqual(packet["metrics"]["calibration"]["reason"], "stale")
            self.assertFalse(packet["metrics"]["armed"])
        self.feed(synthetic_observation())
        self.assertEqual(self.packet["metrics"]["calibration"]["neutralMs"], 0)
        self.assertEqual(snapshot["neutralMs"], 150)

    def test_correct_raise_before_calibration_explains_blocked_scoring(self):
        self.feed(synthetic_observation("left"), 10)
        packet = self.packet
        self.assertEqual(packet["events"], [])
        self.assertEqual(packet["metrics"]["calibration"]["reason"], "needs-neutral")
        self.assertEqual(packet["metrics"]["calibration"]["gates"], {"left": "up", "right": "down"})
        self.assertFalse(packet["metrics"]["armed"])

    def test_loss_identifies_unreliable_wrist_and_clears_dwell(self):
        self.arm()
        fixture = synthetic_observation()
        fixture = replace(fixture, right_wrist=replace(fixture.right_wrist, confidence=.4))
        self.feed(fixture)
        feedback = self.packet["metrics"]["calibration"]
        self.assertEqual(feedback["reason"], "low-confidence")
        self.assertEqual(feedback["lowConfidence"], ["rightWrist"])
        self.assertEqual(feedback["minimumConfidence"], .4)
        self.assertEqual(feedback["neutralMs"], 0)
        self.assertEqual(feedback["gates"], {"left": "unknown", "right": "unknown"})
        self.assertFalse(self.packet["metrics"]["armed"])

    def test_wrong_side_and_both_raised_have_distinct_actionable_reasons(self):
        for side, reason in (("right", "wrong-side"), ("both", "both-raised")):
            with self.subTest(side=side):
                self.setUp()
                self.arm()
                self.feed(synthetic_observation(side))
                self.assertEqual(self.packet["metrics"]["calibration"]["reason"], reason)
                self.assertEqual(self.packet["events"], [])
                self.assertFalse(self.packet["metrics"]["armed"])

    def test_feedback_never_changes_gesture_or_ack_requirements(self):
        self.arm()
        self.assertEqual(self.packet["metrics"]["calibration"]["reason"], "ready")
        self.feed(synthetic_observation("left"), 3)
        feedback = self.packet["metrics"]["calibration"]
        self.assertEqual(feedback["reason"], "holding")
        self.assertEqual(feedback["holdMs"], 100)
        self.assertEqual(feedback["requiredHoldMs"], 350)
        self.assertEqual(self.packet["events"], [])
        self.feed(synthetic_observation("left"), 5)
        self.assertEqual(self.packet["metrics"]["calibration"]["reason"], "return-to-neutral")
        self.assertEqual([e["gesture"] for e in self.packet["events"]], ["left-raise"])
        self.assertFalse(self.packet["metrics"]["armed"])
        self.control["after"] = self.packet["seq"]
        self.assertEqual(self.service.poll(self.control)["events"], [])
        self.assertEqual(self.service.ack_expected, "right")

    def test_nested_feedback_packets_are_isolated_snapshots_without_coordinates(self):
        self.arm()
        feedback = self.packet["metrics"]["calibration"]
        feedback["gates"]["left"] = "up"
        feedback["lowConfidence"].append("person")
        current = self.service.poll(self.control)["metrics"]["calibration"]
        self.assertEqual(current["gates"]["left"], "down")
        self.assertEqual(current["lowConfidence"], [])
        self.assertEqual(set(current), {"reason", "neutralMs", "requiredNeutralMs", "holdMs",
                                        "requiredHoldMs", "gates", "lowConfidence", "minimumConfidence",
                                        "fresh", "ageMs"})

    def test_polling_after_frame_stall_masks_ready_without_mutating_classifier(self):
        self.arm()
        ready = self.packet["metrics"]["calibration"]
        self.assertTrue(ready["fresh"])
        self.assertEqual(ready["ageMs"], 50)
        self.now = 600
        self.assertTrue(self.service.poll(self.control)["metrics"]["armed"])
        self.now = 601
        self.assertFalse(self.service.poll(self.control)["metrics"]["armed"])
        for delay in (350, 700, 1700, 3000):
            self.now = 300 + delay
            packet = self.service.poll(self.control)
            feedback = packet["metrics"]["calibration"]
            self.assertEqual(feedback["reason"], "stale")
            self.assertFalse(feedback["fresh"])
            self.assertEqual(feedback["ageMs"], delay)
            self.assertFalse(packet["metrics"]["armed"])
            self.assertEqual(feedback["gates"], {"left": "unknown", "right": "unknown"})
            self.assertTrue(self.service.machine.armed)  # Diagnostics never change classifier history.
            self.assertEqual(packet["metrics"]["frames"], 7)
        self.assertEqual(ready["reason"], "ready")
        self.feed(synthetic_observation("left"))
        self.assertFalse(self.packet["metrics"]["armed"])
        self.assertEqual(self.packet["metrics"]["calibration"]["reason"], "needs-neutral")
        self.assertEqual(self.packet["events"], [])

    def test_pause_and_capture_loss_reset_feedback_instead_of_stale_ready(self):
        self.arm()
        self.control = {**self.control, "revision": 1, "active": False}
        packet = self.service.poll(self.control)
        self.assertEqual(packet["metrics"]["calibration"]["reason"], "paused")
        self.assertEqual(packet["metrics"]["calibration"]["neutralMs"], 0)
        self.control = {**self.control, "revision": 2, "active": True}
        self.service.poll(self.control)
        self.service.observe(self.service.token(), None, "no-person")
        self.assertEqual(self.service.poll(self.control)["metrics"]["calibration"]["reason"], "no-person")


if __name__ == "__main__":
    unittest.main()
