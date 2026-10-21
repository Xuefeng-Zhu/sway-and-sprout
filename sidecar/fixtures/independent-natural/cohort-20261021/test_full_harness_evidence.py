"""Harness lifecycle only: fake bytes/callbacks, no decoder, SDK, model or camera."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).with_name('run_full_frozen.py')
SPEC = importlib.util.spec_from_file_location('frozen_full_harness', MODULE)
harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harness)


class EvidenceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.label = self.root / 'annotation.freeze.json'
        self.label.write_text('{"testOnly": true}')
        cases = []
        for name in ('first', 'next'):
            video = self.root / (name + '.fake')
            video.write_bytes(('fake test input, not media: ' + name).encode())
            cases.append({'caseId': name, 'video': str(video), 'sha256': harness.digest(video),
                          'frames': 2, 'fps': 10.0, 'streamTickMs': 1.0,
                          'displayPtsMs': [0.0, 100.0], 'expectationKnown': False})
        self.plan = {'status': 'FROZEN_BEFORE_FIRST_MODEL_INFERENCE', 'annotationAuthorType': 'AI',
                     'humanConfirmed': False, 'fullProfile': {'runningMode': 'IMAGE', 'numPoses': 2,
                                                           'delegate': 'CPU', 'admissionThreshold': .65},
                     'sourcePins': [], 'frozenFiles': [{'path': str(self.label),
                                                       'sha256': harness.digest(self.label)}], 'cases': cases}
        self.out = self.root / 'evidence'

    @staticmethod
    def fake_report(item, state, count=2):
        state['modelClosed'] = True  # No graph exists in these callback-only tests.
        state['rows'][:] = [{'frame': i, 'plannedFrameMs': i * 100.0, 'atVideoMs': i * 100.0,
                             'serviceObservationMs': i * 100.0, 'deliveryAtVideoMs': i * 100.0}
                            for i in range(count)]
        return {'evidenceType': 'pure-harness-mock-test', 'fixture': {'decodedFrames': count, 'fps': 10.0},
                'events': [], 'game': {'count': 0}, 'acknowledgedSeq': 0,
                'gameScoringMatches': True, 'gameAcknowledgmentMatches': True,
                'physicalCameraOpens': 0, 'savedOutputFrames': 0, 'uploadedFrames': 0,
                'verificationOutcome': {'status': 'observed-only'}}

    def execute(self, callback):
        with contextlib.redirect_stdout(io.StringIO()):
            return harness.execute_cohort(self.plan, self.out, callback, repo=self.root, plan_sha='test-only')

    def load(self, name):
        return json.loads((self.out / name).read_text())

    def test_partial_decode_is_saved_and_next_case_still_executes(self):
        calls = []
        def callback(item, state):
            calls.append(item['caseId'])
            return self.fake_report(item, state, 1 if item['caseId'] == 'first' else 2)
        status = self.execute(callback)
        first = self.load('first.json')
        self.assertEqual(calls, ['first', 'next'])
        self.assertEqual(len(first['rows']), 1)
        self.assertFalse(first['completeFileProcessed'])
        self.assertIn('incomplete-frozen-file', first['validationFailures'])
        self.assertEqual(self.load('next.json')['executionStatus'], 'completed')
        self.assertTrue(status['allCasesExecuted'])
        self.assertFalse(status['allExecutionChecksPassed'])
        self.assertEqual(len(self.load('summary.json')), 2)

    def test_exception_preserves_partial_rows_without_inventing_score_then_continues(self):
        def callback(item, state):
            if item['caseId'] == 'first':
                self.fake_report(item, state, 1)
                raise RuntimeError('Simulated scorer failure; no real scorer or inference')
            return self.fake_report(item, state)
        status = self.execute(callback)
        first = self.load('first.json')
        self.assertEqual(len(first['rows']), 1)
        self.assertIsNone(first['game'])
        self.assertIsNone(first['events'])
        self.assertIsNone(first['acknowledgedSeq'])
        self.assertEqual(first['exception']['type'], 'RuntimeError')
        self.assertTrue(status['allCasesExecuted'])
        self.assertEqual(self.load('next.json')['executionStatus'], 'completed')

    def test_post_case_pin_change_is_saved_and_prevents_the_next_case(self):
        calls = []
        def callback(item, state):
            calls.append(item['caseId'])
            report = self.fake_report(item, state)
            self.label.write_text('changed after first test callback')
            return report
        status = self.execute(callback)
        self.assertEqual(calls, ['first'])
        self.assertEqual(status['status'], 'unsafe-abort')
        self.assertIn('unsafe-pin-change', self.load('first.json')['validationFailures'])
        self.assertFalse((self.out / 'next.json').exists())
        self.assertEqual(len(self.load('summary.json')), 1)

    def test_preflight_pin_change_prevents_any_callback_or_output_creation(self):
        self.label.write_text('changed before any execution')
        callback = mock.Mock()
        with self.assertRaises(harness.UnsafePreflightError):
            self.execute(callback)
        callback.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_clock_disagreement_is_saved_without_retiming(self):
        def callback(item, state):
            report = self.fake_report(item, state)
            if item['caseId'] == 'first':
                state['rows'][1]['atVideoMs'] = 102.0
            return report
        self.execute(callback)
        first = self.load('first.json')
        self.assertEqual(first['rows'][1]['plannedFrameMs'], 100.0)
        self.assertEqual(first['rows'][1]['atVideoMs'], 102.0)
        self.assertIn('atVideoMs-disagrees-with-frozen-pts', first['validationFailures'])

    def test_missing_network_denial_stops_main_before_sdk_import_or_plan_read(self):
        fake_socket = mock.Mock()
        with mock.patch.object(harness, 'digest', return_value=harness.PROFILE_SHA), \
                mock.patch.object(harness.socket, 'socket', return_value=fake_socket), \
                mock.patch.object(harness, 'validate_plan') as validate:
            with self.assertRaises(harness.UnsafePreflightError):
                harness.main()
        validate.assert_not_called()
        fake_socket.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
