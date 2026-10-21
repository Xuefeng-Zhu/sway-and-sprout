#!/usr/bin/env python3
"""Confidence-free conservative geometry from frozen AI visual regions only."""
from pathlib import Path
import hashlib
import itertools
import json
import math

CASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manual_path=CASE/'manual-visual-regions.freeze.json'
assert sha(manual_path)=='0b2e7ef11a479794619f8866f93836965bb9bd7bb3e8bac999fdb6e003ce449c'
manual=json.loads(manual_path.read_text())
GATES=['down','transition','up']

def envelope(handles, frame, offset, rx, ry):
    before=max(row for row in handles if row[0]<=frame)
    after=min(row for row in handles if row[0]>=frame)
    return [min(before[offset],after[offset])-rx,
            min(before[offset+1],after[offset+1])-ry,
            max(before[offset],after[offset])+rx,
            max(before[offset+1],after[offset+1])+ry]

def scale_box(box, sx, sy):
    return None if box is None else [box[0]*sx,box[1]*sy,box[2]*sx,box[3]*sy]

def distance_bounds(a,b):
    dx=max(a[0]-b[2],b[0]-a[2],0)
    dy=max(a[1]-b[3],b[1]-a[3],0)
    lower=math.hypot(dx,dy)
    upper=max(math.hypot(x1-x2,y1-y2) for x1,y1,x2,y2 in itertools.product((a[0],a[2]),(a[1],a[3]),(b[0],b[2]),(b[1],b[3])))
    return lower,upper

def geometry(joints,sx=1.0,sy=1.0):
    boxes={name:scale_box(info['boxXYXY'],sx,sy) for name,info in joints.items()}
    ls,rs=boxes['left_shoulder'],boxes['right_shoulder']
    dlo,dhi=distance_bounds(ls,rs)
    result={'shoulderSpanBoundsPixels':[dlo,dhi],'method':'Conservative interval enclosure: rectangle distance bounds and all numerator/positive-denominator interval endpoints. Correlation is relaxed, so allowed gates may overstate ambiguity; exclusions remain sound.'}
    for side in ('left','right'):
        shoulder,wrist=boxes[side+'_shoulder'],boxes[side+'_wrist']
        if wrist is None or dlo<=0.00001:
            result[side]={'qBounds':None,'allowedGates':GATES,'certifiedGate':None,'reason':'Unknown wrist centre or potentially degenerate shoulder span'}
            continue
        nlo,nhi=shoulder[1]-wrist[3],shoulder[3]-wrist[1]
        vals=[n/d for n in (nlo,nhi) for d in (dlo,dhi)]
        qlo,qhi=min(vals),max(vals)
        allowed=[]
        if qlo < -0.20: allowed.append('down')
        if qlo <= 0.30 and qhi >= -0.20: allowed.append('transition')
        if qhi > 0.30: allowed.append('up')
        assert allowed
        result[side]={'qBounds':[qlo,qhi],'allowedGates':allowed,'certifiedGate':allowed[0] if len(allowed)==1 else None}
    return result

rows=[]
for i in range(188):
    j={}
    for side,offset in [('left',1),('right',3)]:
        j[side+'_shoulder']={'boxXYXY':envelope(manual['manualShoulderHandles'],i,offset,65,75),'visibility':'garment-covered-anatomical-neighborhood-bounded-by-body-contour','reason':'Broad projected shoulder uncertainty under loose satin, not a cloth-seam point.'}
        blurred=28<=i<=64 or 152<=i<=187
        rx,ry=(65,65) if blurred else (45,50)
        box=envelope(manual['manualWristHandles'],i,offset,rx,ry)
        intervals=[v for v in manual['unknownJointIntervals'] if v['joint']==side+'_wrist' and v['sourceStartFrame']<=i<v['sourceEndFrameExclusive']]
        if intervals:
            entry=intervals[0]
            j[side+'_wrist']={'boxXYXY':None,'visibility':'unknown-centre-occluded-cropped-or-unlocalizable','reason':entry['reason'],'contextBoxXYXY':entry.get('contextBoxXYXY',box),'contextIsNotJointGroundTruth':True}
        else:
            j[side+'_wrist']={'boxXYXY':box,'visibility':'partially-visible-cuff-hand-junction-with-blur' if blurred else 'visible-local-cuff-hand-junction','reason':'Conservative source-pixel region around visible connected hand/forearm junction; cuff and motion uncertainty retained. Not a precise point.'}
    rows.append({'frame':i,'sourceFrame':i,'fileTimeMs':i*1000/25,'physicalPersonCount':1,'sameVisibleTargetWithinShot':True,'anatomicalSideCertain':True,'joints':j,'physicalGatesByCoordinateSpace':{'decoded':geometry(j),'sidecarWorking':geometry(j,640/1080,1137/1920)}})

def true_runs(indices):
    if not indices:return []
    runs=[];start=previous=indices[0]
    for value in indices[1:]:
        if value!=previous+1:runs.append((start,previous));start=value
        previous=value
    runs.append((start,previous));return runs

