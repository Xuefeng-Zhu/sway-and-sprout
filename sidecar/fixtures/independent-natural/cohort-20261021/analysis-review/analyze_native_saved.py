"""Analyze saved native scalar evidence only; imports no inference/media runtimes."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from analyze_full import E, R, PLAN_SHA, digest, groups, read

POINTS = {'left_shoulder': 'ls', 'right_shoulder': 'rs', 'left_wrist': 'lw', 'right_wrist': 'rw'}


def geometry(row, dimensions):
    width, height = dimensions
    for short in POINTS.values():
        x, y, score = (row[short + k] for k in ('X', 'Y', 'Score'))
        if (not all(math.isfinite(v) for v in (x, y, score))
                or not 0 <= score <= 1 or not 0 <= x <= width or not 0 <= y <= height
                or x == y == score == 0):
            return None
    span = math.hypot(row['lsX'] - row['rsX'], row['lsY'] - row['rsY'])
    if span <= .00001:
        return None
    def gate(wrist, shoulder):
        return ('up' if row[wrist + 'Y'] < row[shoulder + 'Y'] - .30 * span else
                'down' if row[wrist + 'Y'] > row[shoulder + 'Y'] + .20 * span else 'transition')
    return {'left': gate('lw', 'ls'), 'right': gate('rw', 'rs')}


def main():
    plan_path = E / 'execution-plan.freeze.json'
    assert digest(plan_path) == PLAN_SHA
    plan = read(plan_path)
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256'], pin['path']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256'], pin['path']
    bindings, cases = [], []
    for case in plan['cases']:
        path = E / 'movenet-results' / (case['caseId'] + '.json')
        result = read(path)
        log = Path(result['nativeScalarLog']['path'])
        summary = Path(result['nativeSummaryLog']['path'])
        for input_path in (path, log, summary):
            bindings.append({'path': str(input_path), 'sha256': digest(input_path)})
        assert digest(log) == result['nativeScalarLog']['sha256']
        assert digest(summary) == result['nativeSummaryLog']['sha256']
        rows = [json.loads(line) for line in log.read_text().splitlines() if line]
        labels = read(case['normalizedLabelsPath'])['perFrame']
        indices = [row['frameIndex'] for row in rows]
        assert len(indices) == len(set(indices))
        assert all(0 <= i < case['frames'] for i in indices)
        assert indices == sorted(indices)
        missing = sorted(set(range(case['frames'])) - set(indices))
        status, counts, weak_joints = Counter(), Counter(), Counter()
        pairs, singleton_pairs = Counter(), Counter()
        conflicts, negative_conflicts, unavailable = [], [], []
        singles = {'left': [], 'right': []}
        admitted_singles = {'left': [], 'right': []}
        negative_indices, errors = [], []
        for row in rows:
            i = row['frameIndex']
            label = labels[i]
            assert row['kind'] == 'pose-frame'
            errors.append(abs(row['fileMs'] - case['displayPtsMs'][i]))
            status[row['status']] += 1
            g = geometry(row, case['decodedDimensions'])
            scores = [row[p + 'Score'] for p in POINTS.values()]
            assert abs(row['confidence'] - min(scores)) < 1e-9
            # Native classifier validity: all finite coordinates, finite scores >= .65,
            # and non-degenerate shoulder span. Adapter already rejects bad mappings.
            admitted = (g is not None and math.isfinite(row['confidence'])
                        and .65 <= row['confidence'] <= 1
                        and all(math.isfinite(s) and .65 <= s <= 1 for s in scores))
            assert admitted == (row['status'] != 'low-confidence')
            for name, p in POINTS.items():
                weak_joints[name] += not (math.isfinite(row[p + 'Score']) and .65 <= row[p + 'Score'] <= 1)
            counts['admittedFrames'] += admitted
            counts['abstainedFrames'] += not admitted
            counts['validGeometryFrames'] += g is not None
            negative = label['poseDefinitelyNegativeBothCoordinateSpaces']
            counts['coveredNegativeSamples'] += negative
            if negative:
                negative_indices.append(i)
                counts['admittedNegativeSamples'] += admitted
            allowed = label['allowedGatesSource']
            singleton = all(len(allowed[s]) == 1 for s in ('left', 'right'))
            singleton_pairs['physicalFramesCovered'] += singleton
            if g is None:
                unavailable.append(i)
                continue
            pairs[g['left'] + '/' + g['right']] += 1
            if singleton:
                singleton_pairs['validPredictionFrames'] += 1
                singleton_pairs['matchingFrames'] += all(g[s] == allowed[s][0] for s in ('left', 'right'))
                singleton_pairs['admittedFrames'] += admitted
            bad = [s for s in ('left', 'right') if g[s] not in allowed[s]]
            if bad:
                conflicts.append({'frame': i, 'sourceFrame': label['sourceFrame'], 'sides': bad,
                                  'predicted': g, 'allowed': allowed, 'admitted': admitted})
            raised = ('left' if g == {'left': 'up', 'right': 'down'} else
                      'right' if g == {'left': 'down', 'right': 'up'} else None)
            if raised:
                singles[raised].append(i)
                if admitted:
                    admitted_singles[raised].append(i)
                if negative:
                    negative_conflicts.append({'frame': i, 'sourceFrame': label['sourceFrame'],
                                               'side': raised, 'admitted': admitted})
        assert max(errors, default=0) <= case['streamTickMs']
        assert result['nativePoseFrameCoverage']['loggedFrames'] == len(rows)
        assert result['nativePoseFrameCoverage']['missingIndices'] == missing
        complete = (not missing and result['completeFileVerified']
                    and result['nativePoseFrameCoverage']['complete'])
        perf = result.get('nativePerformanceSummary')
        neg_runs = groups(negative_indices, case['displayPtsMs'])
        cases.append({'caseId': case['caseId'], 'expectedFrames': case['frames'], 'coveredFrames': len(rows),
                      'completeFileEvidence': complete, 'missingIndices': missing,
                      'executionAcceptance': result['executionAcceptance'],
                      'recognitionAcceptance': result['recognitionAcceptance'],
                      'terminationReason': result['terminationReason'],
                      'expectationKnown': case['expectationKnown'], 'expectedGestures': case['expectedGestures'],
                      'classifierStatuses': dict(status), 'counts': dict(counts), 'weakJointFrameCounts': dict(weak_joints),
                      'maximumPtsErrorMs': max(errors, default=None), 'allowedStreamTickMs': case['streamTickMs'],
                      'geometry': {'sourcePixelGatePairs': dict(pairs), 'singletonGatePairs': dict(singleton_pairs),
                                   'incompatibilitiesWithAllowedSets': conflicts, 'unavailableGeometryFrames': unavailable,
                                   'singleArmRunsIgnoringConfidence': {s: groups(v, case['displayPtsMs']) for s, v in singles.items()},
                                   'admittedSingleArmRuns': {s: groups(v, case['displayPtsMs']) for s, v in admitted_singles.items()},
                                   'negativeFrameSingleArmConflicts': negative_conflicts},
                      'negativeExposure': {'coveredSampleBins': len(negative_indices),
                                           'coveredSampleBinSeconds': len(negative_indices) / case['fps'],
                                           'closedFirstToLastSeconds': sum(r['closedFirstToLastMs'] for r in neg_runs) / 1000},
                      'nativeFileEvents': result['nativeFileEvents'], 'observedGestures': result['observedGestures'],
                      'lastPacket': result['lastPacket'], 'ui': result['ui'],
                      'uiScoringEvidenceVerified': result['uiScoringEvidenceVerified'],
                      'nativeScoringMatches': result['nativeScoringMatches'],
                      'progressUnchanged': result['progressUnchanged'], 'performanceSummary': perf,
                      'lastSummaryResourcesClosed': perf.get('resourcesClosed') if perf else None,
                      'performanceScope': result['nativePerformanceScope'],
                      'wallMs': result['wallMs'], 'caseWallMs': result['caseWallMs']})
    report = {'schemaVersion': 1, 'scope': 'Saved first native attempt: covered frames only; no inference or protected edits',
              'planSha256': PLAN_SHA, 'inputBindings': bindings,
              'frozenFilesReverified': len(plan['frozenFiles']), 'sourcePinsReverified': len(plan['sourcePins']),
              'annotationAuthorType': 'AI', 'humanConfirmed': False, 'preliminaryDiagnosticOnly': True,
              'definitePositiveOpportunities': 0, 'eventRecall': None,
              'eventRecallReason': 'Unestimable: zero definite physical positives; cohort also incomplete',
              'confidenceMeaning': 'MoveNet required-keypoint model scores; global minimum of four scores; not visibility/presence or calibrated correctness probability',
              'geometryMethod': 'Strict .30/.20 gates in source pixels; compare with frozen source-coordinate allowed sets, confidence ignored and admission reported separately',
              'cases': cases,
              'totals': {'plannedFrames': sum(c['frames'] for c in plan['cases']),
                         'coveredFrames': sum(c['coveredFrames'] for c in cases),
                         'missingFrames': sum(len(c['missingIndices']) for c in cases),
                         'admittedFrames': sum(c['counts']['admittedFrames'] for c in cases),
                         'abstainedFrames': sum(c['counts']['abstainedFrames'] for c in cases),
                         'validGeometryFrames': sum(c['counts']['validGeometryFrames'] for c in cases),
                         'coveredNegativeSamples': sum(c['counts']['coveredNegativeSamples'] for c in cases),
                         'admittedNegativeSamples': sum(c['counts']['admittedNegativeSamples'] for c in cases),
                         'gateIncompatibilities': sum(len(c['geometry']['incompatibilitiesWithAllowedSets']) for c in cases),
                         'admittedGateIncompatibilities': sum(sum(v['admitted'] for v in c['geometry']['incompatibilitiesWithAllowedSets']) for c in cases),
                         'negativeFrameSingleArmConflicts': sum(len(c['geometry']['negativeFrameSingleArmConflicts']) for c in cases),
                         'admittedNegativeFrameSingleArmConflicts': sum(sum(v['admitted'] for v in c['geometry']['negativeFrameSingleArmConflicts']) for c in cases)},
              'limitations': ['Two clips terminated before full-file completion; missing rows are not negative outcomes or abstentions.',
                              'Partial clips have no verified end-of-clip UI score; no whole-cohort zero-score claim.',
                              'Source gate compatibility with broad AI uncertainty bounds is not point accuracy.',
                              'No definite physical positives: no recall, timing-acceptance or candidate-benefit claim.',
                              'API34 ARM64 Android emulator measurements are not Fire TV/ARMv7, real camera or sustained hardware evidence.',
                              'Saved lifecycle summaries do not yet confirm final resource closure; root owns final cleanup.']}
    # Fail rather than publish a mixed read if a controller replaced any input.
    for pin in bindings:
        assert digest(pin['path']) == pin['sha256'], 'Result changed during analysis: ' + pin['path']
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256']
    out = Path(__file__).parent / 'native-initial-analysis.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['totals']))


if __name__ == '__main__':
    main()
