#!/usr/bin/env python3
"""Analyze frozen native image outputs. No inference, downloads or application edits."""
import argparse
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import uuid

MODEL_SHA = '0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab'
JOINTS = [('leftShoulder', 'left_shoulder', 5), ('rightShoulder', 'right_shoulder', 6),
          ('leftWrist', 'left_wrist', 9), ('rightWrist', 'right_wrist', 10)]
GRID = [round(.10 + i * .05, 2) for i in range(18)]
STRATA = ('primary_visible', 'occluded_v1', 'no_person_annotation')
COUNTS = {'calibration': dict(zip(STRATA, (47, 6, 20))),
          'heldout': dict(zip(STRATA, (32, 3, 20)))}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def read_json(path, expected_sha=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'regular JSON file required: ' + str(path))
    data = path.read_bytes()
    require(expected_sha is None or digest(data) == expected_sha, 'SHA mismatch: ' + str(path))
    value = json.loads(data, parse_constant=lambda token: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    return value, {'path': str(path.resolve()), 'bytes': len(data), 'sha256': digest(data)}


def cp_upper(errors, total, alpha=.05):
    """Exact one-sided Clopper-Pearson upper bound; None when denominator is zero."""
    require(type(errors) is int and type(total) is int and 0 <= errors <= total, 'binomial counts')
    if total == 0:
        return None
    if errors == total:
        return 1.0
    if errors == 0:
        return 1 - alpha ** (1 / total)
    low, high = errors / total, 1.0
    for _ in range(90):
        p = (low + high) / 2
        cdf = sum(math.comb(total, k) * p ** k * (1 - p) ** (total - k)
                  for k in range(errors + 1))
        if cdf > alpha:
            low = p
        else:
            high = p
    return (low + high) / 2


def validate_protocol(protocol):
    require(protocol['thresholdGrid'] == GRID, 'frozen threshold grid changed')
    require(protocol['model']['sha256'] == MODEL_SHA, 'frozen model changed')
    require(protocol['model']['primaryProfile'] == 'image-3pass-reset-each-image', 'profile changed')
    require(protocol['labels']['accuratePrimaryImage'].startswith('all4 required point errors<=0.10'), 'error metric changed')
    p, h = protocol['exploratorySelection'], protocol['exploratoryHeldoutAcceptance']
    require((p['minimumPrimaryAdmitted'], p['maximumEmpiricalIncorrectPrimaryFraction'],
             p['minimumCorrectPrimaryGainVersus065'], p['maximumCalibrationNoPersonAdmitted'],
             p['maximumNewIncorrectOccludedVersus065']) == (20, .05, 5, 0, 0), 'selection rules changed')
    require((h['minimumPrimaryAdmitted'], h['minimumNewCorrectPrimaryVersus065'],
             h['maximumNewIncorrectPrimaryVersus065'], h['maximumNoPersonAdmitted'],
             h['maximumNewIncorrectOccludedVersus065']) == (15, 5, 0, 0, 0), 'heldout rules changed')


def index_rows(rows, label):
    require(isinstance(rows, list), label + ' rows required')
    indexed = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('id'), str), label + ' image id')
        require(row['id'] not in indexed, label + ' duplicate image id')
        indexed[row['id']] = row
    return indexed


