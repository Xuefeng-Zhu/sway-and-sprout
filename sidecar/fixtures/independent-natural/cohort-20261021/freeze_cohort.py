"""Normalize already-frozen AI records and bind clocks/profiles before prediction."""
from pathlib import Path
from fractions import Fraction
import datetime
import hashlib
import json
import subprocess

W = Path(__file__).resolve().parent
R = Path('/Users/frank/mygit/sway-and-sprout')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(base, value):
    p = Path(value)
    return p if p.is_absolute() else base / p


def main():
    assert not (W / 'execution-plan.freeze.json').exists()
    assert not (W / 'full-results').exists()
    protocol = read(W / 'PROTOCOL.freeze.json')
    cases = []
    frozen = set([W / 'PROTOCOL.freeze.json', W / 'EVALUATION-CONTRACT.freeze.md',
                  W / 'run_full_frozen.py', W / 'privacy-preflight.json',
                  W / 'freeze_cohort.py'])
    for folder in ('both-press', 'both-stretch', 'cross-stretch'):
        base = W / 'cases' / folder
        path = base / 'case.freeze.json'
        c = read(path)
        a = c['annotation']
        ap = resolve(base, a.get('path', a.get('file')))
        assert digest(ap) == a['sha256']
        annotation = read(ap)
        assert annotation['authorType'] == 'AI' and annotation['humanConfirmed'] is False
        assert annotation['predictionBlind'] is True
        assert c['contractSha256'] == digest(W / 'EVALUATION-CONTRACT.freeze.md')
        assert c['protocolSha256'] == digest(W / 'PROTOCOL.freeze.json')
        rows = annotation['perFrame']
        d = c['derivative']
        video = resolve(base, d.get('relativePath', d.get('path', d.get('file'))))
        assert digest(video) == d['sha256'] and video.stat().st_size == d['bytes']
        fps = Fraction(c['displayTime']['fpsNumerator'], c['displayTime']['fpsDenominator'])
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                          '-show_entries', 'stream=width,height,time_base,r_frame_rate,avg_frame_rate,start_pts,nb_frames:frame=pts,best_effort_timestamp',
                          '-show_frames', '-of', 'json', str(video)], text=True))
        stream = probe['streams'][0]
        tick = Fraction(stream['time_base'])
        pts_ticks = [f.get('pts', f['best_effort_timestamp']) for f in probe['frames']]
        assert len(pts_ticks) == len(rows) == int(stream['nb_frames'])
        assert pts_ticks[0] == 0 and Fraction(stream['avg_frame_rate']) == fps
        pts = [float(x * tick * 1000) for x in pts_ticks]
        assert all(abs(x - float(i * 1000 / fps)) <= float(tick * 1000) for i, x in enumerate(pts))
        assert all(b > a for a, b in zip(pts_ticks, pts_ticks[1:]))
        normalized = []
        for i, row in enumerate(rows):
            assert row.get('frame', row.get('clipFrame')) == i
            if folder == 'both-press':
                gates = {'left': row['leftAllowed'], 'right': row['rightAllowed']}
                working = gates
            elif folder == 'both-stretch':
                spaces = row['physicalGatesByCoordinateSpace']
                gates = {s: spaces['decoded'][s]['allowedGates'] for s in ('left', 'right')}
                working = {s: spaces['sidecarWorking'][s]['allowedGates'] for s in ('left', 'right')}
            else:
                gates = row['allowedGates']; working = gates
            may_raise = lambda g: (('up' in g['left'] and 'down' in g['right']) or
                                   ('up' in g['right'] and 'down' in g['left']))
            normalized.append({'frame': i, 'sourceFrame': row['sourceFrame'], 'atVideoMs': pts[i],
                               'allowedGatesSource': gates, 'allowedGatesFullWorking': working,
                               'poseDefinitelyNegativeBothCoordinateSpaces': not may_raise(gates) and not may_raise(working)})
        normalized_path = base / 'root-normalized-physical-labels.freeze.json'
        normalized_path.write_text(json.dumps({'schemaVersion': 1, 'authorType': 'AI', 'humanConfirmed': False,
                                   'annotationPath': str(ap), 'annotationSha256': digest(ap),
                                   'derivation': 'Lossless field normalization only; no new region/label/model-derived edits',
                                   'perFrame': normalized}, indent=2) + '\n')
        pts_path = base / 'execution-pts.freeze.json'
        pts_path.write_text(json.dumps(probe, indent=2) + '\n')
        known = c.get('expectedSequence') is not None
        if folder == 'both-press':
            proof = read(base / 'derived-zero-proof.json')
            assert c['expectedSequence'] == []
            # Independently checked universal zero is bound by the case record.
            assert c.get('derivedEventReference')
            assert proof
        source = c['source']
        source_path = (W / 'discovery-source-b/dvids768147-original.mp4' if folder == 'both-press'
                       else W / ('discovery/pexels-7628775/source.mp4' if folder == 'both-stretch'
                                 else 'discovery/pexels-8401267/source.mp4'))
        assert digest(source_path) == source['sha256']
        item = {'caseId': 'independent-' + folder, 'annotationCaseId': c['caseId'],
                'sourceGroupId': c['sourceGroupId'], 'caseRecordPath': str(path), 'caseRecordSha256': digest(path),
                'video': str(video), 'sha256': d['sha256'], 'bytes': d['bytes'], 'frames': len(rows),
                'fps': float(fps), 'fpsNumerator': fps.numerator, 'fpsDenominator': fps.denominator,
                'displayPtsMs': pts, 'streamTickMs': float(tick * 1000),
                'decodedDimensions': [stream['width'], stream['height']],
                'sourceStartFrame': d.get('sourceStartFrame', d.get('sourceStartFrameInclusive')),
                'sourceEndFrameExclusive': d['sourceEndFrameExclusive'],
                'annotationPath': str(ap), 'annotationSha256': digest(ap),
                'normalizedLabelsPath': str(normalized_path), 'normalizedLabelsSha256': digest(normalized_path),
                'expectationKnown': known, 'expectedGestures': c['expectedSequence'] if known else None,
                'definitePositiveOpportunities': 0, 'preliminaryDiagnosticOnly': True,
                'poseNegativeSamples': sum(x['poseDefinitelyNegativeBothCoordinateSpaces'] for x in normalized)}
        cases.append(item)
        frozen.update(p for p in base.rglob('*') if p.is_file() and p.suffix in ('.json', '.py', '.md'))
        frozen.update([video, source_path])
    lock = read(R / 'android/native-video-assets.lock.json')
    (W / 'native-lock-before-append.freeze.json').write_text(json.dumps(lock, indent=2) + '\n')
    frozen.add(W / 'native-lock-before-append.freeze.json')
    for artifact in lock['artifacts']:
        p = R / artifact['target']
        assert p.stat().st_size == artifact['bytes'] and digest(p) == artifact['sha256']
        frozen.add(p)
    full_lock = R / 'sidecar/mediapipe-full.lock.json'
    full = read(full_lock); model = R / 'sidecar' / full['model']['path']
    assert digest(model) == full['model']['sha256']; frozen.update([full_lock, model])
    for binding in protocol['sourcePins']:
        assert digest(R / binding['path']) == binding['sha256']
    plan = {'schemaVersion': 1, 'status': 'FROZEN_BEFORE_FIRST_MODEL_INFERENCE',
            'frozenAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'startingProtocolCommit': '0092f88', 'annotationAuthorType': 'AI', 'humanConfirmed': False,
            'userSuppliedOrApprovedLabels': False, 'preliminaryDiagnosticOnly': True,
            'humanValidationRequiredBeforeAcceptance': True, 'cases': cases,
            'definitePositiveOpportunities': 0, 'eventRecallStatus': 'unestimable-zero-positive-denominator',
            'sourceGroupCount': 3, 'personIdentityIndependenceClaim': False,
            'fullProfile': {'runningMode': 'IMAGE', 'numPoses': 2, 'delegate': 'CPU', 'admissionThreshold': .65},
            'fullRuntimePins': full,
            'moveNetProfile': {'platform': 'Android emulator', 'runtime': 'LiteRT1.4.2',
                               'model': 'Lightning FP16v4', 'refinement': 'image-three-pass',
                               'threads': 2, 'delegate': 'CPU', 'admissionThreshold': .65,
                               'macCpuComparisonClaim': False, 'fireTvDeviceClaim': False},
            'analysisPolicy': {'negativeExposure': 'Instantaneously pose-negative sample bins: count/fps, excluding unknowns; also report closed first-to-last spans separately. Not a subframe continuous-motion claim or general FPR estimate.',
                               'wholeCaseZeroProof': 'Only both-press has independently proved zero under all allowed state paths; other cases remain unknown.',
                               'unresolvedEvents': 'Any event not excluded by all allowed physical/state interpretations remains unresolved; never relabel as success.',
                               'recall': 'No definite physical positive opportunities; do not manufacture recall/precision or model-benefit claim.',
                               'timing': 'Preserve actual unrounded file-time events and uncertain onset intervals; no tuning or new delay budget.'},
            'sourcePins': protocol['sourcePins'],
            'frozenFiles': [{'path': str(p), 'sha256': digest(p)} for p in sorted(frozen)]}
    (W / 'execution-plan.freeze.json').write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps({'planSha256': digest(W / 'execution-plan.freeze.json'),
                      'cases': [{'case': c['caseId'], 'frames': c['frames'], 'expectationKnown': c['expectationKnown'],
                                 'poseNegativeSamples': c['poseNegativeSamples']} for c in cases],
                      'totalFrames': sum(c['frames'] for c in cases), 'frozenFiles': len(frozen)}))


if __name__ == '__main__':
    main()
