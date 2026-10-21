#!/usr/bin/env python3
"""Derive conservative geometry from frozen AI boxes; no model imports/results."""
import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DT = 1001 / 30


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(indices):
    result = []
    for i in indices:
        if result and i == result[-1][-1] + 1:
            result[-1].append(i)
        else:
            result.append([i])
    return result


def region_geometry(joints):
    a, b = joints['LS']['box'], joints['RS']['box']
    lo = math.hypot(max(0, a[0] - b[2], b[0] - a[2]),
                    max(0, a[1] - b[3], b[1] - a[3]))
    hi = max(math.dist(u, v)
             for u in itertools.product((a[0], a[2]), (a[1], a[3]))
             for v in itertools.product((b[0], b[2]), (b[1], b[3])))
    if lo <= 0:
        return {'leftQBounds': None, 'rightQBounds': None,
                'leftAllowed': ['down', 'transition', 'up'],
                'rightAllowed': ['down', 'transition', 'up'], 'degenerateAllowed': True}
    result = {'shoulderSpanBoundsPx': [lo, hi], 'degenerateAllowed': False}
    for side, shoulder, wrist in [('left', 'LS', 'LW'), ('right', 'RS', 'RW')]:
        s, w = joints[shoulder]['box'], joints[wrist]['box']
        gap = (s[1] - w[3], s[3] - w[1])
        values = [g / width for g in gap for width in (lo, hi)]
        qlo, qhi = min(values), max(values)
        allowed = []
        if qlo < -.20:
            allowed.append('down')
        if qhi >= -.20 and qlo <= .30:
            allowed.append('transition')
        if qhi > .30:
            allowed.append('up')
        result[side + 'QBounds'] = [qlo, qhi]
        result[side + 'Allowed'] = allowed
    return result


def main():
    bounds_path = HERE / 'joint-regions.freeze.json'
    assert sha(bounds_path) == 'dc57331b073ee5ff23d172182edacd700f7c996e56d62d5b3e142d8e6f763bcf'
    bounds = json.loads(bounds_path.read_text())
    assert len(bounds['rows']) == 210
    rows = []
    for original in bounds['rows']:
        i = original['clipFrame']
        assert original['sourceFrame'] == i + 180
        g = region_geometry(original['jointRegions'])
        rows.append({**original, 'atClipMs': i * DT, 'atSourceMs': (i + 180) * DT,
                     **g, 'onePhysicalPerson': True,
                     'visibility': 'all four required projected joint regions visible',
                     'physicalLeftCorrectMayBeAllowed': 'up' in g['leftAllowed'] and 'down' in g['rightAllowed'],
                     'physicalRightCorrectMayBeAllowed': 'up' in g['rightAllowed'] and 'down' in g['leftAllowed'],
                     'definiteBothDown': g['leftAllowed'] == ['down'] and g['rightAllowed'] == ['down'],
                     'definiteBothUp': g['leftAllowed'] == ['up'] and g['rightAllowed'] == ['up']})
    possible = runs([r['clipFrame'] for r in rows if r['physicalLeftCorrectMayBeAllowed']])
    hold_candidates = []
    for run in possible:
        eligible = next((i for i in run if int(i * DT - run[0] * DT) >= 350), None)
        hold_candidates.append({'startClipFrame': run[0], 'endClipFrameInclusive': run[-1],
                                'sampleSpanMs': (run[-1] - run[0]) * DT,
                                'firstHoldEligibleClipFrameRelaxed': eligible})
    whole_zero_proven = not any(r['firstHoldEligibleClipFrameRelaxed'] is not None for r in hold_candidates)
    negatives = []
    for kind, flag in [('neutral', 'definiteBothDown'), ('both-up', 'definiteBothUp')]:
        for run in runs([r['clipFrame'] for r in rows if r[flag]]):
            if len(run) < 2:
                continue
            negatives.append({'kind': kind, 'startClipFrame': run[0],
                              'endClipFrameInclusive': run[-1],
                              'startSourceFrame': run[0] + 180, 'endSourceFrameInclusive': run[-1] + 180,
                              'startClipMs': run[0] * DT, 'endClipMs': run[-1] * DT,
                              'certifiedDurationMs': (run[-1] - run[0]) * DT,
                              'durationRule': 'closed first-to-last sample span; no extra tail-frame duration'})
    annotation = {
        'schemaVersion': 1, 'caseId': 'both-press', 'authorType': 'AI',
        'authorId': '/root/independent_video_sources', 'predictionBlind': True,
        'humanConfirmed': False, 'humanConfirmationStatus': 'not-human-confirmed',
        'labelProvenance': 'AI source-pixel visual review; not human-, user-supplied or user-approved labels',
        'contractSha256': bounds['contractSha256'], 'protocolSha256': bounds['protocolSha256'],
        'jointRegionFreezeSha256': sha(bounds_path), 'sourceSha256': bounds['sourceSha256'],
        'clipSha256': bounds['clipSha256'], 'coordinateSystem': bounds['coordinateSystem'],
        'sourceFrameInterval': [180, 390], 'frameCount': 210, 'fpsNumerator': 30000, 'fpsDenominator': 1001,
        'initialExpected': 'left', 'modelConfidenceUsedForLabels': False, 'modelInferenceRun': False,
        'method': 'Conservative interval arithmetic over independent rectangular joint bounds. Width/point extrema may not be jointly attainable; gate sets and hold candidates form a relaxed superset, not proof that every combination is physically possible. Indeterminacy is retained.',
        'preModelVisualReview': bounds['reviewComplete'],
        'sourceGroupId': 'AFN-Sasebo-Robert-Price-Kelly-Stratoti',
        'performerIndependenceClaim': False, 'opportunities': [], 'definitePositiveDenominator': 0,
        'expectedSequence': [] if whole_zero_proven else None,
        'wholeCaseZeroEventProvenByConservativeBound': whole_zero_proven,
        'wholeCaseSequenceStatus': 'definite zero under left-first rules' if whole_zero_proven else 'indeterminate: broad physical bounds permit a potentially long enough left gate; do not force zero',
        'possibleLeftGateRunsRelaxed': hold_candidates,
        'certifiedNegativeIntervals': negatives,
        'certifiedNegativeDurationMs': sum(r['certifiedDurationMs'] for r in negatives),
        'uncertainFrames': [r['clipFrame'] for r in rows if len(r['leftAllowed']) > 1 or len(r['rightAllowed']) > 1],
        'perFrame': rows,
        'limits': ['No definite natural positive opportunity, so recall is unestimable.',
                   'AI visual regions are broad and not human ground truth or calibrated confidence regions.',
                   'Original source has existing graphics; title overlay obscures legs, not the four required joints.',
                   'No model inference, annotation retuning, camera, upload or native/Fire TV claim.']}
    out = HERE / 'annotations.proposal.json'
    assert not out.exists(), 'Never overwrite an annotation proposal; version changes separately before prediction'
    out.write_text(json.dumps(annotation, indent=2) + '\n')
    print(json.dumps({k: annotation[k] for k in ['expectedSequence', 'wholeCaseSequenceStatus',
          'possibleLeftGateRunsRelaxed', 'certifiedNegativeIntervals', 'certifiedNegativeDurationMs']}))


if __name__ == '__main__':
    main()