def validate_data(manifest, gt, review, gt_sha, review_sha):
    require(manifest.get('schemaVersion') == gt.get('schemaVersion') == review.get('schemaVersion') == 1,
            'dataset schema')
    require(manifest['humanGTSha256'] == gt_sha, 'manifest/GT binding')
    require(manifest['selectionFreezeSha256'] == gt['selectionFreezeSha256'], 'selection freeze binding')
    for name in ('backgroundReviewSha256', 'backgroundReviewedFreezeSha256'):
        if name in manifest:
            require(manifest[name] == review_sha, 'manifest/background review binding')
    images, labels = index_rows(manifest['images'], 'manifest'), index_rows(gt['images'], 'GT')
    require(images.keys() == labels.keys(), 'manifest/GT IDs differ')
    hashes, source_ids = set(), set()
    counts = {split: {s: 0 for s in STRATA} for split in COUNTS}
    for ident, image in images.items():
        truth = labels[ident]
        require(image['split'] in COUNTS and image['stratum'] in STRATA, 'unknown split/stratum')
        require(image['sha256'] not in hashes and image['sourceImageId'] not in source_ids,
                'source-image/byte duplicate, including split leakage')
        hashes.add(image['sha256']); source_ids.add(image['sourceImageId'])
        require(image['licenseId'] in (4, 5, 8), 'unsupported image license')
        require(image['asset'] == 'calibration/' + image['sha256'] + '.jpg', 'asset path')
        for key in ('split', 'stratum', 'kind', 'width', 'height'):
            require(image[key] == truth[key], 'manifest/GT mismatch: ' + key)
        require(image['sourceImageId'] == truth['imageId'], 'source image identity')
        counts[image['split']][image['stratum']] += 1
        if image['stratum'] == 'no_person_annotation':
            require(truth['kind'] == 'no-person-annotation' and not truth['joints'], 'background label contract')
            continue
        require(truth['kind'] == 'human-keypoints' and truth['numKeypoints'] >= 10
                and truth['bboxImageAreaFraction'] >= .10, 'person selection quality')
        points = truth['joints']
        visibility = []
        for _, key, index in JOINTS:
            point = points[key]
            require(all(finite(point[c]) for c in ('x', 'y')), 'nonfinite GT point')
            require(0 <= point['x'] <= image['width'] and 0 <= point['y'] <= image['height'], 'GT point bounds')
            require(type(point['visibility']) is int and point['visibility'] in (1, 2), 'missing required GT joint')
            require(truth['keypoints'][index * 3:index * 3 + 3] == [point['x'], point['y'], point['visibility']],
                    'GT point/keypoint-array mismatch')
            visibility.append(point['visibility'])
        ls, rs = points['left_shoulder'], points['right_shoulder']
        span = math.hypot(ls['x'] - rs['x'], ls['y'] - rs['y'])
        require(span >= 40 and math.isclose(span, truth['shoulderSpanPixels'], abs_tol=1e-6), 'GT shoulder span')
        require((image['stratum'] == 'primary_visible' and visibility == [2] * 4)
                or (image['stratum'] == 'occluded_v1' and 1 in visibility), 'visibility stratum')
    require(counts == COUNTS, 'frozen sample counts changed: ' + str(counts))
    require(review.get('modelBlindBeforeInference') is True, 'background review was not model-blind')
    reviews = index_rows(review['reviews'], 'background review')
    background = {i for i, x in images.items() if x['stratum'] == 'no_person_annotation'}
    require(reviews.keys() == background, 'background review IDs do not cover exact40 images')
    for ident, row in reviews.items():
        image = images[ident]
        require(row.get('noPerson') is True and row.get('decision') == 'clear_no_human', 'ambiguous background review')
        require(row['sha256'] == image['sha256'] and row['split'] == image['split']
                and row['sourceImageId'] == image['sourceImageId'], 'review image binding')
    return images, labels


