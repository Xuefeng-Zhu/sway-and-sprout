"""Offline classifier regressions with synthetic coordinates.

Run in this directory with: python -B -m unittest test_motion_offline -v

Imports only motion/service; opens no camera, model, socket, app, or image.
Passing diagnostic probes describe gates; they do not establish human movements.
"""

from collections import Counter
from dataclasses import replace
import math
import unittest


from motion import GestureMachine, Landmark, Observation, synthetic_observation
from service import MotionService


CLIENT = '12345678-0000-4000-8000-000000000001'
ROUND = '12345678-0000-4000-8000-000000000002'


def control(**changed):
    return {"clientId": CLIENT, "roundId": ROUND, "revision": 0, "active": True,
            "mode": "seated", "after": 0, **changed}


def pose(left_offset=100, right_offset=100, confidence=.9):
    """100px shoulder width; wrist offsets measured down from y=200 shoulders."""
    return Observation(Landmark(400, 200, confidence), Landmark(300, 200, confidence),
                       Landmark(400, 200 + left_offset, confidence),
                       Landmark(300, 200 + right_offset, confidence), confidence)


def transform(observation, scale=1.0, reflect=False, dx=0.0, dy=0.0):
    def point(value):
        x = 800 - value.x if reflect else value.x
        return replace(value, x=x * scale + dx, y=value.y * scale + dy)
    return Observation(*[point(value) for value in (
        observation.left_shoulder, observation.right_shoulder,
        observation.left_wrist, observation.right_wrist)], observation.confidence)


class MachineDriver:
    def __init__(self, convert=lambda value: value):
        self.machine = GestureMachine()
        self.now = 0
        self.convert = convert
        self.events = []
        self.statuses = Counter()

    def step(self, observation, interval=67):
        event = self.machine.update(self.convert(observation) if observation else None, self.now)
        self.statuses[self.machine.status] += 1
        if event:
            self.events.append(event['gesture'])
        self.now += interval
        return event

    def frames(self, observation, count, interval=67):
        for _ in range(count):
            self.step(observation, interval)

    def gradual_raise(self, side):
        self.frames(pose(), 9)
        for offset in (75, 45, 25, 15, 0, -15, -29, -31, -45, -60):
            self.step(pose(offset, 100) if side == 'left' else pose(100, offset))
        self.frames(pose(-60, 100) if side == 'left' else pose(100, -60), 8)


class OfflineCoordinateTests(unittest.TestCase):
    def test_pixel_scale_translation_and_anatomical_x_mirror_preserve_six_raises(self):
        for scale in (1 / 640, .1, 1, 2, 10):
            for reflected in (False, True):
                with self.subTest(scale=scale, xReflected=reflected):
                    driver = MachineDriver(lambda value: transform(value, scale, reflected,
                                                                     17 * scale, 23 * scale))
                    for side in ('left', 'right') * 3:
                        driver.gradual_raise(side)
                    self.assertEqual(driver.events, ['left-raise', 'right-raise'] * 3)
                    self.assertGreater(driver.statuses['tracking'], 0)
                    self.assertGreater(driver.statuses['hold'], 0)

    def test_existing_normalized_fixture_and_pixel_fixture_both_arm(self):
        for fixture in (synthetic_observation('neutral'), pose()):
            with self.subTest(fixture='normalized' if fixture.left_shoulder.x < 1 else 'pixels'):
                machine = GestureMachine()
                for now in (0, 75, 150, 225, 300):
                    self.assertIsNone(machine.update(fixture, now))
                self.assertTrue(machine.armed)
                self.assertEqual(machine.status, 'tracking')

    def test_x_reflection_does_not_swap_anatomical_event_names(self):
        driver = MachineDriver(lambda value: transform(value, reflect=True))
        driver.gradual_raise('left')
        self.assertEqual(driver.events, ['left-raise'])
        self.assertEqual(driver.machine.expected, 'right')

    def test_gradual_lowering_requires_full_rest_before_arming(self):
        driver = MachineDriver()
        for offset in (-60, -30, 0, 15, 20):
            driver.frames(pose(offset, offset), 6)
            self.assertFalse(driver.machine.armed)
        for _ in range(4):
            driver.step(pose(25, 25), interval=75)
            self.assertFalse(driver.machine.armed)
        driver.step(pose(25, 25), interval=75)
        self.assertTrue(driver.machine.armed)


