#!/usr/bin/env python3
"""Pure interval/state arithmetic for frozen AI visual regions; never imports a model."""
import json, math, hashlib
from pathlib import Path
from datetime import datetime, timezone
P=Path(__file__).resolve().parent
B=P.parent.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
# [xmin,xmax,ymin,ymax], decoded unmirrored 1920x1080 pixels.
# Envelopes cover every inspected frame in their interval; null remains unknown.
segments=[
 (0,5, [1300,1450,330,450],None,[750,900,480,620],[990,1110,300,460], 'First crossed pose: left wrist visible with watch; opposite shoulder hidden by arms. No point imputed for hidden shoulder.'),
 (5,16,[1340,1490,350,520],[990,1160,370,560],None,None,'Release and arm crossing; motion blur/partial occlusion prevents bounded wrist centres. Unknown, not neutral certification.'),
 (16,32,[1370,1520,370,530],[990,1160,380,550],None,None,'Wrists approach or pass the lower crop during downward swing. No offscreen coordinates invented.'),
 (32,44,[1370,1510,365,520],[1000,1150,370,530],[1450,1860,700,950],[850,1040,810,1065],'Both wrists visibly well below shoulders, including all frames in this interval.'),
 (44,51,[1360,1500,370,520],[1000,1150,370,530],None,[830,1050,820,1065],'Left wrist partly behind torso; right wrist remains visibly low. Left remains unknown.'),
 (51,56,[1350,1470,370,520],[970,1140,380,535],[1460,1650,780,970],[720,1010,900,1070],'Both wrist centres visible and low; broad regions include moving watch wrist.'),
 (56,72,[1330,1480,370,540],[970,1150,360,550],None,None,'Wrists again near lower crop/blurred while arms start moving. Do not infer a continuous neutral span across this interval.'),
 (72,81,[1320,1480,370,540],[980,1150,350,530],[1190,1530,650,1080],[1020,1730,550,1080],'Rising arm exchange: both wrist centres remain below own shoulder; broad bounds allow down or transition, never up.'),
 (81,90,[1340,1480,395,515],[1000,1140,365,485],[1170,1370,340,800],[1570,1760,425,650],'Left wrist bends upward rapidly while right arm extends across chest. Left onset and opposite-down cutoff uncertain.'),
 (90,120,[1300,1460,395,515],[1000,1150,345,480],[1260,1410,260,400],[1600,1760,410,540],'Bent left wrist high, opposite straight wrist near the down cutoff. Left shoulder partly visible/obscured; deliberately broad region, no exact point claim.'),
 (120,150,[1240,1400,350,510],[940,1120,320,450],[1190,1380,190,340],[1550,1740,250,490],'Crossed pose moves upward. Broad shoulder/wrist bounds do not establish continuous opposite-down or a definite left-up onset.'),
 (150,180,[1220,1400,350,510],[930,1100,330,450],[1180,1340,190,300],[1530,1730,190,340],'Stable high crossed pose: both wrist regions exclude down relative to own shoulder over all bounded configurations.'),
 (180,195,[1200,1380,350,520],[920,1080,350,460],[1150,1320,230,335],[1510,1730,280,420],'Straight wrist settles toward shoulder height; bent left wrist excludes down. Right down/transition uncertainty retained.'),
]
def distance_bounds(a,b):
 if a is None or b is None:
  return (1e-5,math.hypot(1920,1080))
 dx=max(a[0]-b[1],b[0]-a[1],0);dy=max(a[2]-b[3],b[2]-a[3],0)
 lo=math.hypot(dx,dy)
 hi=max(math.hypot(x-u,y-v) for x in a[:2] for u in b[:2] for y in a[2:] for v in b[2:])
 return max(lo,1e-5),hi

def ratio_and_phases(s,w,d):
 if s is None or w is None:return None,['up','down','transition']
 n=(s[2]-w[3],s[3]-w[2]);q=[v/z for v in n for z in d];lo,hi=min(q),max(q)
 out=[]
 if hi>.30:out.append('up')
 if lo<-.20:out.append('down')
 if hi>=-.20 and lo<=.30:out.append('transition')
 return [lo,hi],out

