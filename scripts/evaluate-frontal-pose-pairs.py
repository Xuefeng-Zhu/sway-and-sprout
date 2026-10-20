#!/usr/bin/env python3
"""Evaluate frozen public PNG pose pairs. Never opens camera or socket.

The image comparison is one pass per public still. The ordered classifier replay
runs new model inference on every repeated PNG at authored timestamps.
The parent separately tests the encoded held-pose video decoder/scorer.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import socket
import struct
import sys
from unittest import mock

sys.dont_write_bytecode = True

JOINTS = ('leftShoulder', 'rightShoulder', 'leftWrist', 'rightWrist')
ATTRS = ('left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist')
SWAPPED = dict(zip(JOINTS, ('rightShoulder', 'leftShoulder', 'rightWrist', 'leftWrist')))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def adapt_manual(manual, path, digest):
    if manual.get('annotationRevision') != 2 or manual.get('modelInferenceUsed') is not False:
        raise ValueError('Final pre-inference v2 manual artifact required')
    ids = {'public-frontal-candidate-frame035.png':'R', 'chosen-neutral-source-frame225.png':'N',
           'frontal-left-reflected-frame035.png':'L', 'frontal-neutral-reflected-frame225.png':'NM'}
    if len(manual['poses']) != 4 or {p['file'] for p in manual['poses']} != set(ids):
        raise ValueError('Only the four explicitly frozen source35/source225 images accepted')
    poses = []
    for item in manual['poses']:
        poses.append(dict(id=ids[item['file']],path=item['file'],sha256=item['sha256'],
                          width=manual['size'][0],height=manual['size'][1],expected=item['expectedGeometry'],
                          points={name:dict(x=[p['boxXYXY'][0],p['boxXYXY'][2]],y=[p['boxXYXY'][1],p['boxXYXY'][3]]) for name,p in item['annotations'].items()},
                          manual=item))
    return dict(schemaVersion=1,frozenAtUtc=manual['frozenAtUtc'],manualAnnotation=dict(path=str(path),sha256=digest),
                poses=poses,mirrorPairs=[dict(original='R',mirror='L'),dict(original='N',mirror='NM')],
                sequence=dict(fps=10,prefix=[dict(pose='N',frames=20)],
                    repeat=[dict(pose='L',frames=10),dict(pose='N',frames=12),dict(pose='R',frames=10),dict(pose='N',frames=12)],cycles=3))


def validate_recorded(item, geometry):
    manual = item.get('manual')
    if manual is None:
        return
    points, recorded = manual['annotations'],manual['geometry']
    def same(a,b):
        if isinstance(a,list):
            return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
        return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
    width=math.dist(points['leftShoulder']['center'],points['rightShoulder']['center'])
    if not same(width,recorded['shoulderWidthPx']) or not same(geometry['shoulderWidthBounds'],recorded['shoulderWidthConservativeBounds']):
        raise ValueError('Recorded shoulder geometry mismatch')
    for side in ('left','right'):
        s,w=points[side+'Shoulder'],points[side+'Wrist']
        dy=s['center'][1]-w['center'][1]
        for point in (s,w):
            x,y=point['center'];x0,y0,x1,y1=point['boxXYXY']
            if not x0<=x<=x1 or not y0<=y<=y1:
                raise ValueError('Manual center not in plausibility box')
        if not (same(dy,recorded[side]['verticalOffsetPx']) and same(dy/width,recorded[side]['normalizedOffset']) and
                same([s['boxXYXY'][1]-w['boxXYXY'][3],s['boxXYXY'][3]-w['boxXYXY'][1]],recorded[side]['verticalOffsetConservativeBounds']) and
                same(geometry['gates'][side]['qBounds'],recorded[side]['normalizedConservativeBounds'])):
            raise ValueError('Recorded manual q geometry mismatch')


def validate_manual_reflection(a,b,width):
    for name in JOINTS:
        pa,pb=a['manual']['annotations'][name],b['manual']['annotations'][SWAPPED[name]]
        x0,y0,x1,y1=pa['boxXYXY']
        if pb['center']!=[width-1-pa['center'][0],pa['center'][1]] or pb['boxXYXY']!=[width-1-x1,y0,width-1-x0,y1]:
            raise ValueError('Manual anatomical reflection mismatch')
    return dict(exactCenterAndBoxReflection=True,anatomicalSidesSwapped=True)


def resolve_file(base, item):
    path = Path(item['path']).expanduser()
    path = (base / path).resolve() if not path.is_absolute() else path.resolve()
    data = path.read_bytes()
    if sha(data) != item['sha256']:
        raise ValueError(f"Frozen input hash mismatch: {path}")
    return path, data


def xy_bounds(point):
    def interval(value):
        if isinstance(value, (int, float)):
            value = [value, value]
        if (not isinstance(value, list) or len(value) != 2 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in value) or
                value[0] > value[1]):
            raise ValueError('Annotation needs finite ordered x/y bounds or exact points')
        return value
    return dict(x=interval(point['x']), y=interval(point['y']))


def annotation_geometry(points, width, height, config):
    if points is None:
        return {'status': 'not-provided', 'note': 'No numeric manual joint bounds supplied; no bounds invented.'}
    if set(points) != set(JOINTS):
        raise ValueError('Manual bounds must contain exactly four named shoulder/wrist joints')
    boxes = {name: xy_bounds(points[name]) for name in JOINTS}
    for box in boxes.values():
        if not (0 <= box['x'][0] <= box['x'][1] < width and
                0 <= box['y'][0] <= box['y'][1] < height):
            raise ValueError('Manual joint bounds exceed the frozen PNG dimensions')
    ls, rs = boxes['leftShoulder'], boxes['rightShoulder']
    def axis_separation(a, b):
        return max(0, a[0] - b[1], b[0] - a[1])
    width_min = math.hypot(axis_separation(ls['x'], rs['x']), axis_separation(ls['y'], rs['y']))
    width_max = math.hypot(max(abs(a-b) for a in ls['x'] for b in rs['x']),
                           max(abs(a-b) for a in ls['y'] for b in rs['y']))
    if width_min <= .00001:
        raise ValueError('Manual shoulder boxes do not establish a nondegenerate shoulder-width bound')
    result = {}
    for side in ('left', 'right'):
        shoulder, wrist = boxes[side + 'Shoulder'], boxes[side + 'Wrist']
        numerator = [shoulder['y'][0] - wrist['y'][1], shoulder['y'][1] - wrist['y'][0]]
        values = [value / divisor for value in numerator for divisor in (width_min, width_max)]
        low, high = min(values), max(values)
        gate = ('up' if low > config.raise_margin else
                'down' if high < -config.neutral_margin else
                'transition' if low >= -config.neutral_margin and high <= config.raise_margin else 'ambiguous')
        result[side] = dict(qBounds=[low, high], robustGate=gate)
    return dict(status='validated', shoulderWidthBounds=[width_min, width_max], gates=result)


def measurement(observation, config, gates):
    if observation is None:
        return dict(points=None, q=None, gate=gates(None, config), confidenceEligible=False)
    points = {name: dict(x=getattr(observation, attr).x, y=getattr(observation, attr).y,
                         confidence=getattr(observation, attr).confidence)
              for name, attr in zip(JOINTS, ATTRS)}
    ls, rs = observation.left_shoulder, observation.right_shoulder
    width = math.hypot(ls.x - rs.x, ls.y - rs.y)
    q = None if width <= .00001 else {
        side: (getattr(observation, side + '_shoulder').y - getattr(observation, side + '_wrist').y) / width
        for side in ('left', 'right')}
    phase = gates(observation, config)
    confidences=[observation.confidence]+[point['confidence'] for point in points.values()]
    return dict(points=points, q=q, shoulderWidth=width,
                observationConfidence=observation.confidence, gate=phase,
                minimumConfidence=min(confidences),
                confidenceEligible=all(math.isfinite(v) and config.min_confidence<=v<=1 for v in confidences))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True, help='Freeze manifest before inference')
    parser.add_argument('--project', type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    raw = manifest_path.read_bytes()
    if sha(raw) != args.manifest_sha256:
        raise ValueError('Manifest differs from the explicitly frozen SHA256')
    manifest = json.loads(raw)
    original_manual = manifest if 'annotationRevision' in manifest else None
    if original_manual is not None:
        manifest=adapt_manual(original_manual,manifest_path,sha(raw))
    if manifest.get('schemaVersion') != 1 or not manifest.get('frozenAtUtc'):
        raise ValueError('A frozen schemaVersion1 annotation index is required')
    manual_path, manual_data = resolve_file(manifest_path.parent, manifest['manualAnnotation'])
    sys.path.insert(0, str(args.project.resolve() / 'sidecar'))
    from motion import Config, GestureMachine
    config = Config()
    inputs = {}
    for item in manifest['poses']:
        path, data = resolve_file(manifest_path.parent, item)
        if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
            raise ValueError('Only frozen PNG pose inputs are accepted')
        width, height = struct.unpack('>II', data[16:24])
        if [width, height] != [item['width'], item['height']]:
            raise ValueError('Frozen PNG dimensions differ from annotation index')
        expected = item['expected']
        if set(expected) != {'left', 'right'} or any(v not in ('up','down','transition') for v in expected.values()):
            raise ValueError('Each pose needs frozen anatomical left/right expected gates')
        geometry = annotation_geometry(item.get('points'), width, height, config)
        validate_recorded(item,geometry)
        if geometry['status'] == 'validated':
            for side in ('left', 'right'):
                if geometry['gates'][side]['robustGate'] != expected[side]:
                    raise ValueError('Declared gate is not established by the frozen numeric bounds')
        inputs[item['id']] = dict(path=path, item=item, dimensions=[width,height], annotationGeometry=geometry)
    sequence = manifest['sequence']
    fps = sequence['fps']
    if fps != 10:
        raise ValueError('This bounded fixture uses a frozen10fps time base')
    stages = list(sequence['prefix']) + list(sequence['repeat']) * sequence['cycles']
    if any(stage['pose'] not in inputs or type(stage['frames']) is not int or stage['frames'] <= 0 for stage in stages):
        raise ValueError('Invalid frozen stage sequence')
    if sum(stage['frames'] for stage in stages) != 152:
        raise ValueError('Frozen bounded sequence must total152frames')
    report = dict(evidenceType='public-PNG pose inference plus repeated-observation classifier simulation',
                  manifestSha256=sha(raw), manualAnnotation=dict(path=str(manual_path),sha256=sha(manual_data)),
                  config=asdict(config), physicalCameraUsed=False, socketsOpened=False,
                  thresholdsRetuned=False, validationOnly=args.validate_only,
                  inputs={name:dict(path=str(value['path']),sha256=value['item']['sha256'],
                                   dimensions=value['dimensions'],expected=value['item']['expected'],
                                   annotationGeometry=value['annotationGeometry']) for name,value in inputs.items()})
    if original_manual is not None:
        report.update(source=original_manual['source'],scope=original_manual['scope'],uncertainty=original_manual['uncertainty'],
                      naturalContinuousSequenceCertified=original_manual['naturalContinuousSequenceCertified'],
                      genuineFilmedLeftRaiseSelected=original_manual['genuineFilmedLeftRaiseSelected'],
                      manualMirrorComparisons=[dict(original=p['original'],mirror=p['mirror'],**validate_manual_reflection(inputs[p['original']]['item'],inputs[p['mirror']]['item'],inputs[p['original']]['dimensions'][0])) for p in manifest['mirrorPairs']])
    report['implementationSha256']={name:sha((args.project.resolve()/'sidecar'/name).read_bytes()) for name in ('inference.py','motion.py','video_input.py','models.lock.json')}
    if args.validate_only:
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        return 0
    # This line is reached only after manual/index/image hashes and annotation
    # dimensions/gates have been frozen and checked. No inference runs earlier.
    import cv2
    import numpy as np
    from inference import OpenCVPose
    from video_input import wrist_gates
    observations = {}
    blocked=Counter()
    def no_camera(*a,**kw):
        blocked['camera']+=1
        raise AssertionError('Physical camera prohibited')
    def no_socket(*a,**kw):
        blocked['socket']+=1
        raise AssertionError('Sockets prohibited')
    with mock.patch.object(cv2,'VideoCapture',side_effect=no_camera), \
            mock.patch.object(socket,'socket',side_effect=no_socket):
        pixels={name:cv2.imread(str(value['path']),cv2.IMREAD_COLOR) for name,value in inputs.items()}
        if any(image is None for image in pixels.values()):
            raise ValueError('Frozen PNG decode failed')
        report['exactPixelReflectionChecks']=[dict(original=p['original'],mirror=p['mirror'],matched=bool(np.array_equal(pixels[p['original']][:,::-1],pixels[p['mirror']]))) for p in manifest['mirrorPairs']]
        if not all(p['matched'] for p in report['exactPixelReflectionChecks']):
            raise ValueError('Frozen image pixels do not exactly reflect')
        pipeline = OpenCVPose()
        report['runtime'] = pipeline.runtime
        for name,value in inputs.items():
            image = pixels[name]
            if image is None:
                raise ValueError('Frozen PNG could not be decoded')
            image = pipeline._input_frame(image)
            observation,status,elapsed = pipeline.infer(image)
            observations[name] = observation
            measured = measurement(observation,config,wrist_gates)
            measured.update(inferenceStatus=status,inferenceMs=elapsed,
                            inferenceDimensions=[image.shape[1],image.shape[0]])
            measured['matchesFrozenGate'] = measured['gate'] == 'left-{left}/right-{right}'.format(**value['item']['expected'])
            report['inputs'][name]['measurement'] = measured
            del image
        mirror_results = []
        for pair in manifest['mirrorPairs']:
            original,mirrored = report['inputs'][pair['original']],report['inputs'][pair['mirror']]
            a,b = original['measurement'],mirrored['measurement']
            pair_result = dict(original=pair['original'],mirror=pair['mirror'],anatomicalSidesSwapped=True)
            if a['points'] and b['points']:
                width,height = a['inferenceDimensions']
                if b['inferenceDimensions'] != [width,height]:
                    raise ValueError('Mirror pairs need equal inference dimensions')
                differences = {}
                for name in JOINTS:
                    reflected = dict(x=width-1-a['points'][name]['x'],y=a['points'][name]['y'])
                    actual = b['points'][SWAPPED[name]]
                    differences[name+'To'+SWAPPED[name][0].upper()+SWAPPED[name][1:]] = dict(
                        xDelta=actual['x']-reflected['x'],yDelta=actual['y']-reflected['y'],
                        distancePixels=math.hypot(actual['x']-reflected['x'],actual['y']-reflected['y']))
                pair_result['pointDiscrepancies'] = differences
                if a['q'] and b['q']:
                    pair_result['qDiscrepancies'] = dict(leftToRight=b['q']['right']-a['q']['left'],
                                                       rightToLeft=b['q']['left']-a['q']['right'])
            mirror_results.append(pair_result)
        report['mirrorComparisons'] = mirror_results
        machine,now,events,statuses,armed_transitions = GestureMachine(),0,[],Counter(),0
        trace=[]
        for stage in stages:
            for _ in range(stage['frames']):
                observation,inference_status,elapsed=pipeline.infer(pixels[stage['pose']])
                measured=measurement(observation,config,wrist_gates)
                was_armed = machine.armed
                event = machine.update(observation,now)
                statuses[machine.status] += 1
                armed_transitions += int(machine.armed and not was_armed)
                if event:
                    events.append(dict(atMs=now,pose=stage['pose'],**event))
                trace.append(dict(frame=len(trace),atMs=now,pose=stage['pose'],inferenceStatus=inference_status,inferenceMs=elapsed,
                                  q=measured['q'],minimumConfidence=measured.get('minimumConfidence'),gate=measured['gate'],
                                  classifierStatus=machine.status,armed=machine.armed,expectedSide=machine.expected,heldMs=machine.held_ms))
                now += 1000/fps
        expected_gestures = ['left-raise','right-raise']*3
        report['evidenceType']='public-PNG inference plus actual repeated-pixel inference and classifier sequence'
        report['classifierSimulation'] = dict(method='Actual OpenCVPose.infer for every repeated frozen PNG, actual GestureMachine.update at authored10fps; no naturally filmed motion claim',
            frames=sum(stage['frames'] for stage in stages),durationMs=now,statuses=dict(statuses),
            armedTransitions=armed_transitions,expectedGestures=expected_gestures,
            observedGestures=[event['gesture'] for event in events],events=events,
            matched=[event['gesture'] for event in events]==expected_gestures,trace=trace)
        del pixels
    report['blockedApiAttempts'] = dict(camera=blocked['camera'],socket=blocked['socket'])
    report['allFrozenPoseGatesMatched'] = all(value['measurement']['matchesFrozenGate'] for value in report['inputs'].values())
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(args.output),'allFrozenPoseGatesMatched':report['allFrozenPoseGatesMatched'],
                      'classifierSimulation':{k:v for k,v in report['classifierSimulation'].items() if k!='trace'}},allow_nan=False))
    return 0 if report['allFrozenPoseGatesMatched'] and report['classifierSimulation']['matched'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
