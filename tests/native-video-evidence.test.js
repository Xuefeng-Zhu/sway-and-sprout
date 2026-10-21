import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeScalarRows,nativeSummaryRows,nativeUiScoreVerified,nativeDiagnosticRoundVerified,nativeCompletionVerified,nativeFrameCoverage,assessNativeCase} from '../scripts/native-video-evidence.mjs';

const config='verification/independent-both-press.float16.json';
const expected={frames:2,fps:30,expectationKnown:false,expectedGestures:[]};
const frames=()=>[0,1].map(frameIndex=>({kind:'pose-frame',configAsset:config,frameIndex,fileMs:frameIndex*1000/30}));
function ui(count=0){return {gardenPresent:true,count,countText:String(count),countLabel:String(count),raySlots:6,collectedRays:count,source:'video',badgeText:'VIDEO REPLAY · NO CAMERA'};}
function row(){return {integrationVerified:true,nativeScalarLog:{available:true},observedGestures:[],ui:ui(),
 lastPacket:{metrics:{fullFileProcessed:true,videoFrames:2,decodedFrames:2,acceptedFrames:2,discardedEpochFrames:0,nativeRecognizedEvents:0,acknowledgedEvents:0}}};}

test('PID-filtered text is further case-filtered and persists primitive scalars only',()=>{
 const value={...frames()[0],lsX:3,armed:true,pixels:[1,2],nested:{private:true}};
 const text=['prefix '+JSON.stringify(value),JSON.stringify({...value,configAsset:'verification/other.json'}),
  JSON.stringify({...value,kind:'preview'}),'not JSON'].join('\n');
 const result=nativeScalarRows(text,config);assert.equal(result.length,1);assert.equal(result[0].lsX,3);
 assert.equal(result[0].armed,true);assert.equal('pixels' in result[0],false);assert.equal('nested' in result[0],false);
});
test('complete trace needs each frozen frame exactly once at deterministic file time',()=>{
 assert.equal(nativeFrameCoverage(frames(),expected).complete,true);
 for(const values of [frames().slice(0,1),[...frames(),frames()[1]],[{...frames()[0],fileMs:1},frames()[1]],
  [frames()[0],{...frames()[1],frameIndex:3}]])assert.equal(nativeFrameCoverage(values,expected).complete,false);
});
test('explicit displayed zero is valid; absent or malformed UI and missing video identity never become zero',()=>{
 assert.equal(nativeUiScoreVerified(ui(0)),true);
 for(const changed of [{gardenPresent:false},{countText:null,count:null},{countText:''},{countLabel:null},
  {countLabel:'1'},{raySlots:0},{collectedRays:1},{source:'waiting'},{badgeText:'LOCAL CAMERA · CONNECTING'}]){
  const value=row();Object.assign(value.ui,changed);assessNativeCase(value,expected,frames());
  assert.equal(value.uiScoringEvidenceVerified,false);assert.equal(value.executionAcceptance,'failed');
 }
});
test('aggregate summaries keep measured primitive fields and reject other configs, kinds and nested diagnostics',()=>{
 const summary={kind:'finished',configAsset:config,fullFileProcessed:true,inferenceMeanMs:8,inferenceP95Ms:10,
  decodeMeanMs:3,preprocessMeanMs:2,frameMeanMs:14,frameP95Ms:18,processPssKiB:120000,
  referenceParityChecks:3,referenceByteDifferences:0,referenceOutputMaxDelta:0.001,referenceMeanMs:1,
  modelInferencesPerFrame:3,poseDiagnostics:{raw:'not persisted'},observedGestures:[],pixels:'not persisted'};
 const rows=nativeSummaryRows([summary,{...summary,kind:'frame-diagnostic'},
  {...summary,configAsset:'verification/other.json'}].map(JSON.stringify).join('\n'),config);
 assert.equal(rows.length,1);assert.equal(rows[0].inferenceP95Ms,10);assert.equal(rows[0].processPssKiB,120000);
 assert.equal(rows[0].modelInferencesPerFrame,3);assert.equal('poseDiagnostics' in rows[0],false);
 assert.equal('observedGestures' in rows[0],false);assert.equal('pixels' in rows[0],false);
});
test('unknown empty sequence remains observed-only, never a certified negative',()=>{
 const value=row();assessNativeCase(value,expected,frames());
 assert.equal(value.executionAcceptance,'passed');assert.equal(value.recognitionAcceptance,'observed-only');assert.equal(value.expectedGestures,null);
});
test('only explicit known empty expectation can pass a complete zero-event case',()=>{
 const value=row();assessNativeCase(value,{...expected,expectationKnown:true},frames());
 assert.equal(value.recognitionAcceptance,'passed');
});
test('unknown or positive partial/censored runs cannot hide as observed-only or ACK success',()=>{
 for(const known of [false,true]){
  const value=row();value.lastPacket.metrics.fullFileProcessed=false;
  value.lastPacket.metrics.acknowledgedEvents=6;value.ui.count=6;
  assessNativeCase(value,{...expected,expectationKnown:known},frames().slice(0,1));
  assert.equal(value.executionAcceptance,'failed');assert.equal(value.recognitionAcceptance,'failed');
 }
});
test('missing scalar capture and lost native events fail execution independently of UI count',()=>{
 const a=row();a.nativeScalarLog.available=false;assessNativeCase(a,expected,frames());assert.equal(a.executionAcceptance,'failed');
 const b=row();assessNativeCase(b,expected,[...frames(),{kind:'event',seq:1,gesture:'left-raise',eventFileMs:20}]);
 assert.equal(b.nativeDeliveryMatches,false);assert.equal(b.executionAcceptance,'failed');
});
test('event timing failure survives matching order, UI rays and ACK',()=>{
 const value=row();value.observedGestures=['left-raise'];value.ui=ui(1);value.lastPacket.metrics.acknowledgedEvents=1;value.lastPacket.metrics.nativeRecognizedEvents=1;
 assessNativeCase(value,{...expected,expectationKnown:true,expectedGestures:['left-raise'],eventWindowsMs:[[25,30]]},
  [...frames(),{kind:'event',seq:1,gesture:'left-raise',eventFileMs:20}]);
 assert.equal(value.executionAcceptance,'passed');assert.equal(value.eventTimingVerified,false);assert.equal(value.recognitionAcceptance,'failed');
});
test('unknown truth still requires native events, front-end rays and ACK to agree',()=>{
 const event={kind:'event',seq:1,gesture:'left-raise',eventFileMs:20};
 for(const field of ['nativeRecognizedEvents','acknowledgedEvents','ui']){
  const value=row();value.observedGestures=['left-raise'];value.ui=ui(1);
  value.lastPacket.metrics.nativeRecognizedEvents=1;value.lastPacket.metrics.acknowledgedEvents=1;
  if(field==='ui')value.ui.count=0;else value.lastPacket.metrics[field]=0;
  assessNativeCase(value,expected,[...frames(),event]);
  assert.equal(value.nativeScoringMatches,false);assert.equal(value.executionAcceptance,'failed');
 }
 const value=row();value.observedGestures=['left-raise'];value.ui=ui(1);
 value.lastPacket.metrics.nativeRecognizedEvents=1;value.lastPacket.metrics.acknowledgedEvents=1;
 assessNativeCase(value,expected,[...frames(),{...event,seq:2}]);assert.equal(value.nativeEventLogValid,false);
});