def native_rows(result, images, split, manifest_sha):
    expected = {i: x for i, x in images.items() if x['split'] == split}
    require(result.get('status') == 'passed' and result.get('split') == split
            and result.get('manifestSha256') == manifest_sha and result.get('modelSha256') == MODEL_SHA,
            'native result status/split/model/manifest')
    require(result.get('cameraUsed') is False and result.get('physicalDevice') is False
            and result.get('macInference') is False, 'native evidence scope')
    run_id = result['runId']; require(str(uuid.UUID(run_id)) == run_id, 'native run UUID')
    samples = {}; kinds = {k: [] for k in ('started', 'finished', 'closed')}
    for row in result['records']:
        require(row.get('kind') in ('started', 'sample', 'finished', 'closed'), 'native failure/unknown record')
        require(row.get('runId') == run_id and row.get('manifestSha256') == manifest_sha
                and row.get('datasetId') == 'dataset-' + manifest_sha[:16] and row.get('split') == split
                and row.get('modelId') == 'float16' and row.get('modelSha256') == MODEL_SHA
                and row.get('inputSize') == 192 and row.get('engine') == 'litert'
                and row.get('engineVersion') == '1.4.2' and row.get('profile') == 'image'
                and row.get('modelInferencesPerImage') == 3 and row.get('referenceCalls') == 0
                and row.get('cameraEnabled') is False and row.get('scoringEnabled') is False
                and row.get('scoreSemantics') == 'native-movenet-joint-score-uncalibrated'
                and row.get('coordinateSemantics') == 'official-crop-inverse-source-pixels',
                'native record identity/profile')
        if row['kind'] == 'sample':
            ident = row.get('id'); require(ident in expected and ident not in samples, 'unexpected/duplicate native ID')
            image = expected[ident]
            require((row['imageSha256'], row['width'], row['height']) ==
                    (image['sha256'], image['width'], image['height']), 'native image binding')
            invalid, raw_scores, masked = 0, [], []
            for key, _, _ in JOINTS:
                p = row[key]
                require(all(finite(p.get(c)) for c in ('x', 'y', 'score', 'normalizedX', 'normalizedY',
                                                      'classifierMappedX', 'classifierMappedY', 'classifierScore')),
                        'nonfinite/missing native keypoint')
                require(0 <= p['score'] <= 1, 'native raw score bounds')
                valid = (0 <= p['normalizedX'] <= 1 and 0 <= p['normalizedY'] <= 1
                         and 0 <= p['x'] <= image['width'] and 0 <= p['y'] <= image['height'])
                if valid:
                    require(abs(p['classifierMappedX'] - p['x']) <= .001
                            and abs(p['classifierMappedY'] - p['y']) <= .001
                            and abs(p['classifierScore'] - p['score']) <= 1e-6, 'valid mapping changed')
                else:
                    invalid += 1
                    require(p['classifierMappedX'] == p['classifierMappedY'] == p['classifierScore'] == 0,
                            'invalid mapping not masked')
                raw_scores.append(p['score']); masked.append(p['classifierScore'])
            require(type(row['invalidMappedKeypoints']) is int and row['invalidMappedKeypoints'] == invalid,
                    'invalid mapping count')
            require(finite(row['minimumScore']) and abs(row['minimumScore'] - min(masked)) <= 1e-6,
                    'classifier minimum score mismatch')
            for name, value in [('rawMinimumScore', min(raw_scores)), ('classifierMinimumScore', min(masked))]:
                if name in row:
                    require(finite(row[name]) and abs(row[name] - value) <= 1e-6, name + ' mismatch')
            for name in ('preprocessMs', 'inferenceMs', 'sampleMs'):
                require(finite(row[name]) and row[name] >= 0, 'native timing')
            samples[ident] = row
        else:
            kinds[row['kind']].append(row)
    require(samples.keys() == expected.keys(), 'native requested image coverage')
    require(all(len(v) == 1 for v in kinds.values()), 'native terminal/start record count')
    require(kinds['started'][0]['expectedSamples'] == kinds['finished'][0]['samples'] ==
            kinds['closed'][0]['samples'] == len(expected), 'native batch count')
    closed = kinds['closed'][0]
    require(closed.get('complete') is True and closed.get('resourcesClosed') is True
            and closed.get('cancelled') is False and result.get('resourcesClosed') is True,
            'native incomplete/cleanup/cancelled')
    return samples


