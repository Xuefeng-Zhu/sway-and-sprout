// Mock child processes only: no emulator, browser, SDK, model, or camera.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const source=fileURLToPath(new URL('../scripts/',import.meta.url));
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'sway-native-cli-mock-'));
 fs.mkdirSync(path.join(root,'scripts'));fs.mkdirSync(path.join(root,'android'));
 for(const name of ['native-emulator-options.mjs','native-video-evidence.mjs','verify-native-video.mjs'])
  fs.copyFileSync(path.join(source,name),path.join(root,'scripts',name));
 fs.mkdirSync(path.join(root,'node_modules/@playwright/test'),{recursive:true});
 fs.writeFileSync(path.join(root,'node_modules/@playwright/test/package.json'),JSON.stringify({type:'module',exports:'./index.js'}));
 fs.writeFileSync(path.join(root,'node_modules/@playwright/test/index.js'),String.raw`
const storage='{"completed":[],"sessions":0}';let home=false;
const packet={runtime:{engine:'litert',verified:true,modelSha256:'0'.repeat(64),modelId:'float16',inputSize:192},
 source:'video',status:'tracking',seq:0,active:true,revision:1,events:[],
 metrics:{fullFileProcessed:true,videoFrames:2,decodedFrames:3,acceptedFrames:2,discardedEpochFrames:1,
 nativeRecognizedEvents:0,acknowledgedEvents:0,modelInferencesPerFrame:3,statelessCropRefinement:true}};
function state(){return {gardenPresent:true,countText:'0',count:0,countLabel:'0',raySlots:6,collectedRays:0,
 source:'video',badgeText:'VIDEO REPLAY · NO CAMERA',screen:home?'app home':'app play camera-mode',
 heading:'Mock-only native UI',rayLabel:'',roundSecondsText:'120',diagnosticReplayText:'true',timerText:'120s',
 roundStart:{roundSecondsText:'120',diagnosticReplayText:'true',timerText:'120s'},
 body:'VIDEO REPLAY',packets:[packet],cameraCalls:0,storage};}
const page={on(){},addInitScript:async()=>{},waitForFunction:async()=>{},
 waitForSelector:async()=>{if(process.env.SWAY_MOCK_MODE!=='evidence')throw Error('injected UI failure');},
 evaluate:async fn=>{
  if(fn.name==='readUiState')return state();
  if(fn.name==='installObservation')return;
  if(fn.toString().includes('localStorage.getItem'))return storage;
  if(fn.toString().includes('__nativeObserved'))return packet;
  throw Error('Unexpected mock evaluation');
 },
 locator:selector=>{const item={first:()=>item,click:async()=>{
  if(selector.includes('"home"')){home=true;packet.active=false;}
 }};return item;}};
export const chromium={connectOverCDP:async()=>({contexts:()=>[{pages:()=>[page]}],close:async()=>{}})};
`);
 fs.writeFileSync(path.join(root,'android/native-video-assets.lock.json'),JSON.stringify({
  artifacts:[{role:'candidate-model',modelId:'float16',sha256:'0'.repeat(64),bytes:4758512,input:{shape:[1,192,192,3]}}],
  fixtures:[{case:'independent-both-press',frames:2,fps:30,expectationKnown:false,expectedGestures:[]}]}));
 const adb=path.join(root,'fake-adb.mjs'),log=path.join(root,'adb-arguments.jsonl');
 fs.writeFileSync(adb,`#!/usr/bin/env node
import fs from 'node:fs';
const a=process.argv.slice(2);fs.appendFileSync(process.env.SWAY_MOCK_ADB_LOG,JSON.stringify(a)+'\\n');
if(a.includes('ro.kernel.qemu'))console.log(process.env.SWAY_MOCK_MODE==='reject'?'0':'1');
else if(a.includes('sys.boot_completed'))console.log('1');
else if(a.includes('ro.build.version.sdk'))console.log('34');
else if(a.includes('ro.product.cpu.abi'))console.log('arm64-v8a');
else if(a.includes('ro.product.model'))console.log('mock-only');
else if(a.includes('pidof'))console.log('123');
else if(a.includes('logcat')){
 if(process.env.SWAY_MOCK_MODE==='logfail'){console.error('injected log capture failure');process.exit(2);}
 for(const [offset,phase] of ['decode-discard','accepted','accepted'].entries())console.log(JSON.stringify({
  kind:'frame-attempt',source:'video',configAsset:'verification/independent-both-press.float16.json',
  modelSha256:'0'.repeat(64),attemptId:offset+1,roundId:'mock-round',frameIndex:Math.max(0,offset-1),
  attemptEpoch:offset?2:1,controlEpoch:2,phase,discardReason:offset?0:1,
  inferenceStarted:offset>0,totalWallMs:offset?30:150,decodeWallMs:10,totalWorkerCpuMs:5,
  cpuScope:'worker-thread-and-app-process',pixels:'must-not-persist'}));
 console.log(JSON.stringify({kind:'frame-attempt',configAsset:'verification/other.float16.json',attemptId:99}));
 for(const frameIndex of [0,1])console.log(JSON.stringify({kind:'pose-frame',configAsset:'verification/independent-both-press.float16.json',frameIndex,fileMs:frameIndex*1000/30,lsX:10,pixels:'must-not-persist'}));
 console.log(JSON.stringify({kind:'stopped',configAsset:'verification/independent-both-press.float16.json',fullFileProcessed:true,resourcesClosed:true,cleanupSucceeded:true,verified:false,inferenceMeanMs:8,inferenceP95Ms:10,frameMeanMs:14,frameP95Ms:18,processPssKiB:120000,poseDiagnostics:{raw:'must-not-persist'}}));
}
`,{mode:0o755});
 return {root,adb,log,run(mode,args=[]){return spawnSync(process.execPath,
  [path.join(root,'scripts/verify-native-video.mjs'),'--adb',adb,'--model','float16','--out',path.join(root,'out'),...args],
  {encoding:'utf8',timeout:10000,env:{...process.env,SWAY_MOCK_ADB_LOG:log,SWAY_MOCK_MODE:mode}});},
 commands(){return fs.existsSync(log)?fs.readFileSync(log,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];},
 cleanup(){fs.rmSync(root,{recursive:true,force:true});}};
}

