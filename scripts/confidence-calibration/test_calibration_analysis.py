"""Synthetic analysis-contract tests. No photos, model, Android or actual heldout output."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('analysis', HERE / 'analyze_calibration.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


def data_fixture():
    manifest = {'schemaVersion': 1, 'selectionFreezeSha256': '1' * 64, 'images': []}
    gt = {'schemaVersion': 1, 'selectionFreezeSha256': '1' * 64, 'images': []}
    review = {'schemaVersion': 1, 'modelBlindBeforeInference': True, 'reviews': []}
    for split, counts in a.COUNTS.items():
        for stratum, count in counts.items():
            for index in range(count):
                ident = split + '_' + stratum + '_' + str(index)
                image_id = len(manifest['images']) + 1
                sha = a.digest(ident.encode())
                background = stratum == 'no_person_annotation'
                image = {'id': ident, 'split': split, 'stratum': stratum, 'sourceImageId': image_id,
                         'sha256': sha, 'asset': 'calibration/' + sha + '.jpg', 'bytes': 100,
                         'licenseId': 4, 'width': 640, 'height': 480,
                         'kind': 'no-person-annotation' if background else 'human-keypoints'}
                manifest['images'].append(image)
                points, keypoints = {}, [0] * 51
                coordinates = [(350, 150), (250, 150), (350, 300), (250, 300)]
                for j, ((_, key, coco), (x, y)) in enumerate(zip(a.JOINTS, coordinates)):
                    v = 1 if stratum == 'occluded_v1' and j == 0 else 2
                    points[key] = {'x': x, 'y': y, 'visibility': v}
                    keypoints[coco * 3:coco * 3 + 3] = [x, y, v]
                truth = {k: image[k] for k in ('id', 'split', 'stratum', 'kind', 'width', 'height')}
                truth.update({'imageId': image_id, 'joints': {} if background else points,
                              'keypoints': [] if background else keypoints, 'numKeypoints': 0 if background else 17,
                              'bboxImageAreaFraction': None if background else .2,
                              'shoulderSpanPixels': None if background else 100.0})
                gt['images'].append(truth)
                if background:
                    review['reviews'].append({'id': ident, 'sourceImageId': image_id, 'sha256': sha,
                                              'split': split, 'decision': 'clear_no_human', 'noPerson': True})
    manifest['humanGTSha256'] = a.digest(a.encoded(gt))
    return manifest, gt, review


def native_fixture(manifest, split):
    manifest_sha = a.digest(a.encoded(manifest)); run_id = str(uuid.uuid4())
    common = {'runId': run_id, 'manifestSha256': manifest_sha, 'datasetId': 'dataset-' + manifest_sha[:16],
              'split': split, 'modelId': 'float16', 'modelSha256': a.MODEL_SHA, 'inputSize': 192,
              'engine': 'litert', 'engineVersion': '1.4.2', 'profile': 'image', 'modelInferencesPerImage': 3,
              'referenceCalls': 0, 'cameraEnabled': False, 'scoringEnabled': False,
              'scoreSemantics': 'native-movenet-joint-score-uncalibrated',
              'coordinateSemantics': 'official-crop-inverse-source-pixels'}
    images = [x for x in manifest['images'] if x['split'] == split]
    records = [dict(common, kind='started', expectedSamples=len(images))]
    for image in images:
        idx = int(image['id'].rsplit('_', 1)[-1])
        if image['stratum'] == 'no_person_annotation':
            score = .2
        elif image['stratum'] == 'occluded_v1':
            score = .5
        else:
            score = .75 if idx < 20 else .5
        row = dict(common, kind='sample', id=image['id'], imageSha256=image['sha256'],
                   width=640, height=480, minimumScore=score, classifierMinimumScore=score,
                   rawMinimumScore=score, invalidMappedKeypoints=0,
                   preprocessMs=2.0, inferenceMs=45.0, sampleMs=49.0)
        for (key, _, _), (x, y) in zip(a.JOINTS, [(350, 150), (250, 150), (350, 300), (250, 300)]):
            row[key] = {'x': x, 'y': y, 'score': score, 'normalizedX': x / 640, 'normalizedY': y / 480,
                        'classifierMappedX': x, 'classifierMappedY': y, 'classifierScore': score}
        records.append(row)
    records += [dict(common, kind='finished', samples=len(images)),
                dict(common, kind='closed', samples=len(images), complete=True, resourcesClosed=True, cancelled=False)]
    return {'status': 'passed', 'split': split, 'manifestSha256': manifest_sha, 'modelSha256': a.MODEL_SHA,
            'runId': run_id, 'cameraUsed': False, 'physicalDevice': False, 'macInference': False,
            'records': records, 'resourcesClosed': True}


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.gt, self.review = data_fixture()
        self.native = native_fixture(self.manifest, 'calibration')
        self.images = {r['id']: r for r in self.manifest['images']}
        self.labels = {r['id']: r for r in self.gt['images']}

    def rows(self, native=None, split='calibration'):
        records = a.native_rows(native or self.native, self.images, split, a.digest(a.encoded(self.manifest)))
        return a.measurements(records, self.images, self.labels)

    def validate(self, manifest=None, gt=None, review=None):
        return a.validate_data(manifest or self.manifest, gt or self.gt, review or self.review,
                               a.digest(a.encoded(self.gt)), a.digest(a.encoded(self.review)))

    def test_exact_bounds_and_zero_denominator(self):
        self.assertAlmostEqual(a.cp_upper(0, 32), .0893681989862648)
        self.assertAlmostEqual(a.cp_upper(0, 20), .13910834066826516)
        self.assertAlmostEqual(a.cp_upper(1, 10), .3941633024365047)
        self.assertEqual(a.cp_upper(10, 10), 1)
        self.assertIsNone(a.cp_upper(0, 0))
        self.assertGreater(a.cp_upper(0, 58), .05)
        self.assertLessEqual(a.cp_upper(0, 59), .05)

    def test_dataset_and_review_contract(self):
        self.validate()
        m = copy.deepcopy(self.manifest); m['images'][70]['sha256'] = m['images'][0]['sha256']
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.validate(manifest=m)
        r = copy.deepcopy(self.review); r['reviews'][0]['decision'] = 'ambiguous'
        with self.assertRaisesRegex(ValueError, 'ambiguous'): self.validate(review=r)
        r = copy.deepcopy(self.review); r['reviews'].pop()
        with self.assertRaisesRegex(ValueError, 'exact40'): self.validate(review=r)
        g = copy.deepcopy(self.gt); g['images'][0]['joints']['left_wrist']['x'] += 1
        with self.assertRaisesRegex(ValueError, 'keypoint-array'): self.validate(gt=g)

    def test_native_coverage_identity_and_minimum_fail_closed(self):
        self.assertEqual(len(self.rows()), 73)
        cases = []
        n = copy.deepcopy(self.native); n['records'].append(copy.deepcopy(n['records'][1])); cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['modelSha256'] = '0' * 64; cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['rawMinimumScore'] = .9; cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['imageSha256'] = '0' * 64; cases.append(n)
        n = copy.deepcopy(self.native); n['records'][-1]['complete'] = False; cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['leftWrist']['classifierMappedX'] += 1; cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['leftWrist']['score'] = float('nan'); cases.append(n)
        n = copy.deepcopy(self.native); n['records'][1]['id'] = 'heldout_primary_visible_0'; cases.append(n)
        for i, n in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError): self.rows(n)

    def test_high_raw_score_does_not_override_coordinate_error(self):
        n = copy.deepcopy(self.native); sample = n['records'][1]
        sample['leftWrist']['x'] += 100; sample['leftWrist']['classifierMappedX'] += 100
        sample['leftWrist']['normalizedX'] += 100 / 640
        row = self.rows(n)[0]
        self.assertTrue(a.admitted(row, .65)); self.assertFalse(row['accurate'])
        self.assertEqual(row['jointErrors']['leftWrist'], 1)

    def test_invalid_mapping_retains_raw_score_but_cannot_admit(self):
        n = copy.deepcopy(self.native); sample = n['records'][1]
        sample['leftWrist'].update(normalizedX=1.2, classifierMappedX=0, classifierMappedY=0, classifierScore=0)
        sample.update(invalidMappedKeypoints=1, minimumScore=0, classifierMinimumScore=0)
        row = self.rows(n)[0]
        self.assertEqual(row['rawMinimumScore'], .75)
        self.assertFalse(row['eligible']); self.assertFalse(a.admitted(row, .1))

    def test_raw_float_score_below_boundary_is_not_rounded_into_admission(self):
        n = copy.deepcopy(self.native); sample = n['records'][1]
        value = .6499999761581421
        for key, _, _ in a.JOINTS:
            sample[key]['score'] = sample[key]['classifierScore'] = value
        sample['minimumScore'] = sample['rawMinimumScore'] = sample['classifierMinimumScore'] = value
        row = self.rows(n)[0]
        self.assertLess(row['rawMinimumScore'], .65)
        self.assertFalse(a.admitted(row, .65)); self.assertTrue(a.admitted(row, .6))

    def test_calibration_selection_and_conservative_tie_break(self):
        baseline, table, chosen = a.choose(self.rows())
        self.assertEqual(len(table), 18); self.assertEqual(chosen['threshold'], .5)
        self.assertEqual(baseline['strata']['primary_visible']['correctAdmitted'], 20)
        self.assertEqual(chosen['strata']['primary_visible']['correctAdmitted'], 47)
        self.assertEqual(chosen['strata']['no_person_annotation']['admitted'], 0)

    def test_hard_background_can_reject_all_thresholds(self):
        rows = self.rows()
        for row in rows:
            if row['stratum'] == 'no_person_annotation': row['rawMinimumScore'] = .99
        self.assertIsNone(a.choose(rows)[2])

    def test_heldout_frozen_candidate_and_new_error_rejection(self):
        n = native_fixture(self.manifest, 'heldout'); rows = self.rows(n, 'heldout')
        good = a.evaluate_heldout(rows, .5)
        self.assertTrue(good['pilotAccepted']); self.assertFalse(good['productionCertified'])
        late = copy.deepcopy(rows); next(r for r in late if r['id'] == 'heldout_primary_visible_20')['accurate'] = False
        self.assertFalse(a.evaluate_heldout(late, .5)['pilotAccepted'])
        self.assertFalse(a.evaluate_heldout(rows, None)['pilotAccepted'])
        self.assertIsNone(a.evaluate_heldout(rows, None)['candidate'])

    def test_cli_freeze_and_heldout_binding_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sources = {'protocol': json.loads((HERE / 'protocol.json').read_text()),
                'manifest': self.manifest, 'gt': self.gt, 'absence-review': self.review, 'native': self.native}
            arguments = []
            for name, obj in sources.items():
                path = root / (name + '.json'); path.write_bytes(a.encoded(obj))
                arguments += ['--' + name, str(path), '--' + name + '-sha256', a.digest(path.read_bytes())]
            script = str(HERE / 'analyze_calibration.py')
            completed = subprocess.run([sys.executable, script, 'select', *arguments, '--out', str(root / 'select')], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            freeze = root / 'select/selection.freeze.json'; envelope = json.loads(freeze.read_text())
            self.assertEqual(envelope['selectedThreshold'], .5)
            self.assertTrue(envelope['frozenBeforeHeldout'])
            held = root / 'held-native.json'; held.write_bytes(a.encoded(native_fixture(self.manifest, 'heldout')))
            held_args = list(arguments); i = held_args.index('--native'); held_args[i + 1] = str(held)
            i = held_args.index('--native-sha256'); held_args[i + 1] = a.digest(held.read_bytes())
            command = [sys.executable, script, 'heldout', *held_args, '--selection', str(freeze),
                       '--selection-sha256', a.digest(freeze.read_bytes()), '--out', str(root / 'held')]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads((root / 'held/analysis.json').read_text())
            self.assertTrue(report['evaluation']['pilotAccepted']); self.assertNotIn('thresholdTable', report)
            variants = []
            changed = copy.deepcopy(envelope); changed['bindings']['manifest']['sha256'] = '0' * 64
            variants.append((changed, 'heldout/freeze binding'))
            changed = copy.deepcopy(envelope); changed['scriptSha256'] = '0' * 64
            variants.append((changed, 'analysis script changed'))
            changed = copy.deepcopy(envelope); changed['heldoutIds'].pop()
            variants.append((changed, 'selection exact split IDs'))
            changed = copy.deepcopy(envelope); changed['calibrationIds'].append(changed['calibrationIds'][0])
            variants.append((changed, 'selection exact split IDs'))
            for number, (changed, error) in enumerate(variants):
                freeze.write_bytes(a.encoded(changed))
                command[command.index('--selection-sha256') + 1] = a.digest(freeze.read_bytes())
                command[command.index('--out') + 1] = str(root / ('bad' + str(number)))
                # Prove freeze checks precede even opening the heldout prediction file.
                command[command.index('--native') + 1] = str(root / 'nonexistent-heldout.json')
                completed = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(error, completed.stderr)


if __name__ == '__main__':
    unittest.main()