test('only the explicit diagnostic marker and observed initial120s countdown pass',()=>{
 const valid={roundSecondsText:'120',diagnosticReplayText:'true',timerText:'120s'};
 assert.equal(nativeDiagnosticRoundVerified(valid),true);
 for(const change of [{roundSecondsText:'30'},{diagnosticReplayText:'false'},{timerText:'30s'},{timerText:null}])
  assert.equal(nativeDiagnosticRoundVerified({...valid,...change}),false);
 assert.equal(nativeDiagnosticRoundVerified(null),false);
});

function completion(count=0){return {realTimerElapsed:true,realWallMs:120250,
 path:count===6?'six-ray-auto-celebration':'check-confirmation',realCompleteButtonClicked:count!==6,
 check:{heading:'Replay finished.',rayLabel:`VIDEO REPLAY · NO CAMERA · ${count} OF 6 SIMULATED RAYS`},
 celebration:{screen:'app celebrate camera-mode',heading:'Replay result.',rayLabel:`VIDEO REPLAY · NO CAMERA · ${count} OF 6 SIMULATED RAYS`,replayLabel:true,cameraCalls:0},
 progressUnchangedAtCelebration:true,progressUnchangedAfterReload:true,reload:{screen:'app home',cameraCalls:0},
 inactivePacket:{active:false,metrics:{acknowledgedEvents:count}}};}

test('zero/subsix completion requires the real timer, check confirmation, inactive ACK and unchanged reload',()=>{
 const valid=completion();assert.equal(nativeCompletionVerified(valid,0),true);
 for(const mutate of [c=>c.realWallMs=30000,c=>c.realTimerElapsed=false,c=>c.realCompleteButtonClicked=false,
  c=>c.check.heading='How did that feel?',c=>c.celebration.rayLabel='6 OF 6 SIMULATED RAYS',
  c=>c.inactivePacket.active=true,c=>c.inactivePacket.metrics.acknowledgedEvents=1,c=>c.progressUnchangedAfterReload=false,
  c=>c.reload.cameraCalls=1]){
  const value=structuredClone(valid);mutate(value);assert.equal(nativeCompletionVerified(value,0),false);
 }
 assert.equal(nativeCompletionVerified({},0),false);
});

test('six-ray auto celebration remains a separate valid path and cannot replace zero-ray confirmation',()=>{
 assert.equal(nativeCompletionVerified(completion(6),6),true);
 const value=completion();value.path='six-ray-auto-celebration';assert.equal(nativeCompletionVerified(value,0),false);
});
