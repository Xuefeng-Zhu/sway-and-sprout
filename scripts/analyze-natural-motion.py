#!/usr/bin/env python3
"""Scalar-only local-video diagnosis; camera and sockets prohibited."""
from collections import Counter
from dataclasses import asdict
import argparse
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
from unittest import mock

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project',type=Path,default=Path.cwd(),help='Canonical repository root')
parser.add_argument('--output',type=Path,required=True,help='Local directory for scalar-only JSON')
args=parser.parse_args()
PROJECT=args.project.expanduser().resolve(strict=True)
OUT=args.output.expanduser().resolve()
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'sidecar'))
from inference import OpenCVPose
from service import MotionService
from video_input import open_video,wrist_gates

CLIENT='12345678-0000-4000-8000-000000000101'
ROUND='12345678-0000-4000-8000-000000000102'
files=PROJECT/'sidecar/fixtures/frontal/bounded-frontal'
lock=json.loads((files/'encoded-media-manifest.json').read_text())
hashes={r['file']:r['sha256'] for r in lock}
sources=['sidecar/inference.py','sidecar/motion.py','sidecar/service.py',
         'sidecar/vendor/mp_persondet.py','sidecar/vendor/mp_pose.py',
         'sidecar/video_input.py','src/motion.js','scripts/score-motion-fixture.mjs']
code_hashes={name:hashlib.sha256((PROJECT/name).read_bytes()).hexdigest() for name in sources}
pose=OpenCVPose()
original_capture=pose.cv.VideoCapture
detector=pose.detector.infer
preprocess=pose.pose._preprocess
state={}

def detected(frame):
    people=detector(frame)
    state['detections']=[p.tolist() for p in people]
    return people

def preprocessed(frame, person):
    original=person.copy()
    data=preprocess(frame,person)
    blob,box,angle,matrix,pad=data
    state['roi']={'person':original.tolist(),'angle':float(angle),'padding':pad.tolist(),
                  'box':box.tolist(),'matrix':matrix.tolist()}
    return data

pose.detector.infer=detected
pose.pose._preprocess=preprocessed

def intervals(frames,key,predicate):
    out=[];start=None
    for i,f in enumerate(frames):
        if predicate(f.get(key)):
            if start is None:start=i
        elif start is not None:
            out.append([start,i-1]);start=None
    if start is not None:out.append([start,len(frames)-1])
    return out

