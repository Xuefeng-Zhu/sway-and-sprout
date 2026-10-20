#!/usr/bin/env python3
"""Rebuild two pinned continuous public-video derivatives, without PNG fixtures.

No download, capture, model inference, temporal cuts, expectation generation or
overwrite. Hash differences stay explicit; frozen fixture hashes never change.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


PROJECT = Path(__file__).resolve().parent.parent
SOURCE_SHA = 'd891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51'
SOURCE_BYTES = 31_111_153
RECIPES = [
    ('continuous-source-original640.mp4', 'scale=640:360',
     '88b8a08b43a516d7a73bb3fe1574a3742196e07c059c9b0a4ccbd3e1a6d0752c'),
    ('continuous-source-mirrored640.mp4', 'scale=640:360,hflip',
     'c9dff270546f41f3b3ba7f267e612f14fdc910e134dce37d2ac19ffbddbee9b7'),
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=PROJECT/'sidecar/fixtures/.cache/pexels-artem-podrez-6003772.mp4')
    parser.add_argument('--output-dir', type=Path,
                        default=PROJECT/'sidecar/fixtures/.cache/rebuilt-natural')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    args = parser.parse_args()
    source = args.source.expanduser().resolve(strict=True)
    if (not source.is_file() or source.stat().st_size != SOURCE_BYTES
            or digest(source) != SOURCE_SHA):
        parser.error('Pinned public-source size/SHA256 mismatch; no outputs created')
    output = args.output_dir.expanduser().resolve()
    targets = [output/name for name, _, _ in RECIPES]
    report_path = output/'rebuild-report.json'
    if any(path.exists() or path.is_symlink() for path in [*targets, report_path]):
        parser.error('Refusing to overwrite a previous reconstruction or report; choose a new output directory')
    versions = {name: subprocess.run([binary, '-version'], check=True, capture_output=True,
                                    text=True).stdout.splitlines()[0]
                for name, binary in [('ffmpeg', args.ffmpeg), ('ffprobe', args.ffprobe)]}
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for (name, filters, frozen_hash), target in zip(RECIPES, targets):
        subprocess.run([args.ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', str(source),
                        '-vf', filters, '-an', '-c:v', 'libx264', '-preset', 'fast',
                        '-crf', '18', '-pix_fmt', 'yuv420p', '-threads', '2',
                        '-fps_mode', 'passthrough', '-movflags', '+faststart', str(target)],
                       check=True, capture_output=True)
        probe = json.loads(subprocess.run([
            args.ffprobe, '-v', 'error', '-select_streams', 'v:0', '-count_frames',
            '-show_entries', 'stream=width,height,avg_frame_rate,duration,nb_read_frames',
            '-of', 'json', str(target)], check=True, capture_output=True, text=True).stdout)
        if len(probe['streams']) != 1:
            raise ValueError('Expected exactly one probed video stream')
        stream = probe['streams'][0]
        actual = digest(target)
        shape_and_timing = (stream['width'] == 640 and stream['height'] == 360
                            and stream['avg_frame_rate'] == '30/1'
                            and int(stream['nb_read_frames']) == 319)
        results.append({'file': name, 'bytes': target.stat().st_size, 'sha256': actual,
                        'frozenSha256': frozen_hash, 'matchesFrozenEncoding': actual == frozen_hash,
                        'probe': stream, 'dimensionsAndFrameCadenceMatch': shape_and_timing,
                        'horizontalReflection': filters.endswith(',hflip')})
    report = {'sourceFile': source.name, 'sourceSha256': SOURCE_SHA,
              'sourceBytes': SOURCE_BYTES, **versions, 'physicalCameraUsed': False,
              'networkUsed': False, 'modelInferenceUsed': False, 'pngInputsRequired': False,
              'frameOrderPreserved': True, 'timeChanges': False, 'results': results,
              'allFrozenHashesMatch': all(row['matchesFrozenEncoding'] for row in results),
              'allDimensionsAndFrameCadenceMatch': all(row['dimensionsAndFrameCadenceMatch'] for row in results),
              'limit': 'Reconstruction only; dancing footage and its reflection do not certify a complete alternating game sequence.'}
    with report_path.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    if not report['allFrozenHashesMatch'] or not report['allDimensionsAndFrameCadenceMatch']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
