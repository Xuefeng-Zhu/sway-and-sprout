import fs from 'node:fs';
import crypto from 'node:crypto';
import {chromium} from '@playwright/test';
import {nativeOptions} from './native-emulator-options.mjs';
const options=nativeOptions(),{adb,out,cases}=options;
const lock=JSON.parse(fs.readFileSync(new URL('../android/native-video-assets.lock.json',import.meta.url),'utf8'));
const selectedModel=lock.artifacts.find(item=>options.model==='int8'?item.role==='model':item.role==='candidate-model'&&item.modelId===options.model);
if(!selectedModel)throw Error('Selected native model is not pinned');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const sha=value=>crypto.createHash('sha256').update(value??'<absent>').digest('hex');
const result={startedAt:new Date().toISOString(),cameraUsed:false,physicalDevice:false,fireOSVerified:false,macInferenceService:false,nativeRefinement:options.refinement,completionRequested:options.completion,selectedModel:{id:options.model,sha256:selectedModel.sha256,bytes:selectedModel.bytes},cases:[]};
let browser,forwarded=false,guardPassed=false;
try {
 await options.guard();guardPassed=true;
 result.device={api:(await adb(['shell','getprop','ro.build.version.sdk'])).trim(),abi:(await adb(['shell','getprop','ro.product.cpu.abi'])).trim(),model:(await adb(['shell','getprop','ro.product.model'])).trim()};
 for(const name of cases){
  if(!/^(clear|frontal|nearface|right-negative|both-up-negative|natural-original|natural-mirror)$/.test(name))throw Error('unknown case');
  const row={name,nativeModel:options.model,nativeRefinement:options.refinement,packets:[],pageErrors:[],consoleErrors:[],startedAt:new Date().toISOString()};result.cases.push(row);
  await adb(['shell','am','force-stop','com.togethermove.tv.motion']);
  await adb(['shell','am','start','-n','com.togethermove.tv.motion/com.togethermove.tv.MainActivity','--ez','nativeVideo','true','--es','nativeVideoCase',name,'--es','nativeModel',options.model,'--es','nativeRefinement',options.refinement]);
  let pid='';for(let i=0;i<30&&!pid;i++){pid=(await adb(['shell','pidof','com.togethermove.tv.motion']).catch(()=>'' )).trim();if(!pid)await sleep(200);}
  if(!/^\d+$/.test(pid))throw Error('missing app pid');
  if(forwarded)await adb(['forward','--remove','tcp:9341']);
  await adb(['forward','--no-rebind','tcp:9341','localabstract:webview_devtools_remote_'+pid]);forwarded=true;
  for(let i=0;i<30;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9341');break;}catch(e){if(i===29)throw e;await sleep(200);}}
  const page=browser.contexts()[0].pages()[0];
  page.on('pageerror',e=>row.pageErrors.push(e.message));page.on('console',m=>{if(m.type()==='error')row.consoleErrors.push(m.text());});
  await page.waitForSelector('[data-action="choose:1"]');
  const before=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));row.storageBeforeSha256=sha(before);
  await page.evaluate(()=>{
   window.__nativeObserved=[];window.__cameraCalls=0;
   if(navigator.mediaDevices?.getUserMedia){navigator.mediaDevices.getUserMedia=()=>{window.__cameraCalls++;throw Error('Camera forbidden in video verification');};}
   const parse=JSON.parse;
   JSON.parse=function(...args){const p=parse.apply(this,args);if(p?.protocol===1&&p?.runtime&&p?.source)window.__nativeObserved.push({runtime:p.runtime,source:p.source,status:p.status,seq:p.seq,active:p.active,revision:p.revision,events:p.events,metrics:p.metrics,at:performance.now()});return p;};
  });
  for(const action of ['choose:1','mode:standing','input:camera','start'])await page.locator('[data-action="'+action+'"]').click();
  const started=Date.now();let state;
  while(Date.now()-started<45000){
   state=await page.evaluate(()=>({count:Number(document.querySelector('.sunshine-garden')?.dataset.motionCount||0),source:document.querySelector('.sunshine-garden')?.dataset.motionSource,screen:document.querySelector('.app')?.className,body:document.body.innerText,packets:window.__nativeObserved,cameraCalls:window.__cameraCalls,storage:localStorage.getItem('togethermove.v1')}));
   const p=state.packets.at(-1);
   if(p?.metrics?.fullFileProcessed||p?.metrics?.acknowledgedEvents===6||p?.status==='camera-error')break;
   await sleep(150);
  }
  await sleep(450);
  state=await page.evaluate(()=>({count:Number(document.querySelector('.sunshine-garden')?.dataset.motionCount||0),source:document.querySelector('.sunshine-garden')?.dataset.motionSource,screen:document.querySelector('.app')?.className,body:document.body.innerText,packets:window.__nativeObserved,cameraCalls:window.__cameraCalls,storage:localStorage.getItem('togethermove.v1')}));
  row.packets=state.packets;row.ui={count:state.count,source:state.source,screen:state.screen,replayLabel:state.body.includes('VIDEO REPLAY')||state.body.includes('Video replay'),cameraCalls:state.cameraCalls};row.storageAfterSha256=sha(state.storage);row.progressUnchanged=before===state.storage;
  row.lastPacket=row.packets.at(-1);row.wallMs=Date.now()-started;
  row.integrationVerified=row.packets.some(p=>p.runtime.engine==='litert'&&p.runtime.verified&&p.runtime.modelSha256===selectedModel.sha256&&p.source==='video'&&p.metrics?.modelInferencesPerFrame===(options.refinement==='image'?3:1)&&p.metrics?.statelessCropRefinement===(options.refinement==='image'))&&row.progressUnchanged&&state.cameraCalls===0&&row.pageErrors.length===0;
  const expected=lock.fixtures.find(f=>f.case===name),events=new Map();
  for(const p of row.packets)for(const e of p.events)events.set(e.seq,e.gesture);
  row.observedGestures=[...events.entries()].sort((a,b)=>a[0]-b[0]).map(e=>e[1]);
  row.expectationScope='Frozen event sequence/count, UI rays and ACK; negative zero does not establish robust tracking';row.expectationKnown=expected.expectationKnown;row.expectedGestures=expected.expectationKnown?expected.expectedGestures:null;
  const expectedCount=expected.expectedGestures.length;
  row.recognitionAcceptance=expected.expectationKnown?(row.integrationVerified&&JSON.stringify(row.observedGestures)===JSON.stringify(expected.expectedGestures)&&row.ui.count===expectedCount&&row.lastPacket?.metrics?.acknowledgedEvents===expectedCount&&(expectedCount>0||row.lastPacket?.metrics?.fullFileProcessed===true)?'passed':'failed'):'observed-only';
  // Preserve row.ui/packets as the original scoring snapshot. Completion is a
  // separate real-timer observation; no reducer, timer or native event is injected.
  row.completion={requested:options.completion,status:options.completion?'not-exercised-no-six-rays':'not-requested'};
  if(options.completion&&row.ui.count===6&&row.ui.source==='video'){
   row.completion.status='pending';
   try{
    await page.waitForFunction(()=>document.querySelector('.app')?.classList.contains('celebrate'),undefined,{timeout:40000});
    const celebration=await page.evaluate(()=>({screen:document.querySelector('.app')?.className,heading:document.querySelector('main h1')?.textContent,replayLabel:document.body.innerText.includes('VIDEO REPLAY'),storage:localStorage.getItem('togethermove.v1'),cameraCalls:window.__cameraCalls}));
    row.completion.celebration={screen:celebration.screen,heading:celebration.heading,replayLabel:celebration.replayLabel,storageSha256:sha(celebration.storage),cameraCalls:celebration.cameraCalls};
    row.completion.wallFromStartMs=Date.now()-started;
    row.completion.realTimerElapsed=row.completion.wallFromStartMs>=29000;
    row.completion.progressUnchangedAtCelebration=before===celebration.storage;
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForSelector('[data-action="choose:1"]');
    const reloaded=await page.evaluate(()=>({screen:document.querySelector('.app')?.className,storage:localStorage.getItem('togethermove.v1')}));
    row.completion.reload={screen:reloaded.screen,storageSha256:sha(reloaded.storage)};
    row.completion.progressUnchangedAfterReload=before===reloaded.storage;
    row.completion.status=celebration.replayLabel&&celebration.cameraCalls===0&&row.completion.realTimerElapsed&&row.completion.progressUnchangedAtCelebration&&row.completion.progressUnchangedAfterReload&&reloaded.screen==='app home'&&row.pageErrors.length===0?'passed':'failed';
   }catch(error){row.completion.status='failed';row.completion.error=error.message;}
  }
  row.finishedAt=new Date().toISOString();
  fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(row,null,2));
  await browser.close();browser=null;
  console.log(JSON.stringify({case:name,model:options.model,refinement:options.refinement,completion:row.completion.status,integration:row.integrationVerified,recognition:row.recognitionAcceptance,ui:row.ui,lastMetrics:row.lastPacket?.metrics,pageErrors:row.pageErrors}));
 }
 result.status='execution-completed';result.recognitionAccepted=result.cases.every(r=>r.recognitionAcceptance!=='failed');result.completionVerifiedCases=result.cases.filter(r=>r.completion?.status==='passed').length;result.completionStatus=!options.completion?'not-requested':result.cases.some(r=>r.completion?.status==='failed')?'failed':result.completionVerifiedCases?'passed-for-completed-replays':'not-exercised-no-six-rays';if(!result.recognitionAccepted||result.completionStatus==='failed')process.exitCode=1;
}catch(e){result.status='blocked';result.error={message:e.message,stack:e.stack};process.exitCode=1;console.error(e.message);}
finally{
 if(browser)await browser.close().catch(()=>{});
 if(forwarded)await adb(['forward','--remove','tcp:9341']).catch(()=>{});
 if(guardPassed)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});
 result.finishedAt=new Date().toISOString();fs.writeFileSync(out+'/result.json',JSON.stringify(result,null,2));
}
