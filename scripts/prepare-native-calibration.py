#!/usr/bin/env python3
"""Copy only an explicitly frozen local image manifest into DEBUG assets. No network/inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

PROJECT = Path(__file__).resolve().parent.parent
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular file: ' + str(path))


def jpeg_dimensions(data):
    if data[:2] != b'\xff\xd8':
        raise ValueError('JPEG required')
    offset = 2
    while offset < len(data):
        if data[offset] != 255:
            raise ValueError('Invalid JPEG header')
        while offset < len(data) and data[offset] == 255:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if marker in (0xD9, 0xDA) or offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset + 2], 'big')
        if length < 2 or offset + length > len(data):
            raise ValueError('Invalid JPEG segment')
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if length < 8:
                raise ValueError('Invalid JPEG frame')
            return int.from_bytes(data[offset + 5:offset + 7], 'big'), int.from_bytes(data[offset + 3:offset + 5], 'big')
        offset += length
    raise ValueError('JPEG dimensions unavailable')


def verify_manifest(manifest_path, expected_sha, asset_root):
    regular(manifest_path)
    data = manifest_path.read_bytes()
    if not 1 <= len(data) <= 4 * 1024 * 1024 or sha(data) != expected_sha:
        raise ValueError('Frozen manifest size/SHA mismatch')
    manifest = json.loads(data)
    if type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1:
        raise ValueError('Manifest schema mismatch')
    images = manifest.get('images')
    if not isinstance(images, list) or not 2 <= len(images) <= 1000:
        raise ValueError('Manifest image count')
    ids, hashes, splits, sources = set(), set(), set(), []
    for image in images:
        ident, digest, split = image.get('id', ''), image.get('sha256', ''), image.get('split', '')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', ident):
            raise ValueError('Image id')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Image SHA')
        if image.get('asset') != 'calibration/' + digest + '.jpg' or split not in ('calibration', 'heldout'):
            raise ValueError('Image path/split')
        if ident in ids or digest in hashes:
            raise ValueError('Duplicate image/id, including cross-split leakage')
        ids.add(ident); hashes.add(digest); splits.add(split)
        size, width, height = (image.get(key) for key in ('bytes', 'width', 'height'))
        if any(type(n) is not int for n in (size, width, height)) or not 1 <= size <= MAX_IMAGE_BYTES or not 32 <= width <= 4096 or not 32 <= height <= 4096 or width * height > 4 * 1024 * 1024:
            raise ValueError('Image size contract')
        source = asset_root / image['asset']
        if source.resolve().parent != (asset_root / 'calibration').resolve() or (asset_root / 'calibration').is_symlink():
            raise ValueError('Image escapes fixed source directory')
        regular(source)
        if source.stat().st_size != size:
            raise ValueError('Image byte count')
        image_data = source.read_bytes()
        if sha(image_data) != digest or jpeg_dimensions(image_data) != (width, height):
            raise ValueError('Image SHA/dimensions')
        sources.append((source, digest + '.jpg'))
    if splits != {'calibration', 'heldout'}:
        raise ValueError('Both frozen splits required')
    return data, sources


def prepare(project, manifest_path, expected_sha, asset_root):
    data, sources = verify_manifest(manifest_path, expected_sha, asset_root)
    target = project / 'android/app/src/debug/assets/calibration'
    pin_dir = project / '.toolchain/native-calibration'
    for path in (target, pin_dir):
        for parent in (path, *path.parents):
            if parent == project:
                break
            if parent.is_symlink():
                raise ValueError('Refusing generated symlink path')
    pin = {'schemaVersion': 1, 'datasetId': 'dataset-' + expected_sha[:16], 'manifestSha256': expected_sha, 'manifestBytes': len(data)}
    encoded_pin = (json.dumps(pin, indent=2) + '\n').encode()
    pin_file = pin_dir / 'pin.json'
    if pin_file.exists() or pin_file.is_symlink():
        regular(pin_file)
        if pin_file.read_bytes() != encoded_pin:
            raise ValueError('Refusing to replace another frozen dataset pin')
    if target.exists() or target.is_symlink():
        if not target.is_dir() or target.is_symlink():
            raise ValueError('Expected generated asset directory')
        expected_names = {'manifest.json', *(name for _, name in sources)}
        if {p.name for p in target.iterdir()} != expected_names:
            raise ValueError('Existing dataset has different files')
        regular(target / 'manifest.json')
        if (target / 'manifest.json').read_bytes() != data:
            raise ValueError('Refusing different existing manifest')
        for source, name in sources:
            regular(target / name)
            if (target / name).stat().st_size != source.stat().st_size or sha((target / name).read_bytes()) != name[:-4]:
                raise ValueError('Existing dataset image mismatch')
    else:
        pin_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='staging-', dir=pin_dir) as temporary:
            stage = Path(temporary) / 'calibration'; stage.mkdir()
            (stage / 'manifest.json').write_bytes(data)
            for source, name in sources:
                shutil.copyfile(source, stage / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError('Asset target appeared concurrently')
            os.rename(stage, target)
    pin_dir.mkdir(parents=True, exist_ok=True)
    if not pin_file.exists():
        with pin_file.open('xb') as stream:
            stream.write(encoded_pin)
    return {'status': 'prepared', 'images': len(sources), **pin, 'networkUsed': False, 'inferenceRun': False, 'cameraUsed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256', required=True, help='Exact SHA fixed before inference')
    parser.add_argument('--asset-root', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{64}', args.sha256):
        parser.error('Exact lowercase SHA256 required')
    manifest = args.manifest.expanduser().absolute()
    root = (args.asset_root or manifest.parent).expanduser().resolve(strict=True)
    print(json.dumps(prepare(PROJECT.resolve(), manifest, args.sha256, root)))


if __name__ == '__main__':
    main()
