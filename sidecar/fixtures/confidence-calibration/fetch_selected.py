#!/usr/bin/env python3
"""Fetch only frozen COCO images and public source-page credit metadata. No inference."""
import concurrent.futures
import datetime
import hashlib
import html
import io
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def fetch(url, limit=MAX_RESPONSE_BYTES):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'HumanKeypointCalibrationResearch/1.0'})
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise ValueError(f'Response exceeded {limit} bytes: {url}')
                return raw, response.geturl(), dict(response.headers)
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def attribution(image):
    # Official COCO metadata links the source Flickr image. Its leading filename number is the Flickr photo ID.
    photo_id = pathlib.PurePosixPath(urllib.parse.urlparse(image['flickr_url']).path).name.split('_')[0]
    assert photo_id.isdigit()
    url = f'https://www.flickr.com/photo.gne?id={photo_id}'
    result = {'sourcePhotoId': photo_id, 'requestedUrl': url, 'cocoFlickrUrl': image['flickr_url']}
    try:
        raw, final_url, headers = fetch(url, 2 * 1024 * 1024)
        text = raw.decode('utf-8')
        marker = 'modelExport:'
        position = text.find(marker)
        if position < 0:
            raise ValueError('Public photo metadata is unavailable')
        model, _ = json.JSONDecoder().raw_decode(text[position+len(marker):].lstrip())
        photo = model['main']['photo-models'][0]['data']
        assert str(photo['id']) == photo_id
        owner = photo['owner']['data']
        credit = owner.get('realname') or owner.get('username')
        assert credit
        result.update({'status': 'resolved_public_flickr_page', 'pageSha256': digest(raw), 'pageBytes': len(raw),
                       'resolvedUrl': final_url, 'title': photo.get('title', ''),
                       'creator': credit, 'creatorUsername': owner.get('username'),
                       'creatorNsid': owner.get('id'), 'creatorPathAlias': owner.get('pathAlias'),
                       'creatorUrl': 'https://www.flickr.com/photos/' + (owner.get('pathAlias') or owner['id']) + '/',
                       'currentFlickrLicenseId': photo.get('license'),
                       'cocoLicenseId': image['license'],
                       'licenseMatchesCocoMetadata': photo.get('license') == image['license'],
                       'retrievedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    except Exception as error:
        result.update({'status': 'source_page_unavailable_or_unparseable', 'error': str(error),
                       'retrievedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return result


def process(pair):
    selection, image = pair
    cache = ROOT / 'source' / 'fetch-records' / f"{selection['id']}.json"
    if cache.exists():
        cached = json.loads(cache.read_bytes())
        image_path = ROOT / cached['manifestImage']['asset']
        assert digest(image_path.read_bytes()) == cached['manifestImage']['sha256']
        return cached
    url = 'https://s3.amazonaws.com/images.cocodataset.org/val2017/' + image['file_name']
    raw, final_url, headers = fetch(url)
    with Image.open(io.BytesIO(raw)) as decoded:
        assert decoded.format == 'JPEG'
        assert decoded.size == (image['width'], image['height'])
        decoded.verify()
    sha = digest(raw)
    asset = 'calibration/' + sha + '.jpg'
    path = ROOT / asset
    if not path.exists():
        path.write_bytes(raw)
    else:
        assert path.read_bytes() == raw
    path.chmod(0o444)
    entry = {'id': selection['id'], 'asset': asset, 'sha256': sha, 'bytes': len(raw),
             'width': image['width'], 'height': image['height'], 'split': selection['split'],
             'stratum': selection['stratum'], 'poseStratum': selection['poseStratum'],
             'kind': 'human-keypoints' if selection['annotationId'] is not None else 'no-person-annotation',
             'sourceImageId': image['id'], 'sourceAnnotationId': selection['annotationId'],
             'licenseId': image['license'], 'cocoUrl': image['coco_url'], 'flickrUrl': image['flickr_url']}
    record = {'manifestImage': entry, 'download': {'requestedUrl': url, 'resolvedUrl': final_url,
               'retrievedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'etag': headers.get('ETag'), 'lastModified': headers.get('Last-Modified')},
               'attribution': attribution(image)}
    cache.write_bytes(canonical(record))
    cache.chmod(0o444)
    return record


def main():
    freeze_raw = (ROOT / 'selection.freeze.json').read_bytes()
    frozen = json.loads(freeze_raw)
    source = json.loads((ROOT / 'source' / 'selected_coco_original.json').read_bytes())
    by_image = {image['id']: image for image in source['images']}
    (ROOT / 'calibration').mkdir(exist_ok=True)
    (ROOT / 'source' / 'fetch-records').mkdir(exist_ok=True)
    pairs = [(entry, by_image[entry['imageId']]) for entry in frozen['images']]
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process, pair) for pair in pairs]
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            print(f"{len(records)}/{len(pairs)} {record['manifestImage']['id']} {record['attribution']['status']}", flush=True)
    records.sort(key=lambda r: r['manifestImage']['id'])
    manifest = {'schemaVersion': 1, 'dataset': 'COCO2017 val human-keypoint calibration pilot',
                'selectionFreezeSha256': digest(freeze_raw),
                'humanGTSha256': digest((ROOT / 'humanGT.json').read_bytes()),
                'images': [r['manifestImage'] for r in records]}
    for key in ('sourceImageId', 'sourceAnnotationId', 'sha256'):
        left = {i[key] for i in manifest['images'] if i['split'] == 'calibration' and i[key] is not None}
        right = {i[key] for i in manifest['images'] if i['split'] == 'heldout' and i[key] is not None}
        assert left.isdisjoint(right), f'{key} split overlap: {left & right}'
    credits = {'schemaVersion': 1, 'imageLicenseMetadataSource': 'Original COCO2017 val JSON',
               'creditsSource': 'Public original Flickr photo pages; unavailable sources explicitly flagged',
               'licenses': source['licenses'],
               'images': [{'id': r['manifestImage']['id'], **r['attribution']} for r in records]}
    for name, value in [('manifest.json', manifest), ('credits.json', credits)]:
        path = ROOT / name
        payload = canonical(value)
        if path.exists():
            assert path.read_bytes() == payload, f'Refusing to replace frozen {name}'
        else:
            path.write_bytes(payload)
        path.chmod(0o444)
    print(json.dumps({'manifestSha256': digest((ROOT / 'manifest.json').read_bytes()),
                      'images': len(records), 'imageBytes': sum(r['manifestImage']['bytes'] for r in records),
                      'resolvedCredits': sum(r['attribution']['status'] == 'resolved_public_flickr_page' for r in records),
                      'licenseDisagreements': [r['manifestImage']['id'] for r in records
                                              if r['attribution'].get('licenseMatchesCocoMetadata') is False]}, indent=2))


if __name__ == '__main__':
    main()
