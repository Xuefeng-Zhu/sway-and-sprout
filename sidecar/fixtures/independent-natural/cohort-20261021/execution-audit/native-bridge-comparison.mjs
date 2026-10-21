// Supplemental existing-native bridge comparison. No game UI, score or timer is exercised.
// Run only inside the parent's existing OS network sandbox and one camera-disabled emulator.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';

const E=path.dirname(fileURLToPath(import.meta.url));
const R='/Users/frank/mygit/sway-and-sprout';
const PLAN_SHA='fb84346ad034457d469ff7963f54ec3e518be2675f39ac7aedfbf37cf389f73b';
const cohort=['independent-both-press','independent-both-stretch','independent-cross-stretch'];
const sha=value=>crypto.createHash('sha256').update(value??'<absent>').digest('hex');
const fileSha=file=>sha(fs.readFileSync(file));
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const requestedOut=process.argv[process.argv.indexOf('--out')+1];
if(!process.argv.includes('--out')||!requestedOut||!path.isAbsolute(requestedOut)||
 !path.resolve(requestedOut).startsWith(E+path.sep)||fs.existsSync(requestedOut))
 throw Error('Require a new absolute --out directory inside the evaluation workspace');
const outputParent=fs.realpathSync(path.dirname(requestedOut));
if(outputParent!==fs.realpathSync(E)&&!outputParent.startsWith(fs.realpathSync(E)+path.sep))throw Error('Output parent escapes real evaluation workspace');
const {nativeOptions}=await import(pathToFileURL(R+'/scripts/native-emulator-options.mjs'));
const {nativeScalarRows,nativeSummaryRows,nativeFrameCoverage}=await import(pathToFileURL(R+'/scripts/native-video-evidence.mjs'));
const {createMotionClient}=await import(pathToFileURL(R+'/src/motion.js'));
const {chromium}=createRequire(R+'/package.json')('@playwright/test');
const options=nativeOptions(),{adb,out,cases}=options;
if(options.model!=='float16'||options.refinement!=='image'||options.completion||
 JSON.stringify(cases)!==JSON.stringify(cohort))throw Error('Require the frozen FP16/image profile and all three cohort cases in frozen order');
const planFile=E+'/execution-plan.freeze.json';
if(fileSha(planFile)!==PLAN_SHA)throw Error('Frozen cohort digest mismatch');
const plan=JSON.parse(fs.readFileSync(planFile,'utf8'));
for(const pin of plan.sourcePins)if(fileSha(R+'/'+pin.path)!==pin.sha256)throw Error('Frozen semantic source changed: '+pin.path);
const lock=JSON.parse(fs.readFileSync(R+'/android/native-video-assets.lock.json','utf8'));
const selected=lock.artifacts.find(item=>item.role==='candidate-model'&&item.modelId==='float16');
if(!selected)throw Error('Frozen native model unavailable');
for(const name of cohort){
 const frozen=plan.cases.find(item=>item.caseId===name),fixture=lock.fixtures.find(item=>item.case===name);
 if(!fixture||!frozen||fixture.sha256!==frozen.sha256||fixture.bytes!==frozen.bytes||
  fixture.frames!==frozen.frames||fixture.fps!==frozen.fps||fixture.expectationKnown!==frozen.expectationKnown||
  JSON.stringify(fixture.expectedGestures)!==JSON.stringify(frozen.expectationKnown?frozen.expectedGestures:[]))throw Error('Frozen fixture binding mismatch: '+name);
}
const result={startedAt:new Date().toISOString(),scope:'Supplemental bridge-only native model comparison; actual NativeVideoReplay and validated event route; no game UI/full-game acceptance',
 uiAcceptance:'not-exercised',jsReducerScoring:'not-exercised',protocolACK:'Maximum actually received native event sequence; receipt ACK only, not UI rays or scoring',
 cameraUsed:false,physicalDevice:false,fireOSVerified:false,macInferenceService:false,cohortSha256:PLAN_SHA,
 model:{id:'float16',sha256:selected.sha256,bytes:selected.bytes,inputSize:selected.input.shape[1],runtime:'LiteRT1.4.2',refinement:'image-three-pass'},
 privacyBoundary:'Established separately by parent OS-sandbox controller, not by this runner',cases:[]};
