import fs from 'node:fs';
import crypto from 'node:crypto';
import {chromium} from '@playwright/test';
import {nativeOptions} from './native-emulator-options.mjs';
import {nativeScalarRows,nativeSummaryRows,nativeAttemptRows,nativePerformanceRows,nativeUiScoreVerified,nativeDiagnosticRoundVerified,nativeCompletionVerified,assessNativeCase} from './native-video-evidence.mjs';
const options=nativeOptions(),{adb,out,cases}=options;
if(fs.readdirSync(out).length)throw Error('Refusing nonempty verification output directory');
const lock=JSON.parse(fs.readFileSync(new URL('../android/native-video-assets.lock.json',import.meta.url),'utf8'));
const selectedModel=lock.artifacts.find(item=>options.model==='int8'?item.role==='model':item.role==='candidate-model'&&item.modelId===options.model);
if(!selectedModel)throw Error('Selected native model is not pinned');
const ROUND_SECONDS=120,CASE_DEADLINE_MS=150000;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const sha=value=>crypto.createHash('sha256').update(value??'<absent>').digest('hex');
function readUiState(){
 const garden=document.querySelector('.sunshine-garden'),app=document.querySelector('.app');
 const countText=garden?.getAttribute('data-motion-count')??null;
 return {gardenPresent:!!garden,countText,count:countText===null?null:Number(countText),
  countLabel:document.querySelector('#sunshine-count')?.textContent?.trim()??null,
  raySlots:garden?.querySelectorAll('[data-ray]').length??null,
  collectedRays:garden?.querySelectorAll('[data-ray].collected').length??null,
  source:garden?.dataset.motionSource??null,badgeText:document.querySelector('#camera-source')?.textContent?.trim()??null,
  screen:app?.className,heading:document.querySelector('main h1')?.textContent?.trim()??null,
  rayLabel:document.querySelector('main .step')?.textContent?.trim()??'',
  simulatedRayLabel:document.querySelector('.test-result .garden-caption b')?.textContent?.trim()??'',
  roundSecondsText:app?.getAttribute('data-round-seconds')??null,
  diagnosticReplayText:app?.getAttribute('data-diagnostic-replay')??null,
  timerText:document.querySelector('#time')?.textContent?.trim()??null,
  roundStart:window.__nativeRoundStart??null,body:document.body.innerText,
  packets:window.__nativeObserved??[],cameraCalls:window.__cameraCalls,
  storage:localStorage.getItem('togethermove.v1')};
}
function installObservation(){
 window.__nativeObserved=[];window.__cameraCalls=0;window.__nativeRoundStart=null;
 if(navigator.mediaDevices?.getUserMedia)navigator.mediaDevices.getUserMedia=()=>{window.__cameraCalls++;throw Error('Camera forbidden in video verification');};
 const parse=JSON.parse;
 JSON.parse=function(...args){const packet=parse.apply(this,args);if(packet?.protocol===1&&packet?.runtime&&packet?.source)window.__nativeObserved.push({runtime:packet.runtime,source:packet.source,status:packet.status,seq:packet.seq,active:packet.active,revision:packet.revision,events:packet.events,metrics:packet.metrics,at:performance.now()});return packet;};
 // Observe the real Start render before the next animation frame. No clock or event is injected.
 document.addEventListener('click',event=>{
  if(!event.target?.closest?.('[data-action="start"]'))return;
  queueMicrotask(()=>{const app=document.querySelector('.app');window.__nativeRoundStart={
   roundSecondsText:app?.getAttribute('data-round-seconds')??null,
   diagnosticReplayText:app?.getAttribute('data-diagnostic-replay')??null,
   timerText:document.querySelector('#time')?.textContent?.trim()??null,at:performance.now()};});
 });
}
function scoreSnapshot(state){
 return {ui:{gardenPresent:state.gardenPresent,countText:state.countText,count:state.count,countLabel:state.countLabel,
  raySlots:state.raySlots,collectedRays:state.collectedRays,source:state.source,badgeText:state.badgeText,
  screen:state.screen,replayLabel:state.body.includes('VIDEO REPLAY')||state.body.includes('Video replay'),cameraCalls:state.cameraCalls},
  packets:state.packets,lastPacket:state.packets.at(-1),storageSha256:sha(state.storage)};
}
const result={startedAt:new Date().toISOString(),cameraUsed:false,physicalDevice:false,fireOSVerified:false,macInferenceService:false,
 diagnosticRoundSeconds:ROUND_SECONDS,nativeRefinement:options.refinement,completionRequested:options.completion,
 selectedModel:{id:options.model,sha256:selectedModel.sha256,bytes:selectedModel.bytes,inputSize:selectedModel.input.shape[1]},cases:[]};
