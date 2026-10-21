"""Synthetic functional checks; no video/model/camera or accuracy claims."""
import csv
from dataclasses import replace
from pathlib import Path
import unittest

from activity import ActivityMachine, synthetic_activity_observation
from motion import Landmark, Observation

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/activity-traces.csv"


def traces():
    cases = {}
    with FIXTURE.open() as source:
        for row in csv.DictReader(source):
            points = [Landmark(*(float(row[name + key]) for key in ("X", "Y", "Score")))
                      for name in ("ls", "rs", "lw", "rw", "lh", "rh")]
            observation = Observation(*points[:4], min(p.confidence for p in points[:4]),
                                      left_hip=points[4], right_hip=points[5])
            cases.setdefault(row["case"], []).append((float(row["ms"]), observation))
    return cases


def event_times(rows):
    machine = ActivityMachine()
    return [int(now) for now, observation in rows if machine.update(observation, now)]


class ActivityTests(unittest.TestCase):
    def test_explicit_synthetic_source_generates_activity_not_an_unknown_side(self):
        machine = ActivityMachine()
        events = [machine.update(synthetic_activity_observation(now), now) for now in range(0, 4001, 50)]
        self.assertGreaterEqual(sum(event is not None for event in events), 2)

    def test_small_motion_repeated_either_side_both_and_sway_count(self):
        data = traces()
        for name in ("small-left", "small-right", "both-arms", "torso-sway", "missing-unrelated"):
            with self.subTest(name=name):
                times = event_times(data[name])
                self.assertGreaterEqual(len(times), 2)
                self.assertTrue(all(b - a >= 1000 for a, b in zip(times, times[1:])))
                self.assertEqual(times, event_times(data["small-left"]))

    def test_static_jitter_camera_translation_missing_jump_and_gaps_do_not_score(self):
        for name in ("static", "jitter", "camera-translation", "missing-all", "jump", "gap-reset"):
            with self.subTest(name=name):
                self.assertEqual(event_times(traces()[name]), [])

    def test_absent_unrelated_joints_do_not_gate_a_clear_moving_hand(self):
        rows = [(now, replace(obs, right_wrist=None, left_hip=None, right_hip=None, confidence=0.0))
                for now, obs in traces()["small-left"]]
        self.assertEqual(event_times(rows), event_times(traces()["small-left"]))

    def test_reacquired_static_joint_does_not_reuse_partial_movement(self):
        machine = ActivityMachine()
        rows = traces()["small-left"]
        for now, observation in rows[:7]:
            self.assertIsNone(machine.update(observation, now))
        missing = replace(rows[7][1], left_wrist=None)
        self.assertIsNone(machine.update(missing, 350))
        stationary = rows[8][1]
        self.assertTrue(all(machine.update(stationary, now) is None for now in range(400, 3001, 50)))

    def test_static_raised_hold_never_scores_and_stopping_movement_stops_credit(self):
        rows = traces()["small-left"]
        machine = ActivityMachine()
        held = replace(rows[0][1], left_wrist=Landmark(-.6, -.8))
        self.assertTrue(all(machine.update(held, i * 50) is None for i in range(80)))
        machine.new_round()
        for now, obs in rows[:41]:
            machine.update(obs, now)
        stationary = rows[40][1]
        # Allow smoothing to settle, then no repeated credit for a held pose.
        for now in range(2050, 3001, 50):
            machine.update(stationary, now)
        self.assertTrue(all(machine.update(stationary, now) is None for now in range(3050, 6001, 50)))

    def test_loss_pause_reset_and_timestamp_guards(self):
        rows = traces()["small-left"]
        machine = ActivityMachine()
        for now, obs in rows[:7]:
            self.assertIsNone(machine.update(obs, now))
        machine.lost("paused")
        self.assertFalse(machine.armed)
        self.assertEqual(machine.expected, "any")
        self.assertIsNone(machine.update(rows[7][1], rows[7][0]))
        self.assertIsNone(machine.update(rows[7][1], rows[7][0]))
        with self.assertRaises(ValueError):
            machine.update(rows[0][1], 1)
        with self.assertRaises(ValueError):
            machine.update(rows[0][1], float("nan"))
        self.assertIsNone(machine.update(None, 500))
        self.assertEqual(machine.status, "no-person")


if __name__ == "__main__":
    unittest.main()