def geometry(points):
    ls, rs, lw, rw = [points[k] for k, _, _ in JOINTS]
    width = math.hypot(ls['x'] - rs['x'], ls['y'] - rs['y'])
    if width <= .00001:
        return {'class': 'invalid', 'robust': False}
    ul, ur = ls['y'] - lw['y'] - .30 * width, rs['y'] - rw['y'] - .30 * width
    dl, dr = lw['y'] - ls['y'] - .20 * width, rw['y'] - rs['y'] - .20 * width
    label, robust = 'other', False
    if dl > 0 and dr > 0:
        label, robust = 'neutral', min(dl, dr) > .24 * width
    elif ul > 0 and dr > 0:
        label, robust = 'left', ul > .26 * width and dr > .24 * width
    elif ur > 0 and dl > 0:
        label, robust = 'right', ur > .26 * width and dl > .24 * width
    elif ul > 0 and ur > 0:
        label, robust = 'both-up', min(ul, ur) > .26 * width
    return {'class': label, 'robust': robust, 'shoulderSpan': width,
            'leftRaiseMargin': ul / width, 'rightRaiseMargin': ur / width,
            'leftDownMargin': dl / width, 'rightDownMargin': dr / width}


def measurements(samples, images, labels):
    measured = []
    for ident, sample in samples.items():
        image, truth = images[ident], labels[ident]
        points = {key: sample[key] for key, _, _ in JOINTS}
        width = math.hypot(points['leftShoulder']['x'] - points['rightShoulder']['x'],
                           points['leftShoulder']['y'] - points['rightShoulder']['y'])
        row = {'id': ident, 'split': image['split'], 'stratum': image['stratum'],
               'imageSha256': image['sha256'], 'rawMinimumScore': min(p['score'] for p in points.values()),
               'invalidMappedKeypoints': sample['invalidMappedKeypoints'],
               'eligible': sample['invalidMappedKeypoints'] == 0 and width > .00001,
               'accurate': None, 'predictedGeometry': geometry(points), 'groundTruthGeometry': None,
               'keypoints': points, 'groundTruthKeypoints': {},
               'jointErrors': {}, 'jointScores': {k: p['score'] for k, p in points.items()},
               'jointVisibility': {}, 'preprocessMs': sample['preprocessMs'], 'inferenceMs': sample['inferenceMs'],
               'sampleMs': sample['sampleMs']}
        if image['stratum'] != 'no_person_annotation':
            gt_points = {key: truth['joints'][name] for key, name, _ in JOINTS}
            row['groundTruthKeypoints'] = gt_points
            row['groundTruthGeometry'] = geometry(gt_points)
            span = row['groundTruthGeometry']['shoulderSpan']
            row['jointErrors'] = {key: math.hypot(points[key]['x'] - p['x'], points[key]['y'] - p['y']) / span
                                  for key, p in gt_points.items()}
            row['jointVisibility'] = {k: p['visibility'] for k, p in gt_points.items()}
            row['accurate'] = row['eligible'] and all(e <= .10 for e in row['jointErrors'].values())
        measured.append(row)
    return measured


def admitted(row, threshold):
    return row['eligible'] and row['rawMinimumScore'] >= threshold


