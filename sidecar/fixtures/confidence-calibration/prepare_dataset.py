#!/usr/bin/env python3
"""Human-label-only COCO selection. Does not load any model or predictions."""
import argparse
import collections
import datetime
import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / 'source' / 'person_keypoints_val2017.json'
SOURCE_SHA256 = '788e2dae83c86bd547be7fab269d6399df5671063d29a61360cdb2cc370d2b14'
JOINT_INDEX = {'left_shoulder': 5, 'right_shoulder': 6, 'left_wrist': 9, 'right_wrist': 10}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def write_once(path, obj):
    payload = canonical_bytes(obj)
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f'Refusing to overwrite frozen file {path}')
    else:
        path.write_bytes(payload)
    return sha256(payload)


def select(policy):
    source_raw = SOURCE.read_bytes()
    assert sha256(source_raw) == SOURCE_SHA256
    data = json.loads(source_raw)
    grouped = collections.defaultdict(list)
    for annotation in data['annotations']:
        grouped[annotation['image_id']].append(annotation)
    eligible = collections.defaultdict(list)
    counts = collections.Counter()
    for image in sorted(data['images'], key=lambda i: i['id']):
        if image['license'] not in policy['allowedLicenseIds']:
            continue
        counts['allowed_license'] += 1
        annotations = grouped[image['id']]
        if len(annotations) != 1:
            continue
        counts['exactly_one_person_annotation_including_unlabeled_and_crowd'] += 1
        annotation = annotations[0]
        if annotation.get('iscrowd', 0) or annotation['num_keypoints'] < policy['minimumAnnotatedKeypoints']:
            continue
        counts['noncrowd_and_enough_keypoints'] += 1
        kp = annotation['keypoints']
        if any(kp[3*j+2] < 1 for j in JOINT_INDEX.values()):
            continue
        counts['all_four_target_joints_have_human_coordinates'] += 1
        bbox = annotation['bbox']
        bbox_fraction = bbox[2] * bbox[3] / (image['width'] * image['height'])
        if bbox_fraction < policy['minimumBBoxImageAreaFraction']:
            continue
        counts['prominent_bbox'] += 1
        shoulder_span = math.hypot(kp[15] - kp[18], kp[16] - kp[19])
        if shoulder_span < policy['minimumShoulderSpanPixels']:
            continue
        counts['adequate_shoulder_geometry'] += 1
        if not all(0 <= kp[3*j] < image['width'] and 0 <= kp[3*j+1] < image['height'] for j in JOINT_INDEX.values()):
            continue
        counts['target_coordinates_in_image'] += 1
        occluded = any(kp[3*j+2] == 1 for j in JOINT_INDEX.values())
        shoulder_y = (kp[16] + kp[19]) / 2
        raised = any(kp[3*j+1] < shoulder_y for j in (9, 10))
        stratum = 'occluded_v1' if occluded else 'primary_visible'
        pose_stratum = 'raised' if raised else 'lowered'
        rank = sha256(f"{policy['seed']}:{image['id']}:{annotation['id']}".encode())
        eligible[stratum].append({'image': image, 'annotation': annotation, 'rank': rank,
                                 'stratum': stratum, 'poseStratum': pose_stratum, 'bboxFraction': bbox_fraction,
                                 'shoulderSpanPixels': shoulder_span})
    selected = []
    summary = {}
    for stratum in sorted(eligible):
        entries = sorted(eligible[stratum], key=lambda e: e['rank'])
        requested = policy.get('stratumLimits', {}).get(stratum, len(entries))
        entries = entries[:requested]
        ncal = policy.get('splitCounts', {}).get(stratum, {}).get('calibration', math.floor(len(entries) * policy['calibrationFraction']))
        nheld = policy.get('splitCounts', {}).get(stratum, {}).get('heldout', len(entries) - ncal)
        assert ncal + nheld == len(entries), (stratum, ncal, nheld, len(entries))
        for index, entry in enumerate(entries):
            entry['split'] = 'calibration' if index < ncal else 'heldout'
            entry['id'] = f"coco2017_{entry['image']['id']:012d}_{entry['annotation']['id']}"
        selected.extend(entries)
        summary[stratum] = {'eligible': len(eligible[stratum]), 'selected': len(entries),
                            'calibration': ncal, 'heldout': len(entries) - ncal}
    if policy.get('noPersonAnnotationChallenge'):
        negative = []
        for image in data['images']:
            if image['license'] not in policy['allowedLicenseIds'] or grouped[image['id']]:
                continue
            rank = sha256(f"{policy['seed']}:no-person-annotation:{image['id']}".encode())
            negative.append({'image': image, 'annotation': None, 'rank': rank,
                             'stratum': 'no_person_annotation', 'poseStratum': 'unknown',
                             'bboxFraction': None, 'shoulderSpanPixels': None,
                             'id': f"coco2017_{image['id']:012d}_no_person_annotation"})
        negative.sort(key=lambda e: e['rank'])
        split_counts = policy['noPersonAnnotationChallenge']
        wanted = split_counts['calibration'] + split_counts['heldout']
        assert len(negative) >= wanted
        negative_selected = negative[:wanted]
        for index, entry in enumerate(negative_selected):
            entry['split'] = 'calibration' if index < split_counts['calibration'] else 'heldout'
        selected.extend(negative_selected)
        summary['no_person_annotation'] = {'eligible': len(negative), 'selected': wanted, **split_counts}
    return data, sorted(selected, key=lambda e: e['id']), {'eligibility': dict(counts), 'strata': summary}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', type=pathlib.Path, required=True)
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    policy = json.loads(args.policy.read_bytes())
    data, selected, summary = select(policy)
    if not args.freeze:
        print(json.dumps(summary, indent=2))
        return
    frozen_path = ROOT / 'selection.freeze.json'
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_bytes())
        frozen_at = frozen['frozenAtUtc']
    else:
        frozen_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    selection = {'schemaVersion': 1, 'frozenAtUtc': frozen_at,
                 'selectionBasis': 'Official human annotations and image license metadata only; no inference or prediction inspection.',
                 'sourceAnnotationsSha256': SOURCE_SHA256,
                 'policy': policy, 'summary': summary,
                 'images': [{'id': e['id'], 'imageId': e['image']['id'], 'annotationId': e['annotation']['id'] if e['annotation'] else None,
                             'split': e['split'], 'stratum': e['stratum'], 'poseStratum': e['poseStratum'], 'rankSha256': e['rank']}
                            for e in selected]}
    selection_sha = write_once(frozen_path, selection)
    gt = {'schemaVersion': 1, 'dataset': 'COCO2017 val person keypoints',
          'selectionFreezeSha256': selection_sha, 'sourceAnnotationsSha256': SOURCE_SHA256,
          'coordinateConvention': 'Original image pixels, 0-indexed; x horizontal and y vertical.',
          'visibilitySemantics': {'0': 'not labeled; x=y=0; coordinate accuracy unknown',
                                  '1': 'human labeled but not visible', '2': 'human labeled and visible'},
          'jointOrder': data['categories'][0]['keypoints'],
          'images': [{'id': e['id'], 'split': e['split'], 'stratum': e['stratum'],
                      'poseStratum': e['poseStratum'],
                      'imageId': e['image']['id'], 'annotationId': e['annotation']['id'] if e['annotation'] else None,
                      'width': e['image']['width'], 'height': e['image']['height'],
                      'bbox': e['annotation']['bbox'] if e['annotation'] else None, 'bboxImageAreaFraction': e['bboxFraction'],
                      'shoulderSpanPixels': e['shoulderSpanPixels'],
                      'kind': 'human-keypoints' if e['annotation'] else 'no-person-annotation',
                      'numKeypoints': e['annotation']['num_keypoints'] if e['annotation'] else 0,
                      'keypoints': e['annotation']['keypoints'] if e['annotation'] else [],
                      'joints': {name: {'x': e['annotation']['keypoints'][3*i],
                                        'y': e['annotation']['keypoints'][3*i+1],
                                        'visibility': e['annotation']['keypoints'][3*i+2]}
                                 for name, i in JOINT_INDEX.items()} if e['annotation'] else {}}
                     for e in selected]}
    gt_sha = write_once(ROOT / 'humanGT.json', gt)
    subset = {'info': data['info'], 'licenses': data['licenses'], 'categories': data['categories'],
              'images': [e['image'] for e in selected],
              'annotations': [e['annotation'] for e in selected if e['annotation']]}
    subset_sha = write_once(ROOT / 'source' / 'selected_coco_original.json', subset)
    for p in (SOURCE, frozen_path, ROOT / 'humanGT.json', ROOT / 'source' / 'selected_coco_original.json', args.policy):
        p.chmod(0o444)
    print(json.dumps({'selectionFreezeSha256': selection_sha, 'humanGTSha256': gt_sha,
                      'selectedCocoOriginalSha256': subset_sha, **summary}, indent=2))


if __name__ == '__main__':
    main()
