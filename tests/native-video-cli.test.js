// Mock child processes only: no emulator, browser, SDK, model, or camera.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
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
 fs.writeFileSync(path.join(root,'node_modules/@playwright/test/index.js'),
  "export const chromium={connectOverCDP:async()=>({contexts:()=>[{pages:()=>[{on(){},waitForSelector:async()=>{throw Error('injected UI failure')}}]}],close:async()=>{}})};");
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
 for(const frameIndex of [0,1])console.log(JSON.stringify({kind:'pose-frame',configAsset:'verification/independent-both-press.float16.json',frameIndex,fileMs:frameIndex*1000/30,lsX:10,pixels:'must-not-persist'}));
 console.log(JSON.stringify({kind:'stopped',configAsset:'verification/independent-both-press.float16.json',inferenceMeanMs:8,inferenceP95Ms:10,frameMeanMs:14,frameP95Ms:18,processPssKiB:120000,poseDiagnostics:{raw:'must-not-persist'}}));
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
test('per-case failure still saves PID-filtered primitive diagnostic rows and fails execution',()=>{
 const f=fixture();try{
  const result=f.run('allow',['independent-both-press']);assert.equal(result.status,1);
  assert.match(result.stderr,/injected UI failure/);
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