def statistics(rows, threshold):
    out = {'threshold': threshold, 'strata': {}}
    for stratum in STRATA:
        selected = [r for r in rows if r['stratum'] == stratum]
        accepted = [r for r in selected if admitted(r, threshold)]
        n, a = len(selected), len(accepted)
        background = stratum == 'no_person_annotation'
        errors = len(accepted) if background else sum(not r['accurate'] for r in accepted)
        correct = None if background else a - errors
        out['strata'][stratum] = {'images': n, 'admitted': a, 'correctAdmitted': correct,
            'incorrectAdmitted': errors, 'coverage': a / n if n else None,
            'incorrectFractionAmongAdmitted': None if background or a == 0 else errors / a,
            'incorrectAmongAdmittedUpper95': None if background else cp_upper(errors, a),
            'noPersonAdmissionRate': a / n if background and n else None,
            'noPersonAdmissionUpper95': cp_upper(a, n) if background else None,
            'newCorrectVersus065': 0 if background else sum(r['accurate'] and admitted(r, threshold)
                                                           and not admitted(r, .65) for r in selected),
            'newIncorrectVersus065': sum((background or not r['accurate']) and admitted(r, threshold)
                                         and not admitted(r, .65) for r in selected),
            'admittedIds': [r['id'] for r in accepted],
            'incorrectAdmittedIds': [r['id'] for r in accepted if background or not r['accurate']]}
        if not background:
            confusion = {}
            for r in accepted:
                if r['groundTruthGeometry']['robust']:
                    key = r['groundTruthGeometry']['class'] + ' -> ' + r['predictedGeometry']['class']
                    confusion[key] = confusion.get(key, 0) + 1
            out['strata'][stratum].update({
                'admittedRobustGeometryConfusion': confusion,
                'admittedBoundaryAmbiguousImages': sum(not r['groundTruthGeometry']['robust'] for r in accepted),
                'perJointCorrectAdmitted': {key: sum(r['jointErrors'][key] <= .10 for r in accepted)
                                           for key, _, _ in JOINTS}})
    return out


def quantiles(values):
    values = sorted(values)
    if not values:
        return None
    result = {'count': len(values)}
    for p in (0, .05, .25, .5, .75, .95, 1):
        at = p * (len(values) - 1); lo, hi = math.floor(at), math.ceil(at)
        result[str(p)] = values[lo] + (values[hi] - values[lo]) * (at - lo)
    return result


def distributions(rows):
    return {stratum: {'rawFourJointMinimum': quantiles([r['rawMinimumScore'] for r in rows if r['stratum'] == stratum]),
        'joints': {key: {'score': quantiles([r['jointScores'][key] for r in rows if r['stratum'] == stratum]),
                        'normalizedPointError': quantiles([r['jointErrors'][key] for r in rows
                                                         if r['stratum'] == stratum and key in r['jointErrors']])}
                   for key, _, _ in JOINTS}} for stratum in STRATA}


def choose(rows):
    baseline = statistics(rows, .65)
    table = []
    for threshold in GRID:
        stats = statistics(rows, threshold)
        p, o, b = [stats['strata'][s] for s in STRATA]
        bp = baseline['strata']['primary_visible']
        reasons = []
        for condition, reason in [(p['admitted'] >= 20, 'primary admitted <20'),
                (20 * p['incorrectAdmitted'] <= p['admitted'], 'empirical primary incorrect fraction >5%'),
                (p['correctAdmitted'] - bp['correctAdmitted'] >= 5, 'correct primary gain <5'),
                (b['admitted'] == 0, 'background admission'),
                (o['newIncorrectVersus065'] == 0, 'new incorrect occluded admission')]:
            if not condition:
                reasons.append(reason)
        stats['selectionFeasible'] = not reasons; stats['selectionRejections'] = reasons
        table.append(stats)
    feasible = [s for s in table if s['selectionFeasible']]
    selected = max(feasible, key=lambda s: (s['strata']['primary_visible']['correctAdmitted'], s['threshold'])) if feasible else None
    return baseline, table, selected


def evaluate_heldout(rows, threshold):
    baseline = statistics(rows, .65)
    if threshold is None:
        return {'status': 'baseline-only-no-calibration-candidate', 'baseline': baseline,
                'candidate': None, 'pilotAccepted': False, 'thresholdRetuned': False}
    candidate = statistics(rows, threshold)
    p, o, b = [candidate['strata'][s] for s in STRATA]
    checks = {'primaryAdmittedAtLeast15': p['admitted'] >= 15,
              'newCorrectPrimaryAtLeast5': p['newCorrectVersus065'] >= 5,
              'noNewIncorrectPrimary': p['newIncorrectVersus065'] == 0,
              'noBackgroundAdmission': b['admitted'] == 0,
              'noNewIncorrectOccluded': o['newIncorrectVersus065'] == 0}
    return {'status': 'pilot-passed' if all(checks.values()) else 'pilot-rejected',
            'baseline': baseline, 'candidate': candidate, 'checks': checks,
            'pilotAccepted': all(checks.values()), 'thresholdRetuned': False,
            'productionCertified': False, 'productionRiskCriterionPossibleWithThisSample': False}