proofs={}
for space in ('decoded','sidecarWorking'):
    possible=[r['frame'] for r in rows if 'up' in r['physicalGatesByCoordinateSpace'][space]['left']['allowedGates'] and 'down' in r['physicalGatesByCoordinateSpace'][space]['right']['allowedGates']]
    runs=[{'startFrame':s,'endFrameInclusive':e,'sampledSpanMs':(e-s)*1000/25,'firstHoldEligibleFrame':next((k for k in range(s,e+1) if int(k*1000/25-s*1000/25)>=350),None)} for s,e in true_runs(possible)]
    impossible=not any(x['firstHoldEligibleFrame'] is not None for x in runs)
    proofs[space]={'possibleExpectedLeftUpOppositeDownRunsWithArmingRelaxed':runs,'maximumPossibleQualifyingSampledSpanMs':max([x['sampledSpanMs'] for x in runs],default=0),'noFirstEventPossible':impossible,'proof':'New round expects left. Relax arming, cooldown and geometric correlations to allow more events, never fewer. Any first event still requires continuous left-up/right-down samples with int(elapsedMs)>=350. The allowed-gate run list is an overapproximation of every physical interpretation. If no listed run reaches350ms, no first event can occur; expected side cannot switch, therefore the whole observed sequence permits no event. Unknown joints are all three gates; they are not forced to down/transition.'}
expected_known=all(p['noFirstEventPossible'] for p in proofs.values())
certified_negative=[{'startFrame':0,'endFrameInclusive':187,'startMs':0.0,'endMs':7480.0,'durationMsByObservedSampleSpan':7480.0,'scope':'State-aware event-negative exposure from new_round expected-left under all permitted visual interpretations, in both declared coordinate spaces. This does not certify every individual joint gate.','proofReference':'physicalReferenceProof'}] if expected_known else []
uncertain_frames=[r['frame'] for r in rows if any(len(r['physicalGatesByCoordinateSpace']['decoded'][s]['allowedGates'])!=1 for s in ('left','right'))]
value={
 'schemaVersion':1,'caseId':'independent-both-stretch',
 'authorType':'AI','authorId':manual['authorId'],'predictionBlind':True,
 'humanConfirmed':False,'humanConfirmationStatus':'not-human-confirmed',
 'labelProvenance':manual['labelProvenance'],
 'contractSha256':manual['contractSha256'],'protocolSha256':manual['protocolSha256'],
 'manualVisualRegionsSha256':sha(manual_path),'derivativeVerificationSha256':sha(CASE/'derivative-verification.freeze.json'),
 'sourceFrameMapSha256':sha(CASE/'source-frame-map.freeze.json'),
 'sourceSha256':manual['sourceSha256'],'derivativeSha256':json.loads((CASE/'derivative-verification.freeze.json').read_text())['derivativeSha256'],
 'frameCount':188,'fpsNumerator':25,'fpsDenominator':1,
 'coordinates':{'decodedDimensions':[1080,1920],'sidecarWorkingDimensions':[640,1137],'decodedToSidecarWorkingTransform':{'scaleX':640/1080,'scaleY':1137/1920,'offsetX':0,'offsetY':0},'nativeRestoredCoordinates':'decoded-source-pixels','warning':'Do not normalize working-image points using decoded dimensions. Geometry for slight integer-resize anisotropy is separately enclosed.'},
 'annotationMethod':manual['method'],
 'inspectionOrderAddendum':'Source full frames25,35,125,170 were additionally viewed by the primary annotator after manual-region freeze but before deriving any gate. They were already separately viewed by the independent reviewer. Remaining full-source frames were viewed before manual freeze. No manual handles changed after freeze; no model output used.',
 'perFrame':rows,'physicalReferenceProof':proofs,
 'opportunities':[],
 'definitePositiveOpportunityCount':0,
 'guaranteedPrecedingNeutral':False,
 'neutralLimitation':'Initial right-wrist centre is occluded/unknown; context is not promoted to a down gate, so preceding neutral is not guaranteed. The no-first-event proof, if established, deliberately relaxes arming and remains valid without guaranteed neutral.',
 'expectedSequence':[] if expected_known else None,'expectationKnown':expected_known,
 'certifiedNegativeIntervals':certified_negative,
 'uncertainPhysicalGateIntervals':[{'startFrame':s,'endFrameInclusive':e,'kind':'one-or-more-joint-gates-not-singleton'} for s,e in true_runs(uncertain_frames)],
 'physicalUnknownTimeIsNotAutomaticallyNegative':True,
 'negativeExposureDistinction':'Only the explicitly proven state-aware no-event interval is certified negative; uncertain joint gates remain separately unknown. If proof fails, expectation stays unknown and certifiedNegativeIntervals is empty.',
 'modelConfidenceUsed':False,'modelRun':False,'cameraUsed':False,
 'limitations':['Preliminary AI visual regions, not human ground truth or accepted localization labels.','No positive recall denominator, no six-alternation or live-camera claim.','Source/creator groups are separate from prior excluded material; physical person identity separation is not established.','Source pixels/cadence remain unchanged; derivative byte identity across ffmpeg versions is not promised.']
}
out=CASE/'ai-visual-annotations.draft.json'
assert not out.exists()
out.write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'annotationSha256':sha(out),'expectationKnown':expected_known,'proofs':proofs},indent=2))
