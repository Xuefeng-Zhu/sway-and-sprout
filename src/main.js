import './style.css';
import {challenges,normalizeProgress,complete,phaseAt,nearest} from './model.js';
import {createMotionState,acceptMotionEvent,createMotionClient} from './motion.js';
import {createPreviewClient} from './preview.js';
import {sunshineMarkup,updateSunshine,updateCameraPreview} from './motion-view.js';
import {roundTickDelta} from './round-clock.js';
import {gardenMarkup} from './garden-view.js';
import {cloudBackupLocationAllowed,createCloudGardenClient,cloudGardenErrorMessage,mergeGardenProgress} from './cloud-garden.js';

const root=document.querySelector('#app');
let saved;
try{saved=JSON.parse(localStorage.getItem('togethermove.v1'));}catch{}
const query=new URLSearchParams(location.search);
const nativeVideoCheck=query.get('input')==='video-verification';
// Empty by default. Native hosts retain their existing network restrictions.
const configuredCloud=document.querySelector('meta[name="sway-garden-api"]')?.content;
let cloudStorage;
try{cloudStorage=localStorage;}catch{}
const cloudGarden=typeof configuredCloud==='string'&&configuredCloud&&cloudBackupLocationAllowed(location)?
  createCloudGardenClient({endpoint:configuredCloud,storage:cloudStorage}):null;
