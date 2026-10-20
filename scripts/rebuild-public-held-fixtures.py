#!/usr/bin/env python3
"""Rebuild fixed public held/cut recipes into an ignored output directory.

Never replaces frozen manifests. Encoder version can change output hashes; the
report retains each original hash and flags mismatches rather than blessing them.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
PROJECT = Path(__file__).resolve().parent.parent
SOURCE_SHA = 'd891db0b4b326b5adaa07dbc6af080024ae4ed2e3e3e9c671bf8f75e39708c51'
SCHEDULE = [('N',20)] + [('L',10),('N',12),('R',10),('N',12)]*3
RECIPES = [
    ('held-public-arm-fixture.mp4',165,'e9bbe7ea50a037e6e8a0612fe3cea0ae22427bbc8d8dd042bc17e1edd3c4d4eb',
     'Constructed held/cut-pose fixture. Derived left is a horizontal reflection. Public Pexels video by Artem Podrez; not natural continuous motion or a human camera test.'),
    ('clear-public-arm-fixture.mp4',170,'1013d09d909140d42f500b937657ef9e84bd39bb132faf765a027220dde270dc',
     'Additional held/cut public-pose fixture using source170 above-head right raise and reflected derived left; source225 neutral. Prior source165 near-face failure preserved. Not natural motion or a user-camera test.'),
    ('frontal-held-source035.mp4',35,'e68c3455561c79178627942663bdab6d65a2095701044c743c1feef6c7b22521',None),
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def mirror(pixels):
    return b''.join(b''.join(pixels[y*1920+x*3:y*1920+x*3+3] for x in range(639,-1,-1)) for y in range(360))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=PROJECT/'sidecar/fixtures/.cache/pexels-artem-podrez-6003772.mp4')
    parser.add_argument('--output-dir',type=Path,default=PROJECT/'sidecar/fixtures/.cache/rebuilt')
    parser.add_argument('--ffmpeg',default='ffmpeg')
    args=parser.parse_args()
    source=args.source.expanduser().resolve(strict=True)
    if digest(source)!=SOURCE_SHA:
        raise ValueError('Pinned public-source SHA256 mismatch')
    output=args.output_dir.expanduser().resolve()
    output.mkdir(parents=True,exist_ok=True)
    version=subprocess.run([args.ffmpeg,'-version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
    def frame(index):
        data=subprocess.run([args.ffmpeg,'-nostdin','-v','error','-i',str(source),'-vf',f'select=eq(n\\,{index}),scale=640:360','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],check=True,capture_output=True).stdout
        if len(data)!=640*360*3:
            raise ValueError('Unexpected decoded frame size')
        return data
    neutral=frame(225)
    results=[]
    for filename,index,expected_hash,comment in RECIPES:
        target=output/filename
        if target.exists():
            raise FileExistsError('Refusing to replace previous reconstruction: '+str(target))
        right=frame(index)
        pixels={'N':neutral,'R':right,'L':mirror(right)}
        command=[args.ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','640x360','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2','-frames:v','152','-movflags','+faststart']
        if comment:
            command+=['-metadata','comment='+comment]
        command+=[str(target)]
        process=subprocess.run(command,input=b''.join(pixels[label]*count for label,count in SCHEDULE),check=True,capture_output=True)
        actual=digest(target)
        results.append(dict(file=filename,path=str(target),sha256=actual,originalFixtureSha256=expected_hash,
                            matchesOriginalEncoding=actual==expected_hash,rightSourceFrame=index,neutralSourceFrame=225,
                            derivedLeftIsReflection=True,frames=152,fps=10,expectedGestures=['left-raise','right-raise']*3))
    report=dict(sourceSha256=SOURCE_SHA,ffmpeg=version,thresholdTuning=False,modelInferenceUsed=False,cameraUsed=False,
                naturalContinuousMovement=False,results=results,
                limit='Output hash differences remain explicit. Do not overwrite recorded manifests or call regenerated media identical without matching hashes.')
    (output/'rebuild-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
