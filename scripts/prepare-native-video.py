#!/usr/bin/env python3
"""Explicit, pinned preparation of local native DEBUG video verification assets.

Offline by default. Copies only verified artifacts and already-restored fixtures.
--download opts into bounded official artifact downloads; never downloads media,
installs software, accepts terms, builds, opens a camera, or runs inference.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parent.parent
OFFICIAL_HOSTS = frozenset(('dl.google.com', 'tfhub.dev', 'www.kaggle.com',
                            'kaggle.com', 'storage.googleapis.com', 'repo.maven.apache.org'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path, pin):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing regular pinned file: ' + str(path))
    if path.stat().st_size != pin['bytes'] or sha256(path) != pin['sha256']:
        raise ValueError('Pinned size/SHA256 mismatch: ' + str(path))


def inside(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root):
        raise ValueError('Output path escapes project: ' + relative)
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('Refusing symlink path: ' + str(part))
    return path


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def model_artifacts(lock):
    return [item for item in lock['artifacts'] if item['role'] in ('model', 'candidate-model')]


def model_config_name(fixture, model):
    return fixture['config'] if model['role'] == 'model' else fixture['config'][:-5] + '.' + model['modelId'] + '.json'


def expected_config(lock, fixture, model=None):
    model = model or next(item for item in lock['artifacts'] if item['role'] == 'model')
    return {'schemaVersion': 1, 'runtimeVersion': lock['runtimeVersion'],
            'model': {'asset': model['asset'], 'bytes': model['bytes'],
                      'sha256': model['sha256']},
            'fixture': {'asset': fixture['asset'], 'bytes': fixture['bytes'],
                        'sha256': fixture['sha256'], 'fps': fixture['fps'],
                        'frames': fixture['frames'],
                        'expectedGestures': fixture['expectedGestures'],
                        'expectationKnown': fixture['expectationKnown']}}


def validate_lock(lock):
    if lock['schemaVersion'] != 1 or lock['runtimeVersion'] != '1.4.2':
        raise ValueError('Unsupported native runtime lock schema/version')
    cases = ['clear', 'frontal', 'nearface', 'right-negative', 'both-up-negative',
             'natural-original', 'natural-mirror', 'left-natural', 'right-short']
    if [row['case'] for row in lock['fixtures']] != cases:
        raise ValueError('Expected exactly the seven baseline and two independently bound study cases')
    for row in lock['fixtures']:
        if type(row['expectationKnown']) is not bool:
            raise ValueError('expectationKnown must be an explicit boolean')
        if row['case'] in ('natural-original', 'natural-mirror'):
            if row['expectationKnown'] or row['expectedGestures']:
                raise ValueError('Partial natural clips must remain observed-only')
        elif not row['expectationKnown']:
            raise ValueError('Known frozen controls must retain their expectations')
    models = model_artifacts(lock)
    expected_models = {
        'int8': ('model', 2894840, 'cd7cc22fa946e5d146a7b98d496853e1923e22828d3972d579973f27f91bb105', 'verification/movenet-lightning-int8.tflite', 192),
        'float16': ('candidate-model', 4758512, '0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab', 'verification/movenet-lightning-float16.tflite', 192),
        'thunder': ('candidate-model', 12584128, '41641538679ec79b07d4101e591dda47d098c09af29607674b2a40b8a3798dd3', 'verification/movenet-thunder-float16.tflite', 256)}
    def model_id(row):
        return 'int8' if row['role'] == 'model' else row.get('modelId')
    if len(models) != 3 or {model_id(row) for row in models} != set(expected_models):
        raise ValueError('Expected pinned INT8 baseline and explicit Lightning FP16/Thunder candidates')
    for row in models:
        identity = model_id(row)
        if identity not in expected_models:
            raise ValueError('Unknown native candidate model')
        expected = expected_models[identity]
        if (row['role'], row['bytes'], row['sha256'], row['asset']) != expected[:4]:
            raise ValueError('Native model role/pin mismatch')
        if row['input'] != {'type': 'UINT8', 'shape': [1, expected[4], expected[4], 3], 'color': 'RGB', 'values': [0, 255]}:
            raise ValueError('Native model input contract mismatch')
        if row['output'] != {'type': 'FLOAT32', 'shape': [1, 1, 17, 3], 'order': ['y', 'x', 'score']}:
            raise ValueError('Native model output contract mismatch')
    for row in [*lock['artifacts'], *lock['fixtures']]:
        if type(row['bytes']) is not int or row['bytes'] <= 0:
            raise ValueError('Invalid pinned byte count')
        if len(row['sha256']) != 64 or any(c not in '0123456789abcdef' for c in row['sha256']):
            raise ValueError('Invalid SHA256 pin')


def check_existing_target(path, pin=None, contents=None):
    if not path.exists() and not path.is_symlink():
        return
    if pin is not None:
        verify(path, pin)
    elif path.is_symlink() or not path.is_file() or path.read_bytes() != contents:
        raise ValueError('Refusing to replace different existing config: ' + str(path))


def copy_verified(source, target, pin):
    check_existing_target(target, pin=pin)
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.native-prepare-', dir=target.parent,
                                     delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with source.open('rb') as source_stream:
                shutil.copyfileobj(source_stream, stream)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        verify(temporary, pin)
        # Exclusive link never overwrites a concurrently created unrelated file.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def write_config(target, contents):
    check_existing_target(target, contents=contents)
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(contents)


def official_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in OFFICIAL_HOSTS or parsed.username or parsed.password:
        raise ValueError('Refusing non-official/non-HTTPS artifact URL')


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(pin, target):
    official_url(pin['url'])
    target.parent.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(OfficialRedirects())
    with opener.open(pin['url'], timeout=45) as response:
        official_url(response.url)
        length = response.headers.get('Content-Length')
        if length is not None and int(length) != pin['bytes']:
            raise ValueError('Official response size differs from pin')
        with tempfile.NamedTemporaryFile(prefix='.native-download-', dir=target.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            try:
                remaining = pin['bytes'] + 1
                while remaining:
                    chunk = response.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    stream.write(chunk)
                    remaining -= len(chunk)
                stream.flush()
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
    try:
        verify(temporary, pin)
        copy_verified(temporary, target, pin)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=PROJECT)
    parser.add_argument('--artifact-dir', type=Path,
                        help='Explicit directory containing the pinned artifact filenames')
    parser.add_argument('--download', action='store_true',
                        help='Explicitly allow only missing pinned runtime/model downloads from official URLs')
    parser.add_argument('--check', action='store_true',
                        help='Read-only check of all prepared artifacts, source fixtures, assets and configs')
    args = parser.parse_args()
    if args.check and (args.artifact_dir is not None or args.download):
        parser.error('--check is read-only; do not combine with --artifact-dir or --download')
    root = args.project_root.expanduser().resolve(strict=True)
    lock = json.loads(inside(root, 'android/native-video-assets.lock.json').read_text())
    validate_lock(lock)
    asset_root = inside(root, lock['debugAssetsDirectory'])
    sources = [(row, inside(root, row['source'])) for row in lock['fixtures']]
    # Every fixture must already exist and match frozen bytes before any write/download.
    for pin, source in sources:
        verify(source, pin)
    artifacts = [(row, inside(root, row['target'])) for row in lock['artifacts']]
    source_artifacts = {}
    for pin, target in artifacts:
        if target.exists() or target.is_symlink():
            verify(target, pin)
            source_artifacts[pin['filename']] = target
        elif args.artifact_dir is not None:
            source = args.artifact_dir.expanduser().resolve(strict=True) / pin['filename']
            verify(source, pin)
            source_artifacts[pin['filename']] = source
        elif not args.download or args.check:
            raise ValueError('Missing pinned artifact; supply --artifact-dir or explicitly --download: ' + str(target))
    outputs = []
    for pin, source in sources:
        outputs.append((inside(asset_root, pin['asset']), pin, source))
    models = model_artifacts(lock)
    for model in models:
        outputs.append((inside(asset_root, model['asset']), model, inside(root, model['target'])))
    configs = [(inside(asset_root, model_config_name(row, model)), encoded(expected_config(lock, row, model)))
               for row in lock['fixtures'] for model in models]
    for target, pin, source in outputs:
        if args.check:
            verify(target, pin)
        else:
            check_existing_target(target, pin=pin)
    for target, contents in configs:
        if args.check:
            if not target.is_file() or target.is_symlink() or target.read_bytes() != contents:
                raise ValueError('Prepared config differs from exact locked config: ' + str(target))
        else:
            check_existing_target(target, contents=contents)
    if not args.check:
        for pin, target in artifacts:
            source = source_artifacts.get(pin['filename'])
            if source is None:
                download(pin, target)
            else:
                copy_verified(source, target, pin)
        for target, pin, source in outputs:
            copy_verified(source, target, pin)
        for target, contents in configs:
            write_config(target, contents)
    print(json.dumps({'status': 'checked' if args.check else 'prepared',
                      'runtimeVersion': lock['runtimeVersion'], 'artifacts': len(artifacts),
                      'fixtureAssets': len(sources), 'modelAssets': len(models), 'configs': len(configs),
                      'networkOptIn': args.download, 'cameraUsed': False, 'inferenceRun': False,
                      'naturalClipsObservedOnly': True}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print('native video preparation failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
