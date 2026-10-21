#!/usr/bin/env python3
"""Offline verify/reconstruct fixed study excerpts; never downloads or overwrites."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
from fractions import Fraction

HERE = pathlib.Path(__file__).resolve().parent

def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def local_file(value, label):
    if value is None:
        raise ValueError(f'{label} must be supplied as an existing local file')
    path = pathlib.Path(value).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'{label} is not a local file: {path}')
    return path

def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout

def probe(ffprobe, path):
    output = run([ffprobe, '-v', 'error', '-protocol_whitelist', 'file,pipe',
                  '-select_streams', 'v:0', '-show_entries',
                  'stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames',
                  '-of', 'json', str(path)])
    return json.loads(output)['streams'][0]

def frame_hashes(ffmpeg, path, start=None, end=None):
    command = [ffmpeg, '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
               '-i', str(path), '-map', '0:v:0']
    if start is not None:
        command += ['-vf', f'trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS']
    command += ['-an', '-fps_mode', 'passthrough', '-pix_fmt', 'yuv420p',
                '-f', 'framehash', '-hash', 'sha256', '-']
    output = run(command)
    rows = [line.split(',') for line in output.splitlines() if line and not line.startswith('#')]
    hashes = [row[-1].strip() for row in rows]
    if not hashes or any(len(value) != 64 for value in hashes):
        raise ValueError(f'Unexpected decoded framehash output: {path}')
    return hashes

def sequence_sha(hashes):
    # Deliberately explicit: lowercase hexadecimal frame SHA256s joined with LF,
    # including one final LF, encoded as UTF-8. Each frame is decoded yuv420p.
    return hashlib.sha256(('\n'.join(hashes) + '\n').encode('utf-8')).hexdigest()

def verify(ffmpeg, ffprobe, item, source, derivative, allow_container_difference):
    source_sha = sha_file(source)
    if source_sha != item['sourceSha256']:
        raise ValueError(f"Source byte pin failed for {item['case']}: {source_sha}")
    container_sha = sha_file(derivative)
    container_matches = container_sha == item['derivativeSha256']
    if not container_matches and not allow_container_difference:
        raise ValueError(f"Derivative byte pin failed for {item['case']}: {container_sha}. "
                         'Use --allow-container-difference only to inspect a newly reconstructed candidate; '
                         'it never updates the canonical pin.')
    metadata = probe(ffprobe, derivative)
    expected = item['video']
    if metadata['width'] != expected['width'] or metadata['height'] != expected['height']:
        raise ValueError(f"Dimensions changed for {item['case']}")
    if metadata['pix_fmt'] != 'yuv420p' or metadata['codec_name'] != 'h264':
        raise ValueError(f"Codec/pixel format changed for {item['case']}")
    if Fraction(metadata['avg_frame_rate']) != Fraction(expected['fps']):
        raise ValueError(f"Cadence changed for {item['case']}")
    original = frame_hashes(ffmpeg, source, item['startFrame'], item['endFrameExclusive'])
    excerpt = frame_hashes(ffmpeg, derivative)
    if len(excerpt) != item['frames'] or excerpt != original:
        raise ValueError(f"Decoded YUV sequence differs from the fixed source interval: {item['case']}")
    sequence = sequence_sha(excerpt)
    if sequence != item['decodedYuv420pSha256SequenceLfSha256']:
        raise ValueError(f"Decoded YUV sequence pin changed for {item['case']}: {sequence}")
    return {'case': item['case'], 'source': str(source), 'sourceSha256': source_sha,
            'sourceStartFrame': item['startFrame'], 'sourceEndFrameExclusive': item['endFrameExclusive'],
            'derivative': str(derivative), 'derivativeSha256': container_sha,
            'derivativeBytes': derivative.stat().st_size, 'canonicalDerivativePinMatches': container_matches,
            'canonicalPinNeedsExplicitReviewAndUpdate': not container_matches,
            'frames': len(excerpt), 'decodedYuv420pFrameSequenceEqual': True,
            'decodedYuv420pSha256SequenceLfSha256': sequence, 'ffprobe': metadata}

def reconstruct(ffmpeg, source, item, output):
    command = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-n',
               '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:v:0',
               '-vf', f"trim=start_frame={item['startFrame']}:end_frame={item['endFrameExclusive']},setpts=PTS-STARTPTS",
               '-an', '-map_metadata', '-1', '-map_chapters', '-1', '-c:v', 'libx264',
               '-crf', '0', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', str(output)]
    subprocess.run(command, check=True)
    return command

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'reconstruct'))
    parser.add_argument('--case', choices=('all', 'left-natural', 'right-short'), default='all')
    parser.add_argument('--left-source')
    parser.add_argument('--right-source')
    parser.add_argument('--derivative-dir', help='Required for verify; contains the existing named MP4s')
    parser.add_argument('--output-dir', help='Required for reconstruct; directory must not already exist')
    parser.add_argument('--report', help='Optional JSON report path; must not already exist')
    parser.add_argument('--allow-container-difference', action='store_true',
                        help='Explicitly inspect pixel-identical reconstruction with a different MP4 SHA; never updates any pin')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    args = parser.parse_args()
    lock_path = HERE / 'study-clips.lock.json'
    lock = json.loads(lock_path.read_bytes())
    selected = [item for item in lock['clips'] if args.case in ('all', item['case'])]
    sources = {}
    for item in selected:
        value = args.left_source if item['case'] == 'left-natural' else args.right_source
        source = local_file(value, item['case'] + ' source')
        if sha_file(source) != item['sourceSha256']:
            raise ValueError(f"Pinned source bytes do not match: {item['case']}")
        sources[item['case']] = source
    report_path = pathlib.Path(args.report).expanduser().resolve() if args.report else None
    if report_path and report_path.exists():
        raise FileExistsError(f'Refusing to overwrite report: {report_path}')
    if args.mode == 'verify':
        if not args.derivative_dir or args.output_dir:
            parser.error('verify requires --derivative-dir and does not accept --output-dir')
        directory = pathlib.Path(args.derivative_dir).expanduser().resolve(strict=True)
    else:
        if not args.output_dir or args.derivative_dir:
            parser.error('reconstruct requires --output-dir and does not accept --derivative-dir')
        directory = pathlib.Path(args.output_dir).expanduser().resolve()
        directory.mkdir(exist_ok=False)
    commands = []
    results = []
    for item in selected:
        derivative = directory / item['filename']
        if args.mode == 'reconstruct':
            commands.append(reconstruct(args.ffmpeg, sources[item['case']], item, derivative))
        else:
            derivative = local_file(derivative, item['case'] + ' derivative')
        results.append(verify(args.ffmpeg, args.ffprobe, item, sources[item['case']], derivative,
                              args.allow_container_difference))
    report = {'schemaVersion': 1, 'verifiedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'mode': args.mode, 'lockSha256': sha_file(lock_path),
              'ffmpegVersion': run([args.ffmpeg, '-version']).splitlines()[0],
              'ffprobeVersion': run([args.ffprobe, '-version']).splitlines()[0],
              'networkDownloads': False, 'overwrites': False, 'poseInference': False,
              'reconstructionCommands': commands, 'clips': results}
    encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if report_path:
        with report_path.open('x') as handle:
            handle.write(encoded)
    print(encoded, end='')

if __name__ == '__main__':
    main()