let browser,forwarded=false,guardPassed=false;
const save=(file,value)=>fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
try{
 await options.guard();guardPassed=true;
 result.device={api:(await adb(['shell','getprop','ro.build.version.sdk'])).trim(),abi:(await adb(['shell','getprop','ro.product.cpu.abi'])).trim(),model:(await adb(['shell','getprop','ro.product.model'])).trim()};
 for(const name of cohort){
  const frozen=plan.cases.find(item=>item.caseId===name),fixture=lock.fixtures.find(item=>item.case===name);
  const config='verification/'+name+'.float16.json';
  const row={name,startedAt:new Date().toISOString(),scope:result.scope,uiAcceptance:'not-exercised',jsReducerScoring:'not-exercised',
   expectedGestures:frozen.expectationKnown?frozen.expectedGestures:null,expectationKnown:frozen.expectationKnown,preliminaryAIOnly:true,
   packets:[],transportErrors:[],pageErrors:[],protocolACKPolicy:result.protocolACK};
  result.cases.push(row);
  let pid='',page,client,context,storageBefore,activeStarted,delivered=new Map(),everVerified=false,rawLog='',logCaptured=false;
  const getLog=async()=>{
   if(!/^\d+$/.test(pid))return '';
   const text=await adb(['logcat','-d','--pid='+pid,'-s','SwayNativeVideo:I']);logCaptured=true;return text;
  };
  try{
   await adb(['shell','am','force-stop','com.togethermove.tv.motion']);
   await adb(['shell','am','start','-n','com.togethermove.tv.motion/com.togethermove.tv.MainActivity','--ez','nativeVideo','true','--es','nativeVideoCase',name,'--es','nativeModel','float16','--es','nativeRefinement','image']);
   for(let i=0;i<30&&!pid;i++){pid=(await adb(['shell','pidof','com.togethermove.tv.motion']).catch(()=>'' )).trim();if(!pid)await sleep(200);}
   if(!/^\d+$/.test(pid))throw Error('No app PID');
   if(forwarded)await adb(['forward','--remove','tcp:9343']);
   await adb(['forward','--no-rebind','tcp:9343','localabstract:webview_devtools_remote_'+pid]);forwarded=true;
   for(let i=0;i<30;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9343');break;}catch(error){if(i===29)throw error;await sleep(200);}}
   page=browser.contexts()[0].pages()[0];page.on('pageerror',error=>row.pageErrors.push(error.message));
   await page.waitForSelector('[data-action="choose:1"]');
   storageBefore=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));row.storageBeforeSha256=sha(storageBefore);
   row.initialHome=await page.evaluate(()=>document.querySelector('.app')?.className==='app home');
   if(!row.initialHome)throw Error('Bridge supplement must remain on home screen');
   await page.evaluate(()=>{window.__bridgeCameraCalls=0;if(navigator.mediaDevices?.getUserMedia)navigator.mediaDevices.getUserMedia=()=>{window.__bridgeCameraCalls++;throw Error('Camera forbidden in recorded-video bridge comparison');};});
   context={clientId:crypto.randomUUID(),roundId:crypto.randomUUID(),revision:0,active:true,mode:'standing',after:0};
   client=createMotionClient({getContext:()=>context,intervalMs:200,requestTimeoutMs:1400,
    fetchImpl:async(url)=>{
     const value=await page.evaluate(async url=>{
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),1200);
      try{const response=await fetch(url,{method:'GET',headers:{Accept:'application/json'},cache:'no-store',credentials:'omit',redirect:'error',signal:controller.signal});
       return {ok:response.ok,status:response.status,length:response.headers.get('content-length'),text:await response.text()};
      }finally{clearTimeout(timer);}
     },url);
     return {ok:value.ok,status:value.status,headers:{get:name=>name==='content-length'?value.length:null},text:async()=>value.text};
    },onError:error=>row.transportErrors.push({code:error.code??null,message:error.message}),
    onPacket:packet=>{
     const runtime=packet.runtime,metrics=packet.metrics;
     if(packet.source!=='video'||runtime.engine!=='litert'||runtime.engineVersion!=='1.4.2'||runtime.modelSha256!==selected.sha256||
      runtime.modelId!=='float16'||runtime.inputSize!==192||metrics.modelInferencesPerFrame!==3||metrics.statelessCropRefinement!==true)throw Error('Native runtime/profile mismatch');
     row.packets.push(packet);everVerified||=runtime.verified===true;
     if(packet.events.length&&!runtime.verified)throw Error('Unverified runtime emitted semantic events');
     for(const event of packet.events){
      const old=delivered.get(event.seq);
      if(old&&(old.gesture!==event.gesture||old.confidence!==event.confidence))throw Error('Event sequence changed contents');
      if(!old)delivered.set(event.seq,{seq:event.seq,gesture:event.gesture,confidence:event.confidence,ageMsAtFirstReceipt:event.ageMs});
      context.after=Math.max(context.after,event.seq); // Actual receipt ACK, explicitly not a game score.
     }
    }});
   activeStarted=Date.now();row.terminationReason='bridge-wall-deadline';
   while(Date.now()-activeStarted<120000){
    const packet=await client.pollOnce();if(!packet)throw Error('Validated native bridge request failed');
    if(packet.status==='camera-error')throw Error('Native recorded-video source failed: '+(packet.error??'camera-error'));
    if(packet.metrics.fullFileProcessed){row.fullFilePacket=packet;row.terminationReason='full-file';break;}
    await sleep(200);
   }
   row.activeWallMs=Date.now()-activeStarted;
  }catch(error){row.error={message:error.message};}
  finally{
   // Do not leave an active lease after EOF, a deadline or a failed request.
   if(client&&context){
    context={...context,revision:context.revision+1,active:false};
    try{row.deactivatedPacket=await client.pollOnce();row.explicitlyDeactivated=row.deactivatedPacket?.active===false;}catch(error){row.deactivationError=error.message;}
    client.stop();
   }
   if(page){try{
    const state=await page.evaluate(()=>({home:document.querySelector('.app')?.className==='app home',storage:localStorage.getItem('togethermove.v1'),cameraCalls:window.__bridgeCameraCalls}));
    row.finalHome=state.home;row.progressUnchanged=storageBefore===state.storage;row.storageAfterSha256=sha(state.storage);row.cameraCalls=state.cameraCalls;
   }catch(error){row.stateObservationError=error.message;}}
   if(/^\d+$/.test(pid)){
    try{
     // Home's real Back handler returns false, so MainActivity.finish calls native close.
     if(row.finalHome===true)await adb(['shell','input','keyevent','4']);
     else row.closeRequestError='Home screen unavailable; no claim that Back closed the Activity';
     const closing=Date.now();
     while(Date.now()-closing<8000){rawLog=await getLog();row.closedSummary=nativeSummaryRows(rawLog,config).findLast(item=>item.kind==='stopped');if(row.closedSummary)break;await sleep(150);}
     row.closeWaitMs=Date.now()-closing;
    }catch(error){row.captureError=error.message;}
   }
   try{
    if(!logCaptured){try{rawLog=await getLog();}catch(error){row.captureError=error.message;}}
    const scalar=nativeScalarRows(rawLog,config),summaries=nativeSummaryRows(rawLog,config);
    for(const [suffix,values] of [['native-scalar',scalar],['native-summary',summaries]]){
     const body=values.map(item=>JSON.stringify(item)).join('\n')+(values.length?'\n':'');const file=out+'/'+name+'.'+suffix+'.jsonl';
     fs.writeFileSync(file,body,{flag:'wx'});row[suffix]={available:logCaptured,path:file,sha256:sha(body),rows:values.length,pid:pid||null,configAsset:config};
    }
    row.nativePoseFrameCoverage=nativeFrameCoverage(scalar,fixture);
    row.nativeFileEvents=scalar.filter(item=>item.kind==='event').map(item=>({seq:item.seq,gesture:item.gesture,confidence:item.confidence,fileMs:item.eventFileMs}));
    row.deliveredEvents=[...delivered.values()].sort((a,b)=>a.seq-b.seq);
    row.protocolAfter=context?.after??0;
    row.deliveryMatches=row.nativeFileEvents.every((item,index)=>item.seq===index+1&&Number.isFinite(item.fileMs))&&
     JSON.stringify(row.nativeFileEvents.map(({seq,gesture})=>({seq,gesture})))===JSON.stringify(row.deliveredEvents.map(({seq,gesture})=>({seq,gesture})));
    row.nativePerformanceSummary=summaries.findLast(item=>item.kind==='stopped')??summaries.at(-1)??null;
    row.resourcesClosed=row.closedSummary?.resourcesClosed===true&&row.closedSummary?.cleanupSucceeded===true&&row.closedSummary?.verified===false;
    const metrics=row.fullFilePacket?.metrics,finalMetrics=row.deactivatedPacket?.metrics;
    row.completeFileVerified=metrics?.fullFileProcessed===true&&metrics.videoFrames===fixture.frames&&metrics.decodedFrames===fixture.frames&&
     metrics.acceptedFrames===fixture.frames&&metrics.discardedEpochFrames===0&&Math.abs(metrics.fileMs-fixture.frames*1000/fixture.fps)<1e-6&&row.nativePoseFrameCoverage.complete;
    row.protocolACKMatches=finalMetrics?.acknowledgedEvents===row.nativeFileEvents.length&&row.closedSummary?.acknowledgedEvents===row.nativeFileEvents.length;
    row.executionAcceptance=!row.error&&logCaptured&&everVerified&&row.completeFileVerified&&row.deliveryMatches&&row.protocolACKMatches&&row.resourcesClosed&&
     row.explicitlyDeactivated&&row.initialHome&&row.finalHome&&row.progressUnchanged&&row.cameraCalls===0&&row.pageErrors.length===0?'passed':'failed';
    row.recognitionObservation=row.executionAcceptance==='passed'?(frozen.expectationKnown?(row.nativeFileEvents.length===0?'matches-preliminary-AI-zero-reference':'violates-preliminary-AI-zero-reference'):'unknown-sequence-observed-only'):'incomplete-or-failed';
   }catch(error){row.evidenceError=error.message;row.executionAcceptance='failed';}
   row.finishedAt=new Date().toISOString();row.caseWallMs=Date.parse(row.finishedAt)-Date.parse(row.startedAt);save(out+'/'+name+'.json',row);
   if(browser)await browser.close().catch(()=>{});browser=null;
   if(guardPassed)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});
  }
  console.log(JSON.stringify({case:name,scope:'bridge-only',execution:row.executionAcceptance,termination:row.terminationReason,frames:row.nativePoseFrameCoverage?.uniqueFrames,events:row.nativeFileEvents?.length,protocolACKs:row.closedSummary?.acknowledgedEvents,resourcesClosed:row.resourcesClosed,error:row.error??row.evidenceError??null}));
 }
 result.status=result.cases.every(row=>row.executionAcceptance==='passed')?'bridge-comparison-completed':'bridge-comparison-incomplete';
 if(result.status!=='bridge-comparison-completed')process.exitCode=1;
}catch(error){result.status='blocked';result.error={message:error.message};process.exitCode=1;}
finally{
 if(browser)await browser.close().catch(()=>{});
 if(forwarded)await adb(['forward','--remove','tcp:9343']).catch(()=>{});
 if(guardPassed)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});
 result.finishedAt=new Date().toISOString();save(out+'/result.json',result);
}