test('unknown CLI cases/options reject before any ADB process',()=>{
 for(const args of [['not-frozen'],['--model','unfrozen'],['--serial','physical-device','independent-both-press']]){
  const f=fixture();try{const result=f.run('reject',args);assert.notEqual(result.status,0);assert.deepEqual(f.commands(),[]);}finally{f.cleanup();}
 }
});
test('non-emulator guard performs only its read-only probe, no app mutation',()=>{
 const f=fixture();try{
  const result=f.run('reject',['independent-both-press']);assert.equal(result.status,1);
  const commands=f.commands();assert.equal(commands.length,1);assert.deepEqual(commands[0].slice(-3),['shell','getprop','ro.kernel.qemu']);
  assert.match(result.stderr,/Target is not a verified emulator/);
 }finally{f.cleanup();}
});
test('nonempty output is preserved and rejected before any ADB process',()=>{
 const f=fixture();try{
  const output=path.join(f.root,'out');fs.mkdirSync(output);fs.writeFileSync(path.join(output,'prior.json'),'preserve prior result');
  const result=f.run('allow',['independent-both-press']);assert.notEqual(result.status,0);
  assert.match(result.stderr,/Refusing nonempty verification output/);assert.deepEqual(f.commands(),[]);
  assert.equal(fs.readFileSync(path.join(output,'prior.json'),'utf8'),'preserve prior result');
 }finally{f.cleanup();}
});
test('per-case failure still saves PID-filtered primitive diagnostic rows and fails execution',()=>{
 const f=fixture();try{
  const result=f.run('allow',['independent-both-press']);assert.equal(result.status,1);
  const commands=f.commands(),capture=commands.find(a=>a.includes('logcat'));
  assert.ok(capture.includes('--pid=123'));assert.ok(capture.includes('SwayNativeVideo:I'));
  const output=path.join(f.root,'out'),trace=fs.readFileSync(path.join(output,'independent-both-press.native-scalar.jsonl'),'utf8');
  assert.equal(trace.trim().split('\n').length,2);assert.equal(trace.includes('must-not-persist'),false);
  const row=JSON.parse(fs.readFileSync(path.join(output,'independent-both-press.json')));
  assert.equal(row.nativeScalarLog.available,true);assert.equal(row.executionAcceptance,'failed');
  assert.equal(row.recognitionAcceptance,'failed');assert.equal(row.expectedGestures,null);
  assert.equal(row.harnessError.message,'injected UI failure');assert.ok(row.caseWallMs>=0);
  const summaries=fs.readFileSync(path.join(output,'independent-both-press.native-summary.jsonl'),'utf8');
  assert.equal(summaries.trim().split('\n').length,1);assert.equal(summaries.includes('must-not-persist'),false);
  assert.equal(row.nativeSummaryLog.available,true);assert.equal(row.nativePerformanceSummary.inferenceMeanMs,8);
 }finally{f.cleanup();}
});