# Pure phase-state implementation of current motion.py. Frame timestamps are
# unrounded float i*1000/30. Unknown regions branch to every admissible gate;
# the Cartesian product is a conservative outer approximation, not a claim
# each extreme jointly occurs in the filmed person.
# State=(expected,armed,neutral_since_frame,hold_since_frame,last_emit_frame)
def step(s,i,l,r):
 expected,armed,neutral,hold,last=s;t=i*1000/30
 if l=='down' and r=='down':
  neutral=i if neutral is None else neutral
  if t-neutral*1000/30>=300:armed=True
  return (expected,armed,neutral,None,last),False
 neutral=None
 correct=(l=='up' and r=='down') if expected=='left' else (r=='up' and l=='down')
 if not correct:
  transition=(l=='transition' and r=='down') if expected=='left' else (r=='transition' and l=='down')
  if not transition:armed=False
  return (expected,armed,None,None,last),False
 if not armed or (last is not None and t-last*1000/30<500):return (expected,armed,None,None,last),False
 hold=i if hold is None else hold
 if int(t-hold*1000/30)<350:return (expected,armed,None,hold,last),False
 return ('right' if expected=='left' else 'left',False,None,None,i),True

def run():
 rows=[];segrows=[]
 for k,(start,end,ls,rs,lw,rw,note) in enumerate(segments):
  d=distance_bounds(ls,rs);ql,l=ratio_and_phases(ls,lw,d);qr,r=ratio_and_phases(rs,rw,d)
  joint=dict(zip(('left_shoulder','right_shoulder','left_wrist','right_wrist'),(ls,rs,lw,rw)))
  segrows.append({'segmentId':f'visual-{k:02}','startFrame':start,'endFrameExclusive':end,'jointRegions':joint,'shoulderSpanOuterBounds':list(d),'leftQOuterBounds':ql,'rightQOuterBounds':qr,'allowedGates':{'left':l,'right':r},'unknownJointNames':[key for key,value in joint.items() if value is None],'reason':note,'everyFrameVisuallyInspected':True})
  for i in range(start,end):rows.append({'frame':i,'sourceFrame':150+i,'timeMs':i*1000/30,'regionSegmentId':f'visual-{k:02}','allowedGates':{'left':l,'right':r},'jointVisibilityUncertain':any(v is None for v in joint.values()),'physicalPersonCount':1,'anatomicalSides':'continuous-shot limb tracing; left watch wrist; no identity claim'})
 assert [r['frame'] for r in rows]==list(range(195))
 # value stores attainable min/max event count within this phase outer model.
 states={('left',False,None,None,None):(0,0)}; timeline=[]
 for row in rows:
  new={};emission_sides=set()
  for state,(count_min,count_max) in states.items():
   for l in row['allowedGates']['left']:
    for r in row['allowedGates']['right']:
     ns,emit=step(state,row['frame'],l,r)
     if emit:emission_sides.add(state[0])
     bounds=(count_min+int(emit),count_max+int(emit))
     if ns in new:new[ns]=(min(new[ns][0],bounds[0]),max(new[ns][1],bounds[1]))
     else:new[ns]=bounds
  states=new
  timeline.append({'frame':row['frame'],'sourceFrame':row['sourceFrame'],'timeMs':row['timeMs'],'stateCount':len(states),'eventCountOuterBounds':[min(v[0] for v in states.values()),max(v[1] for v in states.values())],'emissionSidesNotExcludedByOuterBounds':sorted(emission_sides)})
 negative=[]
 for a,b,why in [(32,44,'both down'),(51,56,'both down'),(72,81,'neither wrist can be up'),(150,180,'neither wrist can be down')]:
  assert all(not timeline[i]['emissionSidesNotExcludedByOuterBounds'] for i in range(a,b))
  negative.append({'startFrame':a,'endFrameExclusive':b,'sampleSupportStartMs':a*1000/30,'sampleSupportEndExclusiveMs':b*1000/30,'sampleCount':b-a,'exposureMs':(b-a)*1000/30,'basis':why,'unknownJointFramesIncluded':0,'meaning':'No valid expected-side raise at these observed samples under any annotated joint configuration; coverage uses [t_i,t_i+1) sample bins, not a subframe continuous-motion claim.'})
 annotation={'schemaVersion':1,'status':'candidate-bound-analysis-before-freeze','caseId':'cross-stretch','sourceGroupId':'Pexels/RDNE Stock project/8401267','authorType':'AI','authorId':'Codex /root/native_resume_review','predictionBlind':True,'humanConfirmed':False,'humanConfirmationStatus':'not-human-confirmed','labelProvenance':'AI visual annotations of public footage, authored after contract freeze and before this cohort model inference; not human-, user-supplied or user-approved labels.','preliminaryDiagnosticOnly':True,'contractSha256':sha(B/'EVALUATION-CONTRACT.freeze.md'),'protocolSha256':sha(B/'PROTOCOL.freeze.json'),'sourceSha256':sha(B/'discovery/pexels-8401267/source.mp4'),'selectionSha256':sha(P/'selection-before-annotation.json'),'derivativeSha256':sha(P/'cross-stretch.mp4'),'coordinateSystem':'decoded source unmirrored 1920x1080 pixels, top-left origin, anatomical left/right','jointRegionFormat':'[xmin,xmax,ymin,ymax] inclusive axis-aligned plausible visual region; null explicitly unknown','regionScope':'shared conservative envelope for every inspected frame in each segment, not a predicted trajectory or exact point ground truth','method':{'all195FramesInspected':True,'contactSheets':['review-contact-sheets/'+p.name for p in sorted((P/'review-contact-sheets').glob('*.jpg'))],'fullResolutionGridFrames':[0,10,20,30,40,55,65,75,85,90,100,110,120,130,140,150,160,170,180,190,194],'fullResolutionAdditionalFrames':[0,40,90,130],'contactSheetRender':'640x360 image tiles; tool display downsized whole sheets; full-resolution arm/shoulder crops checked at listed frames','noModelOrConfidenceUsed':True,'limitation':'One AI reviewer, projected joints partly occluded, no calibrated annotation-error guarantee. Shared regions intentionally broad. All region-based guarantees are conditional on these independently chosen visual envelopes; human confirmation absent. Unknown/cropped wrists remain null rather than inferred coordinates.'},'segments':segrows,'perFrame':rows,'definiteOpportunities':[],'definitePositiveOpportunityCount':0,'positiveDenominatorStatus':'unestimable; this case supplies no certified positive, not evidence there is physically no qualifying gesture','expectedSequence':None,'certifiedNegativeIntervals':negative,'certifiedNegativeSampleCount':sum(x['sampleCount'] for x in negative),'certifiedNegativeExposureMs':sum(x['exposureMs'] for x in negative),'uncertainIntervals':[{'startFrame':a,'endFrameExclusive':b,'reason':why} for a,b,why in [(0,32,'Initial crossed pose/release/cropped wrists: incomplete joints and uncertain gates; not certified negative exposure.'),(44,51,'Left wrist occluded.'),(56,72,'Wrists cropped or blurred; continuous neutral not certified.'),(81,150,'A left-up/right-down hold is not excluded. Onset, opposite-down support, and resulting expected-side state are not definite.'),(180,195,'Right-wrist gate near cutoff. Outer-state analysis can exclude a new event after the preceding no-neutral/no-down span, but this is omitted from the minimal physical-negative exposure.')]],'possibleLeftCorrectRunOuterBounds':{'startFrame':81,'endFrameExclusive':150,'meaning':'Envelope permits left-up/right-down at some/all samples; not a demonstrated filmed continuous run, definite opportunity, or an event acceptance window. No exact onset or positive count is invented.'},'wholeClipGuaranteedZeroExpected':False,'pointAccuracyGroundTruth':False,'cameraUsed':False,'modelInferencePerformed':False}
 out={'schemaVersion':1,'caseId':'cross-stretch','analysisType':'conservative interval geometry and exact phase-state outer-bound enumeration, no model inference','algorithmSha256':sha(Path(__file__)),'sourceMotionPath':'/Users/frank/mygit/sway-and-sprout/sidecar/motion.py','sourceMotionSha256':sha('/Users/frank/mygit/sway-and-sprout/sidecar/motion.py'),'frameCount':195,'timestamps':'i*1000/30 float, no rounding; int hold truncation','confidenceGateApplied':False,'allPlausibleRegionConfigurationsCovered':True,'outerApproximationNotAttainabilityProof':True,'noExactPossibleEligibilityClaim':True,'guaranteedEventCount':None,'eventCountOuterBounds':[min(v[0] for v in states.values()),max(v[1] for v in states.values())],'definitePositiveOpportunityCount':0,'perFrame':timeline,'regionCalculations':segrows,'minimalNegativeIntervals':negative,'negativeExposureMs':annotation['certifiedNegativeExposureMs'],'warnings':['Cartesian-product phase branches may include geometrically dependent or visually implausible combinations, so possible-emission bounds do not prove physical events.','Unknown wrist/shoulder observations branch conservatively; they are excluded from negative exposure.','No exact physical onset, timed positive acceptance, probability calibration, or point-accuracy claim.']}
 (P/'ai-visual-annotations.candidate.json').write_text(json.dumps(annotation,indent=2)+'\n')
 (P/'bound-analysis.candidate.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'statesAtEnd':len(states),'eventCountOuterBounds':out['eventCountOuterBounds'],'negativeSampleCount':annotation['certifiedNegativeSampleCount'],'negativeExposureMs':annotation['certifiedNegativeExposureMs'],'segments':[{'frames':[s['startFrame'],s['endFrameExclusive']],'gates':s['allowedGates'],'qL':s['leftQOuterBounds'],'qR':s['rightQOuterBounds']} for s in segrows]},indent=2))
if __name__=='__main__':run()