def write_csvs(out, rows):
    image_fields = ['id', 'split', 'stratum', 'imageSha256', 'rawMinimumScore', 'invalidMappedKeypoints',
                    'eligible', 'accurate', 'predictedClass', 'gtClass', 'gtClassRobust', 'preprocessMs', 'inferenceMs', 'sampleMs']
    with (out / 'images.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=image_fields); writer.writeheader()
        for r in rows:
            flat = {k: r.get(k) for k in image_fields}
            flat['predictedClass'] = r['predictedGeometry']['class']
            flat['gtClass'] = (r['groundTruthGeometry'] or {}).get('class')
            flat['gtClassRobust'] = (r['groundTruthGeometry'] or {}).get('robust')
            writer.writerow(flat)
    with (out / 'joints.csv').open('w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['id', 'split', 'stratum', 'joint', 'rawScore',
            'predictedX', 'predictedY', 'groundTruthX', 'groundTruthY', 'normalizedPointError', 'visibility'])
        for r in rows:
            for key, _, _ in JOINTS:
                point, truth = r['keypoints'][key], r['groundTruthKeypoints'].get(key, {})
                writer.writerow([r['id'], r['split'], r['stratum'], key, r['jointScores'][key],
                                 point['x'], point['y'], truth.get('x'), truth.get('y'),
                                 r['jointErrors'].get(key), r['jointVisibility'].get(key)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('select', 'heldout'))
    for name in ('protocol', 'manifest', 'gt', 'absence-review', 'native'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--selection-sha256')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    objects, bindings = {}, {}
    for name in ('protocol', 'manifest', 'gt', 'absence_review'):
        objects[name], bindings[name] = read_json(getattr(args, name), getattr(args, name + '_sha256'))
    validate_protocol(objects['protocol'])
    declared_manifest = objects['protocol']['data'].get('datasetManifestSha256')
    require(declared_manifest is None or declared_manifest == bindings['manifest']['sha256'],
            'bound protocol/dataset manifest mismatch')
    images, labels = validate_data(objects['manifest'], objects['gt'], objects['absence_review'],
                                   bindings['gt']['sha256'], bindings['absence_review']['sha256'])
    split = 'calibration' if args.mode == 'select' else 'heldout'
    selection = None
    if args.mode == 'heldout':
        require(args.selection is not None and args.selection_sha256 is not None, 'heldout requires frozen selection +SHA')
        selection, bindings['selection'] = read_json(args.selection, args.selection_sha256)
        require(selection.get('schemaVersion') == 1 and selection.get('frozenBeforeHeldout') is True
                and selection.get('modelSha256') == MODEL_SHA and selection.get('profile') == 'image-3pass-reset-each-image',
                'selection envelope identity')
        require(selection.get('scriptSha256') == digest(Path(__file__).read_bytes()), 'analysis script changed after freeze')
        for name in ('protocol', 'manifest', 'gt', 'absence_review'):
            require(selection['bindings'][name]['sha256'] == bindings[name]['sha256'], 'heldout/freeze binding: ' + name)
        for name, declared_split in (('calibrationIds', 'calibration'), ('heldoutIds', 'heldout')):
            ids = selection.get(name)
            expected_ids = {i for i, image in images.items() if image['split'] == declared_split}
            require(isinstance(ids, list) and len(ids) == len(set(ids)) and set(ids) == expected_ids,
                    'selection exact split IDs: ' + name)
        threshold = selection['selectedThreshold']
        require(threshold is None or threshold in GRID, 'frozen threshold not in grid')
    objects['native'], bindings['native'] = read_json(args.native, args.native_sha256)
    samples = native_rows(objects['native'], images, split, bindings['manifest']['sha256'])
    rows = measurements(samples, images, labels)
    report = {'schemaVersion': 1, 'mode': args.mode, 'bindings': bindings,
              'modelSha256': MODEL_SHA, 'profile': 'image-3pass-reset-each-image',
              'scope': 'Actual Android static-image outputs analyzed offline; not gesture/UI or device acceptance',
              'statisticalUnit': 'original source image, never individual joints or repeated video frames',
              'uncertaintyScope': 'Exact intervals use a Bernoulli image sampling model; curated COCO data and unknown subject overlap do not establish deployment risk or score probabilities. Background and person prevalence are not pooled.',
              'productionCertified': False, 'scoreAndErrorDistributions': distributions(rows),
              'rawScoresRemapped': False, 'geometryOrTimingChanged': False,
              'createdAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'images': rows}
    args.out.mkdir(parents=True, exist_ok=True)
    require(not any(args.out.iterdir()), 'output directory must be empty; preserve prior evidence')
    frozen_bytes = None
    if args.mode == 'select':
        baseline, table, selected = choose(rows)
        report.update({'baseline': baseline, 'thresholdTable': table,
                       'selectedThreshold': selected['threshold'] if selected else None})
        with (args.out / 'thresholds.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['threshold', 'primaryAdmitted', 'primaryCorrect', 'primaryIncorrect', 'primaryErrorUpper95',
                             'occludedNewIncorrect', 'backgroundAdmitted', 'backgroundUpper95', 'feasible', 'rejections'])
            for s in table:
                p, o, b = [s['strata'][t] for t in STRATA]
                writer.writerow([s['threshold'], p['admitted'], p['correctAdmitted'], p['incorrectAdmitted'],
                                 p['incorrectAmongAdmittedUpper95'], o['newIncorrectVersus065'], b['admitted'],
                                 b['noPersonAdmissionUpper95'], s['selectionFeasible'], '; '.join(s['selectionRejections'])])
        frozen = {'schemaVersion': 1, 'frozenBeforeHeldout': True, 'createdAtUtc': report['createdAtUtc'],
                  'modelSha256': MODEL_SHA, 'profile': report['profile'], 'bindings': bindings,
                  'scriptSha256': digest(Path(__file__).read_bytes()),
                  'calibrationIds': list(samples), 'heldoutIds': [i for i, x in images.items() if x['split'] == 'heldout'],
                  'selectedThreshold': report['selectedThreshold'], 'selectionReason': 'fixed-calibration-rule' if selected else 'no-feasible-calibration-threshold',
                  'productionDefaultUnchanged': .65}
        frozen_bytes = encoded(frozen)
        report['selectionFreeze'] = {'path': str((args.out / 'selection.freeze.json').resolve()),
                                    'bytes': len(frozen_bytes), 'sha256': digest(frozen_bytes)}
    else:
        report['evaluation'] = evaluate_heldout(rows, selection['selectedThreshold'])
    write_csvs(args.out, rows)
    with (args.out / 'analysis.json').open('xb') as stream:
        stream.write(encoded(report))
    # Publish the selection token last, after all calibration evidence succeeds.
    if frozen_bytes is not None:
        with (args.out / 'selection.freeze.json').open('xb') as stream:
            stream.write(frozen_bytes)
    print(json.dumps({'mode': args.mode, 'images': len(rows), 'selectedThreshold': report.get('selectedThreshold'),
                      'selectionSha256': report.get('selectionFreeze', {}).get('sha256'),
                      'status': report.get('evaluation', {}).get('status'), 'out': str(args.out)}))


if __name__ == '__main__':
    main()
