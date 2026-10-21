"""Read-only frozen-label/scalar-result analysis; no SDK or media imports."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

E = Path(__file__).resolve().parent.parent
R = Path('/Users/frank/mygit/sway-and-sprout')
PLAN_SHA = 'fb84346ad034457d469ff7963f54ec3e518be2675f39ac7aedfbf37cf389f73b'
NAMES = ('left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist')


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def groups(indices, times):
    runs = []
    for i in indices:
        if runs and runs[-1][-1] + 1 == i:
            runs[-1].append(i)
        else:
            runs.append([i])
    return [{'firstFrame': run[0], 'lastFrame': run[-1], 'samples': len(run),
             'closedFirstToLastMs': times[run[-1]] - times[run[0]]} for run in runs]


def geometry(obs, width, height):
    if obs is None:
        return None
    for name in NAMES:
        p = obs[name]
        if (not all(math.isfinite(p[k]) for k in ('x', 'y', 'confidence'))
                or not 0 <= p['confidence'] <= 1 or not 0 <= p['x'] < width or not 0 <= p['y'] < height
                or p['x'] == p['y'] == p['confidence'] == 0):
            return None
    ls, rs, lw, rw = [obs[n] for n in NAMES]
    span = math.hypot(ls['x'] - rs['x'], ls['y'] - rs['y'])
    if span <= .00001:
        return None
    def gate(wrist, shoulder):
        return ('up' if wrist['y'] < shoulder['y'] - .30 * span else
                'down' if wrist['y'] > shoulder['y'] + .20 * span else 'transition')
    return {'left': gate(lw, ls), 'right': gate(rw, rs)}


def main():
    pp = E / 'execution-plan.freeze.json'
    assert digest(pp) == PLAN_SHA
    plan = read(pp)
    # These 71 immutable files are verified, never rewritten by this analysis.
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256'], pin['path']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256'], pin['path']
    assert plan['definitePositiveOpportunities'] == 0
    cases = []
    for case in plan['cases']:
        path = E / 'full-results' / (case['caseId'] + '.json')
        result = read(path)
        labels = read(case['normalizedLabelsPath'])['perFrame']
        rows = result['rows']
        assert result['planSha256'] == PLAN_SHA
        assert len(rows) == len(labels) == case['frames']
        assert result['executionStatus'] == 'completed' and not result['validationFailures']
        assert result['completeFileProcessed'] and result['modelClosed']
        assert result['humanConfirmed'] is False and result['annotationAuthorType'] == 'AI'
        counts = Counter()
        phase_pairs, weak_joints = Counter(), Counter()
        incompatibilities, negative_conflicts, unavailable_geometry = [], [], []
        negative_indices, admitted_negative_indices = [], []
        single_indices = {'left': [], 'right': []}
        admitted_single_indices = {'left': [], 'right': []}
        gate_matches = {'left': Counter(), 'right': Counter()}
        singleton_pairs = Counter()
        scores = {name: [] for name in NAMES}
        clock_errors = []
        for row, label in zip(rows, labels):
            i = row['frame']
            assert i == label['frame']
            for field in ('atVideoMs', 'serviceObservationMs', 'deliveryAtVideoMs'):
                clock_errors.append(abs(row[field] - case['displayPtsMs'][i]))
            obs = row['observationWorkingPixels']
            if obs is not None:
                for name in NAMES:
                    scores[name].append(obs[name]['confidence'])
                    if not .65 <= obs[name]['confidence'] <= 1:
                        weak_joints[name] += 1
            admitted = (row['inferenceStatus'] == 'tracking' and obs is not None
                        and all(math.isfinite(obs[name]['confidence']) and .65 <= obs[name]['confidence'] <= 1
                                for name in NAMES)
                        and .65 <= obs['confidence'] <= 1)
            g = geometry(obs, row['inferenceImageWidth'], row['inferenceImageHeight'])
            admitted = admitted and g is not None
            counts['admittedFrames'] += admitted
            counts['abstainedFrames'] += not admitted
            counts['noObservationFrames'] += obs is None
            counts['validGeometryFrames'] += g is not None
            allowed = label['allowedGatesFullWorking']
            singletons = all(len(allowed[s]) == 1 for s in ('left', 'right'))
            singleton_pairs['physicalFrames'] += singletons
            for side in ('left', 'right'):
                gate_matches[side]['physicallySingletonFrames'] += len(allowed[side]) == 1
            counts['negativeSamples'] += label['poseDefinitelyNegativeBothCoordinateSpaces']
            if label['poseDefinitelyNegativeBothCoordinateSpaces']:
                negative_indices.append(i)
                counts['negativeAdmittedFrames'] += admitted
                if admitted:
                    admitted_negative_indices.append(i)
            if g is None:
                unavailable_geometry.append(i)
                continue
            phase_pairs[g['left'] + '/' + g['right']] += 1
            if singletons:
                singleton_pairs['validPredictionFrames'] += 1
                singleton_pairs['matchingFrames'] += all(g[s] == allowed[s][0] for s in ('left', 'right'))
                singleton_pairs['admittedFrames'] += admitted
            for side in ('left', 'right'):
                if len(allowed[side]) == 1:
                    gate_matches[side]['validPredictions'] += 1
                    gate_matches[side]['matchingPredictions'] += g[side] == allowed[side][0]
            bad = [s for s in ('left', 'right') if g[s] not in allowed[s]]
            if bad:
                incompatibilities.append({'frame': i, 'sourceFrame': label['sourceFrame'], 'sides': bad,
                                          'predicted': g, 'allowed': allowed, 'admitted': admitted})
            source_g = geometry(row.get('derivedObservationSourcePixels'), row['sourceImageWidth'], row['sourceImageHeight'])
            counts['workingVersusSourceGatePairDifferences'] += source_g != g
            raised = ('left' if g == {'left': 'up', 'right': 'down'} else
                      'right' if g == {'left': 'down', 'right': 'up'} else None)
            if raised is not None:
                single_indices[raised].append(i)
                if admitted:
                    admitted_single_indices[raised].append(i)
                if label['poseDefinitelyNegativeBothCoordinateSpaces']:
                    negative_conflicts.append({'frame': i, 'sourceFrame': label['sourceFrame'],
                                               'side': raised, 'admitted': admitted})
        assert max(clock_errors) <= case['streamTickMs']
        assert counts['negativeSamples'] == case['poseNegativeSamples']
        assert counts['admittedFrames'] + counts['abstainedFrames'] == case['frames']
        negative_runs = groups(negative_indices, case['displayPtsMs'])
        cases.append({'caseId': case['caseId'], 'frames': case['frames'], 'fps': case['fps'],
                      'bindings': {'rawResult': {'path': str(path), 'sha256': digest(path)},
                                   'normalizedLabels': {'path': case['normalizedLabelsPath'], 'sha256': digest(case['normalizedLabelsPath'])}},
                      'expectationKnown': case['expectationKnown'], 'expectedGestures': case['expectedGestures'],
                      'rawVerificationOutcome': result['verificationOutcome'], 'executionStatus': result['executionStatus'],
                      'events': result['events'], 'actualJsScore': result['game']['count'], 'ack': result['acknowledgedSeq'],
                      'counts': dict(counts), 'inferenceStatuses': result['inferenceStatuses'],
                      'classifierStatuses': result['classifierStatuses'], 'weakJointFrameCounts': dict(weak_joints),
                      'classifierArmedFrames': sum(bool(row['classifier']['armed']) for row in rows),
                      'classifierMaximumHeldMs': max(row['classifier']['heldMs'] for row in rows),
                      'scoreSummary': {name: {'samples': len(v), 'minimum': min(v) if v else None,
                                              'median': statistics.median(v) if v else None} for name, v in scores.items()},
                      'geometry': {'workingPixelGatePairs': dict(phase_pairs), 'singletonGatePairs': dict(singleton_pairs),
                                   'perSideSingletonAgreement': {s: dict(v) for s, v in gate_matches.items()},
                                   'incompatibilitiesWithAllowedSets': incompatibilities,
                                   'unavailableGeometryFrames': unavailable_geometry,
                                   'singleArmRunsIgnoringConfidence': {s: groups(v, case['displayPtsMs']) for s, v in single_indices.items()},
                                   'admittedSingleArmRuns': {s: groups(v, case['displayPtsMs']) for s, v in admitted_single_indices.items()},
                                   'negativeFrameSingleArmConflicts': negative_conflicts},
                      'negativeExposure': {'sampleBins': len(negative_indices), 'sampleBinSeconds': len(negative_indices) / case['fps'],
                                           'sampleRuns': negative_runs,
                                           'sumClosedFirstToLastSeconds': sum(x['closedFirstToLastMs'] for x in negative_runs) / 1000,
                                           'noContinuousSubframeMotionClaim': True},
                      'clock': {'fixtureFps': result['fixture']['fps'], 'frozenFps': case['fps'],
                                'maximumTracePtsErrorMs': max(clock_errors), 'allowedStreamTickMs': case['streamTickMs']},
                      'timing': {k: result[k] for k in ('inferenceMedianMs', 'processingSeconds', 'modelInitializationMs', 'caseWallSecondsIncludingInitialization')},
                      'modelClosed': result['modelClosed'], 'previewCacheCleared': result['previewCacheCleared']})
    total = {'frames': sum(c['frames'] for c in cases),
             'admittedFrames': sum(c['counts']['admittedFrames'] for c in cases),
             'abstainedFrames': sum(c['counts']['abstainedFrames'] for c in cases),
             'validGeometryFrames': sum(c['counts']['validGeometryFrames'] for c in cases),
             'negativeSamples': sum(c['counts']['negativeSamples'] for c in cases),
             'negativeAdmittedFrames': sum(c['counts']['negativeAdmittedFrames'] for c in cases),
             'negativeSampleBinSeconds': sum(c['negativeExposure']['sampleBinSeconds'] for c in cases),
             'negativeClosedFirstToLastSeconds': sum(c['negativeExposure']['sumClosedFirstToLastSeconds'] for c in cases),
             'uniqueEmittedEvents': sum(len(c['events']) for c in cases),
             'pointGateIncompatibilities': sum(len(c['geometry']['incompatibilitiesWithAllowedSets']) for c in cases),
             'negativeFrameSingleArmConflicts': sum(len(c['geometry']['negativeFrameSingleArmConflicts']) for c in cases)}
    report = {'schemaVersion': 1, 'scope': 'Independent read-only Full analysis; no inference, retuning or label edits',
              'planSha256': PLAN_SHA, 'frozenFilesReverified': len(plan['frozenFiles']),
              'sourcePinsReverified': len(plan['sourcePins']),
              'annotationAuthorType': 'AI', 'humanConfirmed': False, 'preliminaryDiagnosticOnly': True,
              'definitePositiveOpportunities': 0, 'eventRecall': None, 'eventRecallReason': 'unestimable: zero definite physical positives',
              'eventPrecision': None, 'eventPrecisionReason': 'unestimable: zero emitted events',
              'eventTimingAgreement': 'not applicable: no emitted events or definite positive opportunities',
              'confidenceMeaning': 'Full min(visibility,presence), global0.65 task-admission bound; neither calibrated correctness probability nor MoveNet-equivalent score',
              'geometryMethod': 'Recompute strict .30/.20 gates without confidence from finite in-image non-sentinel points. Check exclusion by frozen working-coordinate allowed gate sets. Broad AI bounds permit non-contradiction only, not point accuracy. Zero sentinel conservatively marks unavailable geometry.',
              'negativeExposurePolicy': plan['analysisPolicy']['negativeExposure'],
              'generalFalsePositiveRateEstimate': False, 'totals': total, 'cases': cases,
              'limitations': ['Only both-press has a proved whole-case zero expectation; the two other cases are observed-only.',
                              'No observed events means zero definite/unresolved emissions here, not demonstrated positive recognition.',
                              'Frames and source derivatives are correlated; no population accuracy or false-positive-rate claim.',
                              'Mac Python timing includes adapter work and separately reported initialization; no native/Fire TV speed comparison.',
                              'No browser rendering or live-user acceptance was exercised by Full headless scoring.']}
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256']
    dest = Path(__file__).parent / 'full-analysis.json'
    dest.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(total))


if __name__ == '__main__':
    main()