let browser,forwarded=false,guardPassed=false;
try{
 await options.guard();guardPassed=true;
 result.device={api:(await adb(['shell','getprop','ro.build.version.sdk'])).trim(),abi:(await adb(['shell','getprop','ro.product.cpu.abi'])).trim(),model:(await adb(['shell','getprop','ro.product.model'])).trim()};
 for(const name of cases){
  const row={name,nativeModel:options.model,nativeRefinement:options.refinement,packets:[],pageErrors:[],consoleErrors:[],startedAt:new Date().toISOString()};result.cases.push(row);
  const expected=lock.fixtures.find(fixture=>fixture.case===name);
  const config='verification/'+name+(options.model==='int8'?'':'.'+options.model)+'.json';
  let pid='',page,before,nativeRows=[],started,deadline,closedLog='',captures=new Set();
  const getLog=async()=>{
   if(!/^\d+$/.test(pid))throw Error('No verified app PID available for native diagnostics');
   return adb(['logcat','-d','--pid='+pid,'-s','SwayNativeVideo:I']);
  };
  const captureNative=async(phase='final')=>{
   if(captures.has(phase))return;captures.add(phase);
   const stem=out+'/'+name+(phase==='eof'?'.eof':'');
   const file=stem+'.native-scalar.jsonl',summaryFile=stem+'.native-summary.jsonl',attemptFile=stem+'.native-attempt.jsonl',performanceFile=stem+'.native-performance.jsonl';
   let scalarLog,summaryLog,attemptLog,performanceLog,summary=null;
   try{
    const text=phase==='final'&&closedLog?closedLog:await getLog();
    const scalars=nativeScalarRows(text,config),summaries=nativeSummaryRows(text,config),attempts=nativeAttemptRows(text,config),performance=nativePerformanceRows(text,config);
    for(const [target,rows] of [[file,scalars],[summaryFile,summaries],[attemptFile,attempts],[performanceFile,performance]]){
     const body=rows.map(item=>JSON.stringify(item)).join('\n')+(rows.length?'\n':'');fs.writeFileSync(target,body,{flag:'wx'});
    }
    scalarLog={available:true,path:file,sha256:sha(fs.readFileSync(file)),rows:scalars.length,pid,configAsset:config,phase};
    summaryLog={available:true,path:summaryFile,sha256:sha(fs.readFileSync(summaryFile)),rows:summaries.length,pid,configAsset:config,phase};
    attemptLog={available:true,path:attemptFile,sha256:sha(fs.readFileSync(attemptFile)),rows:attempts.length,pid,configAsset:config,phase};
    performanceLog={available:true,path:performanceFile,sha256:sha(fs.readFileSync(performanceFile)),rows:performance.length,pid,configAsset:config,phase};
    summary=summaries.findLast(item=>['stopped','finished'].includes(item.kind)&&item.fullFileProcessed===true)??summaries.at(-1)??null;
    if(phase==='final'){
     nativeRows=scalars;row.nativeClosedSummary=summaries.findLast(item=>item.kind==='stopped')??null;
     row.resourcesClosed=row.nativeClosedSummary?.resourcesClosed===true&&row.nativeClosedSummary?.cleanupSucceeded===true&&row.nativeClosedSummary?.verified===false;
    }
   }catch(error){
    if(!fs.existsSync(file))fs.writeFileSync(file,'',{flag:'wx'});
    if(!fs.existsSync(summaryFile))fs.writeFileSync(summaryFile,'',{flag:'wx'});
    if(!fs.existsSync(attemptFile))fs.writeFileSync(attemptFile,'',{flag:'wx'});
    if(!fs.existsSync(performanceFile))fs.writeFileSync(performanceFile,'',{flag:'wx'});
    scalarLog={available:false,path:file,pid:pid||null,error:error.message,phase};summaryLog={available:false,path:summaryFile,pid:pid||null,error:error.message,phase};
    const attemptBody=fs.readFileSync(attemptFile,'utf8');
    attemptLog={available:false,path:attemptFile,sha256:sha(attemptBody),rows:attemptBody.split('\n').filter(Boolean).length,pid:pid||null,configAsset:config,error:error.message,phase};
    performanceLog={available:false,path:performanceFile,pid:pid||null,configAsset:config,error:error.message,phase};
   }
   if(phase==='eof'){row.eofNativeScalarLog=scalarLog;row.eofNativeSummaryLog=summaryLog;row.eofNativeAttemptLog=attemptLog;row.eofNativePerformanceLog=performanceLog;row.eofNativePerformanceSummary=summary;}
   else{row.nativeScalarLog=scalarLog;row.nativeSummaryLog=summaryLog;row.nativeAttemptLog=attemptLog;row.nativePerformanceLog=performanceLog;row.nativePerformanceSummary=summary;}
   row.nativePerformanceScope='PID/config/kind-filtered primitive scalars only; no pixels or nested poseDiagnostics. Native three-pass inference and frame/reference overhead differ from full UI wall time. PSS is an app-process snapshot, not sustained/full-TV peak.';
  };
  const waitInactive=async()=>{
   await page.waitForFunction(()=>window.__nativeObserved?.at(-1)?.active===false,undefined,{timeout:5000});
   return page.evaluate(()=>window.__nativeObserved.at(-1));
  };
  const closeActivity=async()=>{
   if(!page||typeof page.evaluate!=='function')return;
   try{
    let state=await page.evaluate(readUiState);
    if(state.screen!=='app home'){
     await page.locator('[data-action="home"]').first().click();
     await page.waitForFunction(()=>document.querySelector('.app')?.className==='app home',undefined,{timeout:5000});
     if(state.packets.length)row.cleanupInactivePacket=await waitInactive();
    }
    state=await page.evaluate(readUiState);
    row.cleanupHome={screen:state.screen,storageSha256:sha(state.storage),progressUnchanged:before===state.storage,cameraCalls:state.cameraCalls};
    if(state.screen!=='app home')throw Error('Activity close requires actual home screen');
    await adb(['shell','input','keyevent','4']);
    const closing=Date.now();
    while(Date.now()-closing<8000){closedLog=await getLog();if(nativeSummaryRows(closedLog,config).some(item=>item.kind==='stopped'))break;await sleep(150);}
    row.cleanupWaitMs=Date.now()-closing;
   }catch(error){row.cleanupError=error.message;}
  };
  try{
   if(!expected)throw Error('Missing frozen fixture binding');
   await adb(['shell','am','force-stop','com.togethermove.tv.motion']);
   await adb(['shell','am','start','-n','com.togethermove.tv.motion/com.togethermove.tv.MainActivity','--ez','nativeVideo','true','--es','nativeVideoCase',name,'--es','nativeModel',options.model,'--es','nativeRefinement',options.refinement]);
   for(let i=0;i<30&&!pid;i++){pid=(await adb(['shell','pidof','com.togethermove.tv.motion']).catch(()=>'' )).trim();if(!pid)await sleep(200);}
   if(!/^\d+$/.test(pid))throw Error('missing app pid');
   if(forwarded)await adb(['forward','--remove','tcp:9341']);
   await adb(['forward','--no-rebind','tcp:9341','localabstract:webview_devtools_remote_'+pid]);forwarded=true;
   for(let i=0;i<30;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9341');break;}catch(error){if(i===29)throw error;await sleep(200);}}
   page=browser.contexts()[0].pages()[0];
   page.on('pageerror',error=>row.pageErrors.push(error.message));page.on('console',message=>{if(message.type()==='error')row.consoleErrors.push(message.text());});
   await page.waitForSelector('[data-action="choose:1"]');
   before=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));row.storageBeforeSha256=sha(before);
   await page.addInitScript(installObservation);await page.evaluate(installObservation);
   for(const action of ['choose:1','mode:standing','input:camera'])await page.locator('[data-action="'+action+'"]').click();
   started=Date.now();deadline=started+CASE_DEADLINE_MS;
   await page.locator('[data-action="start"]').click();
   let state=await page.evaluate(readUiState),sawActive=false;
   row.initialRound=state.roundStart;row.roundMarkerVerified=nativeDiagnosticRoundVerified(row.initialRound);
   if(!row.roundMarkerVerified)throw Error('Expected explicit native diagnostic marker and actual initial120s timer');
   row.terminationReason='harness-wall-deadline';
   while(Date.now()<deadline){
    state=await page.evaluate(readUiState);const packet=state.packets.at(-1);
    if(packet?.active===true)sawActive=true;
    if(packet?.metrics?.fullFileProcessed){row.terminationReason='full-file';row.eofSnapshot=scoreSnapshot(state);row.eofWallMs=Date.now()-started;break;}
    if(packet?.status==='camera-error'){row.terminationReason='native-error';break;}
    if(sawActive&&packet?.active===false){row.terminationReason='inactive-before-full-file';break;}
    await sleep(150);
   }
   // A short real polling interval settles the actual frontend ACK; keep the first EOF observation too.
   await sleep(450);const settled=await page.evaluate(readUiState);
   const scoring=nativeUiScoreVerified(scoreSnapshot(settled).ui)?settled:state;
   const snapshot=scoreSnapshot(scoring);row.ui=snapshot.ui;row.packets=snapshot.packets;row.lastPacket=snapshot.lastPacket;
   row.storageAfterSha256=sha(scoring.storage);row.progressUnchanged=before===scoring.storage;row.wallMs=Date.now()-started;
   row.integrationVerified=row.roundMarkerVerified&&row.packets.some(packet=>packet.runtime.engine==='litert'&&packet.runtime.verified&&packet.runtime.modelSha256===selectedModel.sha256&&packet.runtime.modelId===options.model&&packet.runtime.inputSize===selectedModel.input.shape[1]&&packet.source==='video'&&packet.metrics?.modelInferencesPerFrame===(options.refinement==='image'?3:1)&&packet.metrics?.statelessCropRefinement===(options.refinement==='image'))&&nativeUiScoreVerified(row.ui)&&row.progressUnchanged&&scoring.cameraCalls===0&&row.pageErrors.length===0;
   const events=new Map();for(const packet of row.packets)for(const event of packet.events)events.set(event.seq,event.gesture);
   row.observedGestures=[...events.entries()].sort((a,b)=>a[0]-b[0]).map(entry=>entry[1]);
   await captureNative('eof');
   row.completion={requested:options.completion,status:options.completion?'pending':'not-requested',roundSeconds:ROUND_SECONDS};
   if(options.completion){
    try{
     if(!nativeUiScoreVerified(row.ui))throw Error('No valid preserved EOF/video score observation');
     await page.waitForFunction(()=>{const app=document.querySelector('.app');return app?.classList.contains('check')||app?.classList.contains('celebrate');},undefined,{timeout:Math.max(1,deadline-Date.now())});
     let terminal=await page.evaluate(readUiState);
     row.completion.realWallMs=Date.now()-started;row.completion.realTimerElapsed=row.completion.realWallMs>=119000;
     if(terminal.screen?.split(' ').includes('check')){
      row.completion.path='check-confirmation';row.completion.check={screen:terminal.screen,heading:terminal.heading,rayLabel:terminal.rayLabel,simulatedRayLabel:terminal.simulatedRayLabel};
      row.completion.inactivePacket=await waitInactive();
      row.completion.completeButtonLabel=await page.locator('[data-action="complete"]').textContent();
      await page.locator('[data-action="complete"]').click();row.completion.realCompleteButtonClicked=true;
      await page.waitForFunction(()=>document.querySelector('.app')?.classList.contains('celebrate'),undefined,{timeout:5000});
     }else{row.completion.path='six-ray-auto-celebration';row.completion.inactivePacket=await waitInactive();}
     terminal=await page.evaluate(readUiState);
     row.completion.celebration={screen:terminal.screen,heading:terminal.heading,rayLabel:terminal.rayLabel,simulatedRayLabel:terminal.simulatedRayLabel,
      replayLabel:terminal.body.includes('VIDEO REPLAY'),storageSha256:sha(terminal.storage),cameraCalls:terminal.cameraCalls};
     row.completion.progressUnchangedAtCelebration=before===terminal.storage;
     await page.reload({waitUntil:'domcontentloaded'});await page.waitForSelector('[data-action="choose:1"]');
     const reloaded=await page.evaluate(readUiState);
     row.completion.reload={screen:reloaded.screen,storageSha256:sha(reloaded.storage),cameraCalls:reloaded.cameraCalls};
     row.completion.progressUnchangedAfterReload=before===reloaded.storage;
     row.completion.status=nativeCompletionVerified(row.completion,row.ui.count)&&row.pageErrors.length===0?'passed':'failed';
    }catch(error){row.completion.status='failed';row.completion.error=error.message;}
   }
  }catch(error){row.harnessError={message:error.message};row.terminationReason??='harness-error-before-active-loop';}
  finally{
   await closeActivity();await captureNative('final');
   if(expected)assessNativeCase(row,expected,nativeRows);else{row.executionAcceptance='failed';row.recognitionAcceptance='failed';}
   row.fullFlowExecutionVerified=row.executionAcceptance==='passed'&&row.resourcesClosed===true&&row.cleanupHome?.progressUnchanged===true&&row.cleanupHome?.cameraCalls===0&&(!options.completion||row.completion?.status==='passed');
   row.finishedAt=new Date().toISOString();row.caseWallMs=Date.parse(row.finishedAt)-Date.parse(row.startedAt);
   fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(row,null,2));
   if(browser)await browser.close().catch(()=>{});browser=null;
   if(guardPassed)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});
  }
  console.log(JSON.stringify({case:name,model:options.model,refinement:options.refinement,completion:row.completion?.status,
   integration:row.integrationVerified,recognition:row.recognitionAcceptance,fullFlow:row.fullFlowExecutionVerified,resourcesClosed:row.resourcesClosed,ui:row.ui,lastMetrics:row.lastPacket?.metrics,pageErrors:row.pageErrors}));
 }
 result.status='execution-completed';result.executionAccepted=result.cases.every(row=>row.fullFlowExecutionVerified);
 result.recognitionAccepted=result.cases.every(row=>row.recognitionAcceptance==='passed');
 result.recognitionStatus=result.cases.some(row=>row.recognitionAcceptance==='failed')?'failed':result.recognitionAccepted?'matches-known-frozen-reference':'observed-only-incomplete-reference';
 result.completionVerifiedCases=result.cases.filter(row=>row.completion?.status==='passed').length;
 result.completionStatus=!options.completion?'not-requested':result.cases.every(row=>row.completion?.status==='passed')?'passed':'failed';
 if(!result.executionAccepted||result.recognitionStatus==='failed'||result.completionStatus==='failed')process.exitCode=1;
}catch(error){result.status='blocked';result.error={message:error.message,stack:error.stack};process.exitCode=1;console.error(error.message);}
finally{
 if(browser)await browser.close().catch(()=>{});
 if(forwarded)await adb(['forward','--remove','tcp:9341']).catch(()=>{});
 if(guardPassed)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});
 result.finishedAt=new Date().toISOString();fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2));
}
