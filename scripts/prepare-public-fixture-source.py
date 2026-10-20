#!/usr/bin/env python3
"""Verify/copy one pinned public source; downloading requires --download.

Uses only Python's standard library. No camera, model inference, service, or
private media. The default verifies an existing ignored local cache file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request

PROJECT = Path(__file__).resolve().parent.parent
URL = 'https://videos.pexels.com/video-files/6003772/6003772-uhd_3840_2160_30fps.mp4'
EXPECTED_SHA = 'd891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51'
EXPECTED_BYTES = 31111153


def verify(path):
    if not path.is_file() or path.stat().st_size != EXPECTED_BYTES:
        raise ValueError('Public source size mismatch: ' + str(path))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError('Public source SHA256 mismatch: ' + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=PROJECT/'sidecar/fixtures/.cache/pexels-artem-podrez-6003772.mp4')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--from-file', type=Path, help='Verified offline local public-source copy')
    mode.add_argument('--download', action='store_true', help='Explicitly fetch the fixed public HTTPS URL')
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.exists():
        verify(destination)
        action = 'verified-existing'
    elif not args.from_file and not args.download:
        parser.error('No cached public source. Supply --from-file or explicitly --download.')
    else:
        if args.from_file:
            verify(args.from_file.expanduser().resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.public-source-', delete=False) as temp:
            temporary = Path(temp.name)
        try:
            if args.from_file:
                shutil.copyfile(args.from_file.expanduser().resolve(), temporary)
            else:
                request = urllib.request.Request(URL, headers={'User-Agent':'SwayAndSprout-local-fixture-check/1'})
                with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as out:
                    remaining = EXPECTED_BYTES + 1
                    while remaining:
                        chunk = response.read(min(1024*1024, remaining))
                        if not chunk:
                            break
                        out.write(chunk)
                        remaining -= len(chunk)
            verify(temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        action = 'copied-local-public-source' if args.from_file else 'downloaded-fixed-public-source'
    print(json.dumps(dict(action=action,path=str(destination),bytes=EXPECTED_BYTES,sha256=EXPECTED_SHA,
                          sourceUrl=URL,creator='Artem Podrez',license='https://www.pexels.com/license/',
                          cameraUsed=False,modelInferenceUsed=False,uploaded=False)))


if __name__ == '__main__':
    main()