class OfflineGateAndTimingTests(unittest.TestCase):
    def test_neutral_boundary_is_strict_and_waits_300ms(self):
        machine = GestureMachine()
        for now in range(0, 1000, 50):
            machine.update(pose(20, 20), now)
        self.assertFalse(machine.armed)
        self.assertEqual(machine.status, 'neutral')
        for now in (1000, 1100, 1200, 1299):
            machine.update(pose(20.000001, 20.000001), now)
        self.assertFalse(machine.armed)
        machine.update(pose(20.000001, 20.000001), 1300)
        self.assertTrue(machine.armed)

    def test_raise_boundary_is_strict_and_transition_cannot_earn_hold_time(self):
        machine = GestureMachine()
        for now in (0, 100, 200, 300):
            machine.update(pose(), now)
        for now in range(400, 1000, 100):
            self.assertIsNone(machine.update(pose(-30, 100), now))
        self.assertTrue(machine.armed)
        self.assertEqual(machine.held_ms, 0)
        for now in (1000, 1100, 1200, 1300):
            self.assertIsNone(machine.update(pose(-30.000001, 100), now))
        event = machine.update(pose(-30.000001, 100), 1350)
        self.assertEqual(event['gesture'], 'left-raise')

    def test_exact_300ms_frame_gap_is_allowed_301ms_resets_neutral(self):
        for gap, armed in ((300, True), (301, False)):
            with self.subTest(gap=gap):
                machine = GestureMachine()
                machine.update(pose(), 0)
                machine.update(pose(), gap)
                self.assertEqual(machine.armed, armed)

    def test_repeated_301ms_gaps_produce_neutral_even_for_perfect_rest(self):
        machine = GestureMachine()
        for now in range(0, 301 * 20, 301):
            machine.update(pose(), now)
            self.assertEqual(machine.status, 'neutral')
            self.assertFalse(machine.armed)

    def test_frame_gap_during_partial_hold_requires_new_neutral(self):
        driver = MachineDriver()
        driver.frames(pose(), 6)
        driver.frames(pose(-60, 100), 4)
        self.assertGreater(driver.machine.held_ms, 0)
        driver.now += 301
        driver.frames(pose(-60, 100), 10)
        self.assertEqual(driver.events, [])
        self.assertFalse(driver.machine.armed)
        driver.gradual_raise('left')
        self.assertEqual(driver.events, ['left-raise'])

    def test_exact_confidence_threshold_arms_below_threshold_resets_timer(self):
        machine = GestureMachine()
        for now in (0, 100, 200, 300):
            machine.update(pose(confidence=.65), now)
        self.assertTrue(machine.armed)
        machine.update(pose(confidence=.65 - 1e-8), 350)
        self.assertFalse(machine.armed)
        self.assertEqual(machine.status, 'low-confidence')
        for now in (400, 500, 600):
            machine.update(pose(), now)
        self.assertFalse(machine.armed)
        machine.update(pose(), 700)
        self.assertTrue(machine.armed)

    def test_each_required_joint_and_global_confidence_can_reset_neutral(self):
        for field in ('left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist', 'confidence'):
            with self.subTest(field=field):
                machine = GestureMachine()
                for now in (0, 100, 200):
                    machine.update(pose(), now)
                observation = pose()
                bad = (replace(observation, confidence=.4) if field == 'confidence' else
                       replace(observation, **{field: replace(getattr(observation, field), confidence=.4)}))
                machine.update(bad, 250)
                machine.update(pose(), 300)
                machine.update(pose(), 500)
                self.assertFalse(machine.armed)
                machine.update(pose(), 600)
                self.assertTrue(machine.armed)

    def test_high_confidence_388_neutral_frames_need_not_be_a_code_failure(self):
        # Fully visible wrist poses within the shoulder-height band never satisfy
        # the specified arms-down gate. This reproduces the COUNT, not a human pose.
        driver = MachineDriver()
        driver.frames(pose(0, 0), 388)
        self.assertEqual(driver.statuses, Counter(neutral=388))
        self.assertEqual(driver.events, [])
        self.assertFalse(driver.machine.armed)

    def test_neutral_status_conflates_distinct_gate_failures(self):
        for label, observation in (('both-mid', pose(0, 0)), ('both-up', pose(-60, -60)),
                                   ('wrong-side', pose(100, -60)), ('expected-up-unarmed', pose(-60, 100))):
            with self.subTest(case=label):
                driver = MachineDriver()
                driver.frames(observation, 20)
                self.assertEqual(set(driver.statuses), {'neutral'})
                self.assertEqual(driver.events, [])


class OfflineServiceResetTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = MotionService({'opencv': '5.0.0', 'verified': True}, 'synthetic',
                                     clock=lambda: self.now)
        self.context = control()
        self.after = 0
        self.service.poll(self.context)

    def observe(self, observation):
        self.service.observe(self.service.token(), observation, 'tracking')

    def frames(self, observation, count):
        for _ in range(count):
            # Poll exactly the same context every frame, more often than the UI.
            self.service.poll({**self.context, 'after': self.after})
            self.observe(observation)
            if self.service.seq > self.after:
                self.after = self.service.seq
            self.now += 67

    def gradual_raise(self, side):
        self.frames(pose(), 9)
        for offset in (75, 45, 25, 15, 0, -15, -29, -31, -45, -60):
            self.frames(pose(offset, 100) if side == 'left' else pose(100, offset), 1)
        self.frames(pose(-60, 100) if side == 'left' else pose(100, -60), 8)

    def test_stable_polling_context_preserves_calibration_hold_and_six_events(self):
        for mode in ('seated', 'standing'):
            with self.subTest(mode=mode):
                self.setUp()
                self.context = {**self.context, 'mode': mode, 'revision': 3}
                for side in ('left', 'right') * 3:
                    self.gradual_raise(side)
                packet = self.service.poll({**self.context, 'after': self.after})
                self.assertEqual(self.service.seq, 6)
                self.assertEqual(self.service.ack_seq, 6)
                self.assertEqual(packet['expected'], 'left')
                self.assertEqual([event['gesture'] for event in self.service.history],
                                 ['left-raise', 'right-raise'] * 3)

    def test_revision_change_explicitly_cancels_calibration(self):
        self.frames(pose(), 4)
        self.assertFalse(self.service.machine.armed)
        self.context = {**self.context, 'revision': 1}
        self.service.poll(self.context)
        self.frames(pose(), 4)
        self.assertFalse(self.service.machine.armed)
        self.frames(pose(), 2)
        self.assertTrue(self.service.machine.armed)

    def test_revision_churn_can_reproduce_all_neutral_but_stable_revision_does_not(self):
        for revision in range(20):
            self.context = {**self.context, 'revision': revision}
            self.frames(pose(), 1)
            self.assertEqual(self.service.machine.status, 'neutral')
        self.frames(pose(), 6)
        self.assertTrue(self.service.machine.armed)

    def test_pause_resume_keeps_acknowledged_side_but_needs_fresh_rest(self):
        self.gradual_raise('left')
        self.service.poll({**self.context, 'after': self.after})
        self.context = {**self.context, 'revision': 1, 'active': False}
        self.service.poll({**self.context, 'after': self.after})
        self.context = {**self.context, 'revision': 2, 'active': True}
        self.frames(pose(100, -60), 10)
        self.assertEqual(self.service.seq, 1)
        self.gradual_raise('right')
        self.assertEqual(self.service.seq, 2)

    def test_lease_expiry_ignores_observation_then_poll_requires_new_rest(self):
        self.frames(pose(), 6)
        self.assertTrue(self.service.machine.armed)
        old_token = self.service.token()
        frames = self.service.metrics['frames']
        self.now += 1501
        self.assertIsNone(self.service.observe(old_token, pose(-60, 100), 'tracking'))
        self.assertEqual(self.service.metrics['frames'], frames)
        self.service.poll(self.context)
        self.assertFalse(self.service.machine.armed)
        self.frames(pose(-60, 100), 10)
        self.assertEqual(self.service.seq, 0)
        self.gradual_raise('left')
        self.assertEqual(self.service.seq, 1)

    def test_pending_event_expiry_does_not_reset_a_zero_event_round(self):
        self.frames(pose(), 50)
        self.assertTrue(self.service.machine.armed)
        self.assertEqual(self.service.seq, 0)
        self.frames(pose(-60, 100), 8)
        self.assertEqual(self.service.seq, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
