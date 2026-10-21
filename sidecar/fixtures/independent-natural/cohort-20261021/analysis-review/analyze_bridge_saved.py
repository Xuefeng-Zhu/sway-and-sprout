"""Read saved bridge-only native evidence; no SDK, media or network imports."""
from collections import Counter
import json
import math
from pathlib import Path

from analyze_full import E, R, PLAN_SHA, digest, groups, read, geometry as full_geometry
from analyze_native_saved import POINTS, geometry


def analyze():
    pp = E / 'execution-plan.freeze.json'
    assert digest(pp) == PLAN_SHA
    plan = read(pp)
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256'], pin['path']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256'], pin['path']
    result_path = E / 'movenet-bridge-results' / 'result.json'
    cohort = read(result_path)
    assert cohort['cohortSha256'] == PLAN_SHA
    assert cohort['status'] in ('bridge-comparison-completed', 'bridge-comparison-incomplete')
    assert cohort['uiAcceptance'] == cohort['jsReducerScoring'] == 'not-exercised'
    bindings = [{'path': str(result_path), 'sha256': digest(result_path)}]
    cases = []
    for case in plan['cases']:
        path = result_path.parent / (case['caseId'] + '.json')
        result = read(path)
        assert result['name'] == case['caseId']
        assert result['expectationKnown'] == case['expectationKnown']
        assert result['expectedGestures'] == case['expectedGestures']
        assert result['uiAcceptance'] == result['jsReducerScoring'] == 'not-exercised'
        log = Path(result['native-scalar']['path'])
        summary = Path(result['native-summary']['path'])
        full_path = E / 'full-results' / (case['caseId'] + '.json')
        for p in (path, log, summary, full_path):
            bindings.append({'path': str(p), 'sha256': digest(p)})
        assert digest(log) == result['native-scalar']['sha256']
        assert digest(summary) == result['native-summary']['sha256']
        raw = [json.loads(line) for line in log.read_text().splitlines() if line]
        rows = [row for row in raw if row['kind'] == 'pose-frame']
        labels = read(case['normalizedLabelsPath'])['perFrame']
        full_rows = read(full_path)['rows']
        assert len(full_rows) == len(labels) == case['frames']
        indices = [row['frameIndex'] for row in rows]
        assert len(indices) == len(set(indices)) and indices == sorted(indices)
        assert all(0 <= i < case['frames'] for i in indices)
        missing = sorted(set(range(case['frames'])) - set(indices))
        counts, status, weak = Counter(), Counter(), Counter()
        pairs, singleton = Counter(), Counter()
        conflicts, neg_conflicts, unavailable = [], [], []
        negative_indices, errors = [], []
        singles = {'left': [], 'right': []}
        admitted_singles = {'left': [], 'right': []}
        paired = Counter()
        for row in rows:
            i = row['frameIndex']
            label, full = labels[i], full_rows[i]
            errors.append(abs(row['fileMs'] - case['displayPtsMs'][i]))
            status[row['status']] += 1
            scores = [row[p + 'Score'] for p in POINTS.values()]
            assert abs(row['confidence'] - min(scores)) < 1e-9
            g = geometry(row, case['decodedDimensions'])
            admitted = (g is not None and math.isfinite(row['confidence']) and .65 <= row['confidence'] <= 1
                        and all(math.isfinite(s) and .65 <= s <= 1 for s in scores))
            assert admitted == (row['status'] != 'low-confidence')
            counts['admittedFrames'] += admitted
            counts['abstainedFrames'] += not admitted
            counts['validGeometryFrames'] += g is not None
            for name, p in POINTS.items():
                weak[name] += not (math.isfinite(row[p + 'Score']) and .65 <= row[p + 'Score'] <= 1)
            obs = full['derivedObservationSourcePixels']
            fg = full_geometry(obs, full['sourceImageWidth'], full['sourceImageHeight'])
            fa = (fg is not None and .65 <= obs['confidence'] <= 1
                  and all(.65 <= obs[n]['confidence'] <= 1 for n in POINTS))
            paired['coveredFrames'] += 1
            paired['fullAdmittedFrames'] += fa
            paired['nativeAdmittedFrames'] += admitted
            paired['bothAdmittedFrames'] += fa and admitted
            paired['fullOnlyAdmittedFrames'] += fa and not admitted
            paired['nativeOnlyAdmittedFrames'] += admitted and not fa
            paired['bothAbstainedFrames'] += not admitted and not fa
            paired['bothValidGeometries'] += fg is not None and g is not None
            paired['differentPredictedGatePairs'] += fg is not None and g is not None and fg != g
            negative = label['poseDefinitelyNegativeBothCoordinateSpaces']
            counts['coveredNegativeSamples'] += negative
            if negative:
                negative_indices.append(i)
                counts['admittedNegativeSamples'] += admitted
            allowed = label['allowedGatesSource']
            one = all(len(allowed[s]) == 1 for s in ('left', 'right'))
            singleton['physicalFramesCovered'] += one
            if g is None:
                unavailable.append(i)
                continue
            pairs[g['left'] + '/' + g['right']] += 1
            if one:
                singleton['validPredictionFrames'] += 1
                singleton['matchingFrames'] += all(g[s] == allowed[s][0] for s in ('left', 'right'))
                singleton['admittedFrames'] += admitted
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
                    neg_conflicts.append({'frame': i, 'side': raised, 'admitted': admitted})
        assert max(errors, default=0) <= case['streamTickMs']
        assert result['nativePoseFrameCoverage']['loggedFrames'] == len(rows)
        assert result['nativePoseFrameCoverage']['missingIndices'] == missing
        runs = groups(negative_indices, case['displayPtsMs'])
        cases.append({'caseId': case['caseId'], 'expectedFrames': case['frames'], 'coveredFrames': len(rows),
                      'missingIndices': missing, 'completeFileVerified': result['completeFileVerified'],
                      'executionAcceptance': result['executionAcceptance'], 'terminationReason': result['terminationReason'],
                      'recognitionObservation': result['recognitionObservation'], 'expectationKnown': case['expectationKnown'],
                      'expectedGestures': case['expectedGestures'], 'counts': dict(counts), 'classifierStatuses': dict(status),
                      'weakJointFrameCounts': dict(weak), 'maximumPtsErrorMs': max(errors, default=None),
                      'geometry': {'sourcePixelGatePairs': dict(pairs), 'singletonGatePairs': dict(singleton),
                                   'incompatibilitiesWithAllowedSets': conflicts, 'unavailableGeometryFrames': unavailable,
                                   'negativeFrameSingleArmConflicts': neg_conflicts,
                                   'singleArmRunsIgnoringConfidence': {s: groups(v, case['displayPtsMs']) for s, v in singles.items()},
                                   'admittedSingleArmRuns': {s: groups(v, case['displayPtsMs']) for s, v in admitted_singles.items()}},
                      'negativeExposure': {'coveredSampleBins': len(negative_indices),
                                           'sampleBinSeconds': len(negative_indices) / case['fps'],
                                           'closedFirstToLastSeconds': sum(r['closedFirstToLastMs'] for r in runs) / 1000},
                      'pairedWithFullOnCoveredIndices': dict(paired),
                      'nativeFileEvents': result['nativeFileEvents'], 'deliveredEvents': result['deliveredEvents'],
                      'receiptProtocolACK': result['protocolAfter'], 'protocolACKMatches': result['protocolACKMatches'],
                      'uiScoring': 'not exercised; receipt ACK does not establish score/rays',
                      'resourcesClosed': result['resourcesClosed'], 'explicitlyDeactivated': result['explicitlyDeactivated'],
                      'cameraCalls': result['cameraCalls'], 'progressUnchanged': result['progressUnchanged'],
                      'performanceSummary': result['nativePerformanceSummary'],
                      'activeWallMs': result.get('activeWallMs'), 'caseWallMs': result['caseWallMs']})
    total_keys = ('admittedFrames', 'abstainedFrames', 'validGeometryFrames', 'coveredNegativeSamples', 'admittedNegativeSamples')
    totals = {key: sum(c['counts'][key] for c in cases) for key in total_keys}
    totals.update({'plannedFrames': sum(c['frames'] for c in plan['cases']),
                   'coveredFrames': sum(c['coveredFrames'] for c in cases),
                   'missingFrames': sum(len(c['missingIndices']) for c in cases),
                   'gateIncompatibilities': sum(len(c['geometry']['incompatibilitiesWithAllowedSets']) for c in cases),
                   'admittedGateIncompatibilities': sum(sum(x['admitted'] for x in c['geometry']['incompatibilitiesWithAllowedSets']) for c in cases),
                   'negativeFrameSingleArmConflicts': sum(len(c['geometry']['negativeFrameSingleArmConflicts']) for c in cases),
                   'events': sum(len(c['nativeFileEvents']) for c in cases)})
    report = {'schemaVersion': 1, 'scope': cohort['scope'], 'cohortStatus': cohort['status'],
              'planSha256': PLAN_SHA, 'annotationAuthorType': 'AI', 'humanConfirmed': False,
              'definitePositiveOpportunities': 0, 'eventRecall': None, 'eventRecallReason': 'zero definite physical positives',
              'frozenFilesReverified': len(plan['frozenFiles']), 'sourcePinsReverified': len(plan['sourcePins']),
              'inputBindings': bindings, 'uiAcceptance': 'not-exercised', 'jsReducerScoring': 'not-exercised',
              'confidenceSemantics': 'Native required-keypoint scores and Full min(visibility,presence) are separate model-specific signals, not calibrated correctness probabilities',
              'cases': cases, 'totals': totals,
              'limitations': ['Bridge-only diagnostic completion cannot repair first-attempt UI execution failures.',
                              'Zero definite positive opportunities: no event recall, accuracy-benefit or native-porting acceptance.',
                              'Broad AI uncertainty permits non-contradiction, not point accuracy.',
                              'Receipt ACK is not game reducer scoring; no UI rays, rendering or full-game claim.',
                              'Single API34 ARM64 emulator measurements are not real Fire TV/ARMv7/camera/sustained performance evidence.',
                              'Full Mac and native emulator timing scopes differ; no direct speed ranking.']}
    for pin in bindings:
        assert digest(pin['path']) == pin['sha256'], 'Input replaced during analysis: ' + pin['path']
    for pin in plan['frozenFiles']:
        assert digest(pin['path']) == pin['sha256']
    for pin in plan['sourcePins']:
        assert digest(R / pin['path']) == pin['sha256']
    out = Path(__file__).parent / 'native-bridge-analysis.json'
    out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(totals))


if __name__ == '__main__':
    analyze()
