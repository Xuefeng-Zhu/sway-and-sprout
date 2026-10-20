"""Synthetic capture-epoch regressions: no camera, model, socket or real image."""
import unittest

from motion import synthetic_observation
from service import MotionService


CLIENT = '12345678-0000-4000-8000-000000000001'
ROUND = '12345678-0000-4000-8000-000000000002'


class CaptureEpochTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = MotionService({'opencv': '5.0.0-fixture', 'verified': True},
                                     'camera', clock=lambda: self.now)
        self.control = dict(clientId=CLIENT, roundId=ROUND, revision=0,
                            active=True, mode='seated', after=0)
        self.service.poll(self.control)

    @staticmethod
    def preview_image():
        # publish_preview validates metadata; this is not decoded or displayed.
        return dict(jpeg='data:image/jpeg;base64,AA==', width=1, height=1,
                    visibility=dict(leftShoulder=True, rightShoulder=True,
                                    leftWrist=True, rightWrist=True), confidence=.9)

    def test_old_inference_and_preview_rejected_after_same_context_lease_renewal(self):
        old = self.service.token()
        self.now = 1501
        self.assertIsNone(self.service.token())
        self.service.poll(self.control)
        fresh = self.service.token()
        self.assertNotEqual(old, fresh)
        before = self.service.metrics['frames']
        self.assertIsNone(self.service.observe(old, synthetic_observation(), 'tracking'))
        self.assertEqual(self.service.metrics['frames'], before)
        self.assertFalse(self.service.publish_preview(old, self.preview_image(), self.now))
        self.assertIsNone(self.service.latest_preview)
        self.service.observe(fresh, synthetic_observation(), 'tracking')
        self.assertEqual(self.service.metrics['frames'], before + 1)
        self.assertTrue(self.service.publish_preview(fresh, self.preview_image(), self.now))
        self.assertTrue(self.service.preview(self.control)['available'])

    def test_pending_expiry_cannot_admit_the_inflight_pose_into_reset_epoch(self):
        for side, count in (('neutral', 11), ('left', 8)):
            for _ in range(count):
                self.service.poll(self.control)
                self.service.observe(self.service.token(), synthetic_observation(side), 'tracking')
                self.now += 50
        self.assertEqual(self.service.seq, 1)
        pending_at = self.service.events[0]['at']
        # Keep the capture lease active without expiring the queued event yet.
        self.now = pending_at + 1400
        self.service.poll(self.control)
        old = self.service.token()
        self.now = pending_at + 1501
        before = self.service.metrics['frames']
        self.service.observe(old, synthetic_observation(), 'tracking')
        self.assertEqual(self.service.metrics['frames'], before)
        fresh = self.service.token()
        self.assertNotEqual(old, fresh)
        self.assertEqual(self.service.machine.expected, 'left')
        self.assertFalse(self.service.machine.armed)
        self.assertFalse(self.service.publish_preview(old, self.preview_image(), self.now))
        self.service.observe(fresh, synthetic_observation(), 'tracking')
        self.assertEqual(self.service.metrics['frames'], before + 1)

    def test_same_context_polls_keep_current_token_and_arming(self):
        token = self.service.token()
        for now in (0, 100, 200, 300):
            self.now = now
            self.service.poll(self.control)
            self.assertEqual(self.service.token(), token)
            self.service.observe(token, synthetic_observation(), 'tracking')
        self.assertTrue(self.service.machine.armed)
        self.assertEqual(self.service.metrics['frames'], 4)


if __name__ == '__main__':
    unittest.main()