test('EOF and final attempt artifacts retain discards separately from accepted pose coverage',()=>{
 const f=fixture();try{
  const result=f.run('evidence',['independent-both-press']);assert.equal(result.status,1);
  const output=path.join(f.root,'out'),row=JSON.parse(fs.readFileSync(path.join(output,'independent-both-press.json')));
  const paths=[];
  for(const [key,phase,suffix] of [['eofNativeAttemptLog','eof','.eof'],['nativeAttemptLog','final','']]){
   const log=row[key],expectedPath=path.join(output,'independent-both-press'+suffix+'.native-attempt.jsonl');
   assert.equal(log.available,true);assert.equal(log.rows,3);assert.equal(log.phase,phase);
   assert.equal(log.path,expectedPath);assert.equal(log.pid,'123');
   assert.equal(log.configAsset,'verification/independent-both-press.float16.json');
   const body=fs.readFileSync(log.path,'utf8'),attempts=body.trim().split('\n').map(JSON.parse);
   assert.equal(log.sha256,crypto.createHash('sha256').update(body).digest('hex'));
   assert.deepEqual(attempts.map(item=>item.phase),['decode-discard','accepted','accepted']);
   assert.deepEqual(attempts.map(item=>item.frameIndex),[0,0,1]);
   assert.equal(attempts[0].inferenceStarted,false);assert.equal(attempts[0].totalWallMs,150);
   assert.equal(body.includes('must-not-persist'),false);assert.equal(body.includes('"attemptId":99'),false);
   paths.push(log.path);
  }
  assert.notEqual(paths[0],paths[1]);
  assert.equal(row.nativeScalarLog.rows,2);assert.equal(row.eofNativeScalarLog.rows,2);
  assert.equal(row.nativePoseFrameCoverage.loggedFrames,2);assert.equal(row.nativePoseFrameCoverage.uniqueFrames,2);
  assert.equal(row.nativePoseFrameCoverage.complete,true);
  assert.equal(row.completeFileVerified,false,'Discard evidence must not be promoted to complete accepted processing');
  assert.equal(row.executionAcceptance,'failed');
  assert.equal(row.nativeClosedSummary.resourcesClosed,true);
  const scalarBody=fs.readFileSync(row.nativeScalarLog.path,'utf8');
  assert.equal(scalarBody.includes('frame-attempt'),false);
 }finally{f.cleanup();}
});

test('failed log capture leaves a hashed empty unavailable attempt artifact',()=>{
 const f=fixture();try{
  const result=f.run('logfail',['independent-both-press']);assert.equal(result.status,1);
  const output=path.join(f.root,'out'),row=JSON.parse(fs.readFileSync(path.join(output,'independent-both-press.json')));
  const log=row.nativeAttemptLog;
  assert.equal(log.available,false);assert.equal(log.rows,0);assert.equal(log.phase,'final');assert.equal(log.pid,'123');
  assert.equal(log.configAsset,'verification/independent-both-press.float16.json');
  assert.equal(log.path,path.join(output,'independent-both-press.native-attempt.jsonl'));
  assert.equal(fs.readFileSync(log.path,'utf8'),'');
  assert.equal(log.sha256,crypto.createHash('sha256').update('').digest('hex'));
  assert.match(log.error,/injected log capture failure/);
  assert.equal(row.executionAcceptance,'failed');
 }finally{f.cleanup();}
});
