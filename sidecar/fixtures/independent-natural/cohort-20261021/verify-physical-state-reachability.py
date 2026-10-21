#!/usr/bin/env python3
"""Confidence-free numerical reference audit. No images, inference or model imports."""
import sys, json, hashlib, importlib.util, math
from pathlib import Path
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
M=Path('/Users/frank/mygit/sway-and-sprout/sidecar/motion.py')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('literal_motion_reference',M)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def recalc(joints):
 def box(name):
  v=joints[name]
  return v.get('box',v.get('boxXYXY')) if isinstance(v,dict) else v
 ls,rs,lw,rw=[box(k) for k in ['LS','RS','LW','RW']]
 if ls is None or rs is None:return (['up','down','transition'],)*2
 dx=max(ls[0]-rs[2],rs[0]-ls[2],0);dy=max(ls[1]-rs[3],rs[1]-ls[3],0)
 d0=math.hypot(dx,dy);d1=max(math.hypot(x-u,y-v) for x in [ls[0],ls[2]] for u in [rs[0],rs[2]] for y in [ls[1],ls[3]] for v in [rs[1],rs[3]])
 def phase(s,w):
  if w is None or d0<=1e-5:return ['up','down','transition']
  q=[n/d for n in [s[1]-w[3],s[3]-w[1]] for d in [d0,d1]];lo,hi=min(q),max(q);a=[]
  if hi>.3:a.append('up')
  if lo<-.2:a.append('down')
  if hi>=-.2 and lo<=.3:a.append('transition')
  return a
 return phase(ls,lw),phase(rs,rw)

def verify(case,filename,space=None):
 f=P/'cases'/case/filename;a=json.loads(f.read_text());fps=a['fpsNumerator']/a['fpsDenominator']
 rows=a['perFrame'];states={('left',False,None,None,-math.inf):(0,0)};timeline=[];checks=0;geochecks=0
 for i,row in enumerate(rows):
  if case=='both-press':
   assert row['clipFrame']==i
   l,r=row['leftAllowed'],row['rightAllowed'];rl,rr=recalc(row['jointRegions'])
   assert set(l)==set(rl) and set(r)==set(rr),(i,l,r,rl,rr)
   geochecks+=1
  else:
   assert row['frame']==i
   gates=row['physicalGatesByCoordinateSpace'][space];l=gates['left']['allowedGates'];r=gates['right']['allowedGates']
   if space=='decoded':
    j=row['joints'];rl,rr=recalc({'LS':j['left_shoulder'],'RS':j['right_shoulder'],'LW':j['left_wrist'],'RW':j['right_wrist']})
    assert set(l)==set(rl) and set(r)==set(rr),(i,l,r,rl,rr)
    geochecks+=1
  nxt={};emits=set()
  for state,counts in states.items():
   for lg in l:
    for rg in r:
     g=m.GestureMachine();g.expected,g.armed,g.neutral_since,g.hold_since,g.last_emitted=state;g.last_observed=None if i==0 else (i-1)*1000/fps
     ys={'up':-1.,'down':1.,'transition':0.}
     o=m.Observation(m.Landmark(0,0),m.Landmark(1,0),m.Landmark(0,ys[lg]),m.Landmark(1,ys[rg]))
     e=g.update(o,i*1000/fps);checks+=1
     s=(g.expected,g.armed,g.neutral_since,g.hold_since,g.last_emitted)
     if e:emits.add(e['gesture'])
     c=(counts[0]+int(bool(e)),counts[1]+int(bool(e)))
     if s in nxt:nxt[s]=(min(nxt[s][0],c[0]),max(nxt[s][1],c[1]))
     else:nxt[s]=c
  states=nxt
  timeline.append({'frame':i,'timeMs':i*1000/fps,'leftAllowed':l,'rightAllowed':r,'reachableStateCount':len(states),'reachableArmed':sorted({s[1] for s in states}),'neutralSinceFrames':sorted({round(s[2]*fps/1000) for s in states if s[2] is not None}),'holdSinceFrames':sorted({round(s[3]*fps/1000) for s in states if s[3] is not None}),'maximumHeldMs':max([int(i*1000/fps-s[3]) for s in states if s[3] is not None]+[0]),'possibleEmittedGestures':sorted(emits),'eventCountOuterBounds':[min(v[0] for v in states.values()),max(v[1] for v in states.values())]})
 bounds=[min(v[0] for v in states.values()),max(v[1] for v in states.values())]
 out={'schemaVersion':1,'caseId':case,'coordinateSpace':space or 'decoded','analysisType':'independent conservative allowed-gate reachability using literal current GestureMachine.update','annotationPath':str(f),'annotationSha256':sha(f),'jointRegionFreezeSha256':a.get('jointRegionFreezeSha256',a.get('manualVisualRegionsSha256')),'sourceSha256':a['sourceSha256'],'derivativeSha256':a.get('clipSha256',a.get('derivativeSha256')),'contractSha256':a['contractSha256'],'protocolSha256':a['protocolSha256'],'motionPath':str(M),'motionSha256':sha(M),'analysisScriptSha256':sha(Path(__file__)),'fpsNumerator':a['fpsNumerator'],'fpsDenominator':a['fpsDenominator'],'frameCount':len(rows),'timestampFormula':'i*1000/(fpsNumerator/fpsDenominator), exact float operations used by literal machine','initialExpected':'left','classifierConfiguration':vars(m.Config()),'confidenceGateAppliedToLabels':False,'phaseRepresentativeConfidence':1.0,'syntheticArithmeticOnly':True,'notVideoOrModelInference':True,'actualLiteralTransitionsChecked':checks,'independentlyRecomputedGeometryRows':geochecks,'eventCountOuterBounds':bounds,'zeroEventsProvenWithinAnnotatedGateSuperset':bounds==[0,0],'expectedSequenceDerived':[] if bounds==[0,0] else None,'regionOrAnnotationChanged':False,'notHumanConfirmedAcceptance':True,'scope':'Conditional on original AI visual regions and frozen deterministic full-frame clock; Cartesian-product phase relaxation can add possibilities, never exclude a region-consistent configuration. Zero under this superset proves zero within those annotations; does not validate region accuracy, actual model scores, camera or UI.','perFrame':timeline}
 suffix='' if space in (None,'decoded') else '-'+space
 dest=P/'cases'/case/('derived-zero-proof'+suffix+'.json');dest.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'case':case,'space':space,'eventCountOuterBounds':bounds,'transitionsChecked':checks,'geometryRows':geochecks,'proofFile':str(dest),'proofSha256':sha(dest),'selectedFrames':[timeline[i] for i in ([84,85,91,92,101,102,103,104,105,110,156,166] if case=='both-press' else [])]},indent=2))
 return out
if __name__=='__main__':
 verify('both-press','annotations.proposal.json')
 verify('both-stretch','ai-visual-annotations.freeze.json','decoded')
 verify('both-stretch','ai-visual-annotations.freeze.json','sidecarWorking')