reports={}
for name in ('continuous-source-original640.mp4','continuous-source-mirrored640.mp4'):
    path=files/name
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest==hashes[name],name
    opened=[];api={'camera':0,'socket':0}
    def capture_file(value,backend):
        if not isinstance(value,str) or Path(value).resolve()!=path.resolve() or backend!=pose.cv.CAP_FFMPEG:
            api['camera']+=1
            raise AssertionError('Only exact frozen local file may be decoded')
        opened.append({'source':'local-file','backend':'CAP_FFMPEG'})
        return original_capture(value,backend)
    def blocked_socket(*a,**kw):
        api['socket']+=1
        raise AssertionError('Sockets prohibited')
    now=0.
    service=MotionService(pose.runtime,'video',clock=lambda:now)
    control=dict(clientId=CLIENT,roundId=ROUND,revision=0,active=True,mode='standing',after=0)
    service.poll(control)
    rows=[];events=[];packets=[]
    with mock.patch.object(pose.cv,'VideoCapture',side_effect=capture_file),mock.patch.object(socket,'socket',side_effect=blocked_socket):
        cap,fps=open_video(path,pose.cv)
        try:
            index=0
            while index<3600:
                ok,frame=cap.read()
                if not ok:break
                now=index*1000/fps
                service.poll(control)
                token=service.token()
                state.clear()
                obs,status,duration=pose.infer(frame)
                before={'armed':service.machine.armed,'neutralSince':service.machine.neutral_since,
                        'holdSince':service.machine.hold_since,'lastObserved':service.machine.last_observed}
                service.observe(token,obs,status,duration,fps)
                packet=service.poll(control)
                if packet['events']:
                    events.extend({**event,'frame':index,'atMs':now} for event in packet['events'])
                    control['after']=packet['seq']
                packets.append(packet)
                row={'frame':index,'atMs':round(now,3),'inferenceStatus':status,
                     'gate':wrist_gates(obs,service.machine.config),'status':service.machine.status,
                     'armed':service.machine.armed,'expected':service.machine.expected,
                     'heldMs':service.machine.held_ms,'neutralSince':service.machine.neutral_since,
                     'before':before,'detections':state.get('detections',[]),'roi':state.get('roi')}
                if obs:
                    row['observation']=asdict(obs)
                    ps=(obs.left_shoulder,obs.right_shoulder,obs.left_wrist,obs.right_wrist)
                    width=math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y)
                    row['shoulderWidth']=width
                    row['minConfidence']=min(obs.confidence,*(p.confidence for p in ps))
                    row['leftQ']=(ps[0].y-ps[2].y)/width if width else None
                    row['rightQ']=(ps[1].y-ps[3].y)/width if width else None
                rows.append(row)
                del frame
                index+=1
            service.poll(control)
        finally:cap.release();service.close()
    scoring=subprocess.run(['node',str(PROJECT/'scripts/score-motion-fixture.mjs'),'--module',str(PROJECT/'src/motion.js')],
            input=json.dumps({'source':'video','roundId':ROUND,'packets':packets}),text=True,capture_output=True,check=True)
    neutral=intervals(rows,'gate',lambda v:v=='left-down/right-down')
    low=intervals(rows,'gate',lambda v:v=='low-confidence')
    angles=[r['roi']['angle'] for r in rows if r['roi']]
    first_up=next((r for r in rows if 'up' in r['gate']),None)
    bottlenecks=Counter()
    for r in rows:
        if r['gate']=='low-confidence' and 'observation' in r:
            values={k:v['confidence'] for k,v in r['observation'].items() if isinstance(v,dict)}
            values['detectorOrPose']=r['observation']['confidence']
            bottlenecks[min(values,key=values.get)]+=1
    summary={'file':name,'sha256':digest,'fps':fps,'frames':len(rows),'config':asdict(service.machine.config),
             'gateCounts':dict(Counter(r['gate'] for r in rows)),
             'statusCounts':dict(Counter(r['status'] for r in rows)),
             'inferenceStatusCounts':dict(Counter(r['inferenceStatus'] for r in rows)),
             'detectionCounts':dict(Counter(len(r['detections']) for r in rows)),
             'maxFrameGapMs':max((b['atMs']-a['atMs'] for a,b in zip(rows,rows[1:])),default=0),
             'firstFrameMinConfidence':rows[0].get('minConfidence') if rows else None,
             'firstRaisedGate':{k:first_up[k] for k in ('frame','atMs','gate','armed','status')} if first_up else None,
             'lowConfidenceBottleneckCounts':dict(bottlenecks),
             'neutralIntervalsFrames':neutral,'neutralIntervalsMs':[[round(s*1000/fps,3),round(e*1000/fps,3),round((e-s)*1000/fps,3)] for s,e in neutral],
             'lowConfidenceIntervalsFrames':low,
             'armedFrames':sum(r['armed'] for r in rows),'events':events,
             'game':json.loads(scoring.stdout),'roiAngleRange': [min(angles),max(angles)],
             'blockedApiAttempts':api,'captureOpens':opened,'physicalCameraUsed':False,'savedFrames':0,'uploadedFrames':0,
             'naturalSequenceCertified':False,'framesAreDiagnosticsNotHumanAnnotations':True}
    report={'summary':summary,'frames':rows}
    (OUT/(path.stem+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    reports[name]=summary
(OUT/'summary.json').write_text(json.dumps({'runtime':pose.runtime,'implementationSha256':code_hashes,'files':reports},indent=2)+'\n')
print(json.dumps(reports,indent=2))