let cloudStatus='',cloudDeleteConfirm=false;
// Strict recognition stays available for explicitly selected diagnostic sessions.
const motionPolicy=query.get('policy')==='strict'||(nativeVideoCheck&&query.get('policy')!=='activity')?'strict':'activity';
let progress=normalizeProgress(saved),screen='home',mode='seated',selected=0;
let elapsed=0,paused=false,last=null,frame=0,storageFailed=false,returnScreen='home';
let manualCount=0,journeyCompleted=[],harvestClaimed=false,returnFocus='',renderFocus='';
let roundTiming={wallMs:0,creditedMs:0,stalledMs:0,callbacks:0};
let inputMode='manual',roundId=crypto.randomUUID(),revision=0;
let motion=createMotionState(roundId,motionPolicy),packet=null,disconnected=false;
let roundSource=null,testSource=null,streamId=null,motionNotice='';
const clientId=crypto.randomUUID();
const cameraMode=()=>inputMode==='camera'&&challenges[selected].id==='sun';
const cameraActive=()=>cameraMode()&&screen==='play'&&!paused&&!motion.completed;
const simulatedSource=()=>testSource||(['video','synthetic'].includes(roundSource)?roundSource:null)||(['video','synthetic'].includes(packet?.source)?packet.source:null);
const cloudAvailable=()=>cloudGarden?.snapshot().configured&&!cameraMode()&&!simulatedSource()&&['home','cloud'].includes(screen);
const videoRound=()=>simulatedSource()==='video';
// Only the explicit native recorded-video diagnostic gets a longer diagnostic round.
const diagnosticReplayRound=()=>nativeVideoCheck&&cameraMode();
const roundSeconds=()=>diagnosticReplayRound()?120:challenges[selected].duration;
const motionClient=createMotionClient({
  getContext:()=>({clientId,roundId,revision,active:cameraActive(),mode,after:motion.lastSeq,policy:motionPolicy}),
  onPacket(value){
    // The inactive request has already released capture/ACKed its sequence.
    // Its response must not relabel a manual screen or an earned harvest.
    if(!cameraMode()){motionClient.stop();return;}
    if(['video','synthetic'].includes(value.source)&&!testSource)testSource=value.source;
    if(cameraMode()&&screen==='play'&&((roundSource&&roundSource!==value.source)||(streamId&&value.streamId&&streamId!==value.streamId))){
      const origin=testSource;resetRound();testSource=origin;elapsed=0;paused=true;revision++;packet=value;streamId=value.streamId||null;
      motionNotice=motionPolicy==='activity'?'Input changed. Round reset. Resume when ready.':'Input changed. Round reset. Resume with arms resting.';
      render();return;
    }
    packet=value;disconnected=false;
    streamId=value.streamId||streamId;
    if(cameraActive()&&value.runtime.verified){
      const wasCompleted=motion.completed;
      for(const event of value.events){
        const next=acceptMotionEvent(motion,event,{active:cameraActive()});
        if(next.count>motion.count)roundSource=value.source;
        motion=next;
      }
      // Completing the target changes active=true to false in the wire context.
      if(!wasCompleted&&motion.completed){revision++;previewClient.stop('complete');}
    }
    updateSunshine({motion,packet,paused,disconnected,notice:motionNotice,revision});
    syncPreview();
    // Deliver one inactive context before stopping, so the sidecar releases capture.
    if(!cameraMode()||screen==='celebrate'||screen==='harvest')motionClient.stop();
  },
  onError(){disconnected=true;previewClient.stop('unavailable');updateSunshine({motion,packet,paused,disconnected,notice:motionNotice,revision});if(!cameraMode()||screen==='celebrate'||screen==='harvest')motionClient.stop();},
});
const previewClient=createPreviewClient({
  getContext:()=>({clientId,roundId,revision,active:cameraActive(),mode,after:motion.lastSeq,policy:motionPolicy}),
  onPreview(preview){updateCameraPreview({preview,expected:motion.expected});},
  onClear(reason){updateCameraPreview({reason,expected:motion.expected,source:packet?.source});},
});
function syncPreview(){
  if(cameraActive()&&!disconnected&&packet?.source!=='synthetic')previewClient.start();
  else previewClient.stop(packet?.source==='synthetic'?'synthetic':motion.completed?'complete':paused?'paused':disconnected?'unavailable':'off');
}
function save(){try{localStorage.setItem('togethermove.v1',JSON.stringify(progress));}catch{storageFailed=true;}}
const button=(label,action,cls='',extra='')=>`<button class="${cls}" data-action="${action}" ${extra}>${label}</button>`;
function shell(content){
  const roundMetadata=screen==='play'?` data-round-seconds="${roundSeconds()}" data-diagnostic-replay="${diagnosticReplayRound()}"`:'';
  root.innerHTML=`<div class="app ${screen}${screen==='play'&&paused?' is-paused':''}${cameraMode()?' camera-mode':''}"${roundMetadata}><header><div class="brand" aria-label="Sway &amp; Sprout">Sway <span>&amp; Sprout</span></div><nav aria-label="Main navigation">${button('Garden','home',screen==='home'?'active':'')}${button('Help','help')}${cloudAvailable()?button('Garden backup','cloud',screen==='cloud'?'active':''):''}</nav></header><main>${content}</main><footer><span><kbd>↔ ↕</kbd> Navigate</span><span><kbd>OK</kbd> Select</span><span><kbd>↶</kbd> Back</span><span><kbd>II</kbd> Pause</span>${nativeVideoCheck?'<span class="privacy">Video diagnostic · no camera</span>':''}</footer></div>`;
  root.querySelectorAll('button').forEach(b=>b.onclick=()=>act(b.dataset.action));
  (renderFocus&&root.querySelector(`[data-action="${renderFocus}"]`)||root.querySelector('[autofocus]')||root.querySelector('main button'))?.focus();
}
function journeyStrip(){return `<ol class="journey-strip" aria-label="This garden visit">${challenges.map((c,i)=>`<li class="${journeyCompleted.includes(c.id)?'grown':selected===i?'current':''}"><b>${i+1}</b>${['Wake','Sunshine','Rain'][i]}${journeyCompleted.includes(c.id)?' · tended':''}</li>`).join('')}</ol>`;}
function testResultMarkup(result=false){
  const source=simulatedSource(),video=source==='video',label=video?'VIDEO REPLAY · NO CAMERA':'SYNTHETIC TEST · NO CAMERA';
  const heading=video?(result?'Replay result.':'Replay finished.'):(result?'Test result.':'Test round finished.');
  return `<section class="center-panel test-result"><p class="step">${label}</p><h1>${heading}</h1>${gardenMarkup({count:motion.count,label:`${motion.count}/6 simulated rays`})}<p>Saved garden unchanged.</p><div class="actions">${button(result?'Replay again':video?'View replay result':'View test result',result?'start':'complete','primary','autofocus')}${!result?button('Replay again','start'):''}${button('Garden','home')}</div><p class="subtle">${video?'This replay does not verify live human camera recognition.':'This test does not verify live human movement.'}</p></section>`;
}
function inputChoices(){
  if(challenges[selected].id!=='sun')return '';
  return `<fieldset class="input-choices"><legend>PLAY WITH</legend><div class="input-options">${button('<b>Manual</b>','input:manual',inputMode==='manual'?'selected':'',`aria-pressed="${inputMode==='manual'}"`)}${button(nativeVideoCheck?'<b>Video replay</b><small>Bundled test · no camera</small>':'<b>Camera (optional)</b>','input:camera',inputMode==='camera'?'selected':'',`aria-pressed="${inputMode==='camera'}"`)}</div>${nativeVideoCheck||inputMode==='camera'?`<p class="camera-setup-note">${nativeVideoCheck?'120s diagnostic. No camera.<br>Saved garden unchanged.':inputMode==='camera'?motionPolicy==='activity'?'Camera is off until Start. One player.<br>Frames stay local. No recording.':'Camera is off. One person only: face the camera with both shoulders and wrists visible. Rest both arms below your shoulders, with hands clear of your face. After Start, wait for Ready, then follow the cue. Frames stay on this device; nothing is recorded.':''}</p>`:''}</fieldset>`;
}
function render(focusAction=''){
  renderFocus=focusAction;
  // Remove the current image and invalidate requests before replacing the DOM.
  previewClient.stop();
  cancelAnimationFrame(frame);
  if(screen==='home'){
    shell(`<section class="hero"><div class="intro"><h1>Move a little.<br>Grow something.</h1><p>Small moves grow your garden.</p>${button(journeyCompleted.length===3?(harvestClaimed?'Grow again →':'Harvest your garden →'):journeyCompleted.length?'Keep growing →':'Start growing →',journeyCompleted.length===3?(harvestClaimed?'restart':'return-harvest'):'setup','primary','autofocus')}</div>${gardenMarkup({kind:'garden',completed:progress.completed,label:`${progress.completed.length}/3 blooms`})}</section><section class="challenge-list" aria-label="Three garden moments">${challenges.map((c,i)=>button(`<span class="number">0${i+1}</span><strong>${c.name}</strong><small>${journeyCompleted.includes(c.id)?'Tended':progress.completed.includes(c.id)?'Saved bloom':'30s'}</small>`,`choose:${i}`,'challenge',`style="--accent:${c.color}"`)).join('')}</section>`);
  }else if(screen==='setup'){
    shell(`<section class="panel setup-panel${challenges[selected].id==='sun'?' has-input-choices':''}"><div><p class="step">MOMENT ${selected+1} OF 3 · ${challenges[selected].name.toUpperCase()}</p><h1>Get ready.</h1><p>Choose a comfortable position.</p><div class="choices">${button('<b>Seated</b>','mode:seated',mode==='seated'?'selected':'',`aria-pressed="${mode==='seated'}"`)}${button('<b>Standing</b>','mode:standing',mode==='standing'?'selected':'',`aria-pressed="${mode==='standing'}"`)}</div>${inputChoices()}<p class="safety">${inputMode==='manual'?'Move, then press “Count my movement”.<br>Manual · self-reported · no camera':'Small moves welcome. Rest anytime.'}</p>${button(nativeVideoCheck&&inputMode==='camera'?'Start replay →':inputMode==='camera'?'Start camera →':'Start →','start','primary','autofocus')}</div><aside class="setup-art">${gardenMarkup({count:0,label:'Your next bloom'})}</aside></section>`);
  }else if(screen==='play'){
    const c=challenges[selected],camera=cameraMode();
    shell(`${journeyStrip()}<section class="play-panel" style="--accent:${c.color}"><div class="instruction"><p class="step">MOMENT ${selected+1} OF 3 · ${mode.toUpperCase()}${camera?'<span id="motion-input-mode" hidden aria-hidden="true"></span>':''}</p><h1>${c.name}</h1><p id="${camera?'camera-cue':'cue'}" class="cue">${camera?(motionPolicy==='activity'?'Move your way—wave, reach, stretch or sway.':'Start with both arms resting.'):c[mode][phaseAt(elapsed)]}</p><div class="timer"><div class="track"><div id="bar"></div></div><span id="time"></span></div>${camera&&motionPolicy==='strict'?'<p class="subtle">Six alternating raises. Left, rest, right, rest. Your own pace.</p>':''}<div class="actions">${button(paused?'Resume →':'Pause Ⅱ','pause',camera||paused?'primary':'',camera||paused?'autofocus':'')}${button('Change position','switch')}${camera?button('Manual play','manual'):''}${button('Garden','home')}</div></div>${camera?sunshineMarkup({policy:motionPolicy}):`<aside class="manual-feedback"><div id="manual-garden">${gardenMarkup({count:manualCount,label:manualCount===6?'Your bloom is ready':manualCount?'A little more growth':'Start with a small movement'})}</div><p id="manual-count" role="status" aria-live="polite">${manualCount} / 6 counted</p>${manualCount<6?button('Count my movement','manual-count','primary',paused?'disabled':'autofocus'):button('Finish moment →','finish-moment','primary',paused?'disabled':'autofocus')}<p class="harvest-note">Manual · self-reported · no camera</p></aside>`}</section>${paused?'<div class="pause-note" role="status">Paused. Rest anytime.</div>':''}`);
    updateTimer();
    if(camera)updateSunshine({motion,packet,paused,disconnected,notice:motionNotice,revision});
    // RAF timestamps are sampled at frame start, which can precede a click's
    // performance.now(). Establish the baseline from RAF itself on every resume.
    if(!paused){last=null;frame=requestAnimationFrame(tick);}
  }else if(screen==='check'){
    const c=challenges[selected],camera=cameraMode();
    if(simulatedSource()){
      shell(testResultMarkup());
      syncPreview();return;
    }
    shell(`<section class="center-panel">${gardenMarkup({count:camera?motion.count:manualCount,label:'Your bloom'})}<p class="step">${camera?'Camera rays · self-reported confirmation':'Manual · self-reported · no camera'}</p><h1>Did you move?</h1><p>Confirm your own participation.</p><div class="actions">${button('Grow this moment →','complete','primary','autofocus')}${button('Try again','start')}${button('Skip moment','skip')}</div>${camera?'<p class="subtle">Your report, not a recognition result.</p>':''}</section>`);
  }else if(screen==='celebrate'){
    if(simulatedSource()){
      shell(testResultMarkup(true));
      syncPreview();return;
    }
    const all=journeyCompleted.length===3;
    shell(`<section class="center-panel celebration">${journeyStrip()}<p class="step">${journeyCompleted.length}/3 moments tended${cameraMode()&&motion.completed?' · Camera sunshine':''}</p><h1>${all?'Ready to harvest.':'Your garden is growing.'}</h1><div class="garden-change">${gardenMarkup({kind:'garden',completed:progress.completed,label:`${progress.completed.length}/3 blooms`})}</div><div class="actions">${button(all?'Harvest garden →':'Next moment →',all?'harvest':'next','primary','autofocus')}${button('Garden','home')}</div><p class="subtle">${storageFailed?'Progress could not be saved on this device.':inputMode==='manual'?'Self-reported · saved on this device.':'Saved on this device.'}</p></section>`);
  }else if(screen==='harvest'){
    shell(`<section class="center-panel harvest"><h1>Your garden, gathered.</h1>${gardenMarkup({kind:'harvest',completed:progress.completed,showCaption:false})}<div class="actions">${button('Grow again →','restart','primary','autofocus')}${button('Garden','home')}</div><p class="harvest-note">${storageFailed?'Your garden is visible here, but could not be saved on this device.':'Growing again keeps your blooms.'}</p></section>`);
  }else if(screen==='cloud'&&cloudAvailable()){
    const state=cloudGarden.snapshot(),disabled=state.busy?'disabled':'';
    shell(`<section class="panel backup-panel"><div><p class="step">OPTIONAL GARDEN BACKUP</p><h1>Keep your blooms.</h1><p>Only blooms and harvest totals are sent.<br>Images and movement stay local.</p><p class="backup-status" role="status" aria-live="polite">${cloudStatus||'Choose an action to send data.'}</p><div class="actions">${cloudDeleteConfirm?`${button('Delete cloud copy','cloud-delete-confirm','primary',disabled)}${button('Keep it','cloud-delete-cancel','',disabled)}`:`${button('Back up garden','cloud-backup','primary',disabled)}${button('Restore saved blooms','cloud-restore','',disabled||(!state.hasIdentity?'disabled':''))}${button('Delete cloud copy','cloud-delete','',disabled||(!state.hasIdentity||!state.version?'disabled':''))}`}${button('Garden','home')}</div><p class="backup-key-note">This browser holds your backup key. Clearing its data removes access.</p></div><aside>${gardenMarkup({kind:'garden',completed:progress.completed,label:`${progress.completed.length} of 3 blooms saved on this device`})}</aside></section>`);
  }else if(screen==='help'){
    shell(`<section class="panel help-panel"><h1>How to play</h1><div class="help-grid"><div><h2>1. Move your way</h2><p>Sit or stand. Wave, reach, stretch or sway. Rest anytime.</p></div><div><h2>2. Watch it grow</h2><p>Manual: count a move, then confirm it.<br>Optional camera: activity gathers rays.</p></div><div><h2>3. Gather your garden</h2><p>Tend three moments to harvest.<br>Growing again keeps your blooms.</p></div></div><p class="safety">Camera is optional, for one player. Frames stay local. No recording.<br>Pause or Back stops input. Manual play is always available.</p>${button('Return →','return','primary','autofocus')}</section>`);
  }
  syncPreview();
}
function updateTimer(){
  const c=challenges[selected];
  if(!cameraMode())document.querySelector('#cue').textContent=c[mode][phaseAt(elapsed)];
  document.querySelector('#time').textContent=`${Math.max(0,Math.ceil(roundSeconds()-elapsed))}s`;
  document.querySelector('#bar').style.width=`${elapsed/roundSeconds()*100}%`;
  document.querySelector('.motion-art')?.classList.toggle('still',paused);
  document.querySelector('.sunshine-garden')?.classList.toggle('still',paused);
}
function finish(){
  const source=simulatedSource()||roundSource||packet?.source||'manual';
  const next=complete(progress,challenges[selected].id,source);
  if(next!==progress){
    progress=next;
    if(!journeyCompleted.includes(challenges[selected].id))journeyCompleted.push(challenges[selected].id);
    save();
  }
  screen='celebrate';revision++;render();
}
function tick(now){
  if(screen!=='play'||paused)return;
  const delta=roundTickDelta(last===null?now:last,now);last=now;
  elapsed+=delta.creditedMs/1000;
  for(const key of ['wallMs','creditedMs','stalledMs'])roundTiming[key]+=delta[key];
  roundTiming.callbacks++;
  if(elapsed>=roundSeconds()){
    if(cameraMode()&&motion.completed){finish();return;}
    screen='check';revision++;render();return;
  }
  updateTimer();frame=requestAnimationFrame(tick);
}
function resetRound(){roundId=crypto.randomUUID();motion=createMotionState(roundId,motionPolicy);packet=null;disconnected=false;roundSource=null;testSource=diagnosticReplayRound()?'video':null;manualCount=0;motionNotice='';roundTiming={wallMs:0,creditedMs:0,stalledMs:0,callbacks:0};}
// Primitive, read-only diagnostics. This does not inject a clock or drive input.
window.togetherMoveTiming=()=>({...roundTiming,roundSeconds:roundSeconds(),paused});
async function cloudAction(action){
  if(screen!=='cloud'||!cloudAvailable()||cloudGarden.snapshot().busy)return;
  if(action==='cloud-delete'){cloudDeleteConfirm=true;cloudStatus='Delete cloud copy? Your local garden stays.';render('cloud-delete-cancel');return;}
  if(action==='cloud-delete-cancel'){cloudDeleteConfirm=false;cloudStatus='';render('cloud-backup');return;}
  if(!['cloud-backup','cloud-restore','cloud-delete-confirm'].includes(action)||(action==='cloud-delete-confirm'&&!cloudDeleteConfirm))return;
  const requestRevision=++revision,context={active:false,source:simulatedSource()||'confirmed'};
  cloudStatus=action==='cloud-backup'?'Backing up…':action==='cloud-restore'?'Restoring blooms…':'Deleting cloud copy…';
  cloudDeleteConfirm=false;
  try{
    const pending=action==='cloud-backup'?cloudGarden.backup(progress,context):action==='cloud-restore'?cloudGarden.restore(context):cloudGarden.remove(context);
    render('home');
    const record=await pending;
    if(screen!=='cloud'||revision!==requestRevision)return;
    if(action==='cloud-restore'){progress=mergeGardenProgress(progress,record.progress);save();cloudStatus=storageFailed?'Cloud copy read, but this device could not save it.':'Blooms restored. Current visit unchanged.';}
    else cloudStatus=action==='cloud-backup'?'Garden backed up.':'Cloud copy deleted. Local garden kept.';
  }catch(error){if(screen!=='cloud'||revision!==requestRevision)return;cloudStatus=cloudGardenErrorMessage(error);}
  render('cloud-backup');
}
function act(action){
  if(action.startsWith('cloud-'))return cloudAction(action);
  if(action==='cloud'&&!cloudAvailable())return;
  if(action==='return'){back();return;}
  if(action==='manual-count'&&(screen!=='play'||cameraMode()||paused||manualCount>=6))return;
  if(action==='finish-moment'){
    if(screen==='play'&&!paused&&!cameraMode()&&manualCount===6){screen='check';revision++;render();}
    return;
  }
  if(screen==='cloud'){
    if(cloudGarden?.snapshot().busy)cloudStatus=cloudGardenErrorMessage({code:'cancelled'});
    cloudGarden?.cancel();cloudDeleteConfirm=false;
  }
  revision++;
  if(action==='home'){screen='home';inputMode='manual';paused=false;}
  else if(action==='cloud'){screen='cloud';cloudStatus='';cloudDeleteConfirm=false;}
  else if(action==='help'){if(screen!=='help'){returnScreen=screen;returnFocus=document.activeElement?.dataset?.action||'';}screen='help';}
  else if(action==='setup'){selected=Math.max(0,challenges.findIndex(c=>!journeyCompleted.includes(c.id)));inputMode='manual';screen='setup';}
  else if(action.startsWith('choose:')){selected=Number(action.split(':')[1]);inputMode='manual';screen='setup';}
  else if(action.startsWith('mode:'))mode=action.split(':')[1];
  else if(action.startsWith('input:')){inputMode=action.split(':')[1];if(cameraMode())motionClient.start();}
  else if(action==='start'){elapsed=0;paused=false;resetRound();screen='play';if(cameraMode())motionClient.start();}
  else if(action==='manual-count')manualCount=Math.min(6,manualCount+1);
  else if(action==='pause'){paused=!paused;if(!paused)motionNotice='';}
  else if(action==='switch'){mode=mode==='seated'?'standing':'seated';paused=true;}
  else if(action==='manual'){inputMode='manual';paused=true;}
  else if(action==='complete'){if(screen!=='check')return;finish();return;}
  else if(action==='next'||action==='skip'){selected=(selected+1)%3;inputMode='manual';elapsed=0;paused=false;screen='setup';}
  else if(action==='return-harvest'){
    if(journeyCompleted.length!==3||harvestClaimed)return;
    // The visit ledger contains only real/self-reported completed moments.
    // A later diagnostic must not hide an already-earned, unclaimed harvest.
    inputMode='manual';testSource=null;roundSource=null;packet=null;screen='celebrate';
  }
  else if(action==='harvest'){
    if(screen!=='celebrate'||simulatedSource()||journeyCompleted.length!==3||harvestClaimed)return;
    harvestClaimed=true;progress={...progress,sessions:Math.min(Number.MAX_SAFE_INTEGER,progress.sessions+1)};save();screen='harvest';
  }
  else if(action==='restart'){journeyCompleted=[];harvestClaimed=false;selected=0;inputMode='manual';screen='setup';}
  render(action.startsWith('mode:')||action.startsWith('input:')?action:'');
}
function back(){
  if(screen==='cloud'){cloudGarden?.cancel();cloudDeleteConfirm=false;}
  if(screen==='play'){
    if(paused){screen='home';inputMode='manual';paused=false;}
    else paused=true;
    revision++;render();
  }
  else if(screen==='help'){screen=returnScreen;if(screen==='home')inputMode='manual';if(screen==='play')paused=true;revision++;render(screen==='play'?'pause':returnFocus);}
  else if(screen!=='home'){screen='home';inputMode='manual';revision++;render();}
  else return false;
  return true;
}
window.togetherMoveKey=(key)=>{
  if(key==='Back')return back();
  if(key==='MediaPlayPause'){if(screen==='play')act('pause');return true;}
  document.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));return true;
};
window.togetherMoveSuspend=()=>{if(screen==='play'){paused=true;revision++;render();}};
document.addEventListener('visibilitychange',()=>{if(document.hidden)window.togetherMoveSuspend();});
document.addEventListener('keydown',e=>{
  if(e.key.startsWith('Arrow')){e.preventDefault();const list=[...root.querySelectorAll('button')].filter(b=>!b.disabled);(nearest(document.activeElement,list,e.key)||document.activeElement)?.focus();}
  else if(e.key==='Enter'){if(e.repeat)return;e.preventDefault();document.activeElement?.click();}
  else if(e.key==='Escape'||e.key==='Backspace'){e.preventDefault();back();}
  else if(e.key===' '||e.key==='MediaPlayPause'){e.preventDefault();if(screen==='play')act('pause');}
});
window.addEventListener('pagehide',()=>{revision++;cloudGarden?.cancel();previewClient.stop();motionClient.stop();});
render();
