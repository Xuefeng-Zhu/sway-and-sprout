import './style.css';
import {challenges,normalizeProgress,complete,phaseAt,nearest} from './model.js';
import {createMotionState,acceptMotionEvent,createMotionClient} from './motion.js';
import {createPreviewClient} from './preview.js';
import {sunshineMarkup,updateSunshine,updateCameraPreview} from './motion-view.js';

const root=document.querySelector('#app');
let saved;
try{saved=JSON.parse(localStorage.getItem('togethermove.v1'));}catch{}
let progress=normalizeProgress(saved),screen='home',mode='seated',selected=0;
let elapsed=0,paused=false,last=0,frame=0,storageFailed=false,returnScreen='home';
let inputMode='manual',roundId=crypto.randomUUID(),revision=0;
let motion=createMotionState(roundId),packet=null,disconnected=false;
let roundSource=null,streamId=null,motionNotice='';
const clientId=crypto.randomUUID();
const cameraMode=()=>inputMode==='camera'&&challenges[selected].id==='sun';
const cameraActive=()=>cameraMode()&&screen==='play'&&!paused&&!motion.completed;
const videoRound=()=>roundSource==='video'||packet?.source==='video';
const motionClient=createMotionClient({
  getContext:()=>({clientId,roundId,revision,active:cameraActive(),mode,after:motion.lastSeq}),
  onPacket(value){
    if(cameraMode()&&screen==='play'&&((roundSource&&roundSource!==value.source)||(streamId&&value.streamId&&streamId!==value.streamId))){
      resetRound();elapsed=0;paused=true;revision++;packet=value;streamId=value.streamId||null;
      motionNotice='The input service changed. This input round was reset. Resume with both arms resting.';
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
    if(!cameraMode()||screen==='celebrate')motionClient.stop();
  },
  onError(){disconnected=true;previewClient.stop('unavailable');updateSunshine({motion,packet,paused,disconnected,notice:motionNotice,revision});if(!cameraMode()||screen==='celebrate')motionClient.stop();},
});
const previewClient=createPreviewClient({
  getContext:()=>({clientId,roundId,revision,active:cameraActive(),mode,after:motion.lastSeq}),
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
  root.innerHTML=`<div class="app ${screen}${cameraMode()?' camera-mode':''}"><header><div class="brand" aria-label="Sway &amp; Sprout">Sway <span>&amp; Sprout</span><i aria-hidden="true">✦</i></div><nav>${button('Garden','home',screen==='home'?'active':'')}${button('How to play','help')}</nav></header><main>${content}</main><footer><span><kbd>↔ ↕</kbd> Navigate</span><span><kbd>OK</kbd> Select</span><span><kbd>↶</kbd> Back</span><span><kbd>II</kbd> Pause</span><span class="privacy">Optional camera. Local on this Mac.</span></footer></div>`;
  root.querySelectorAll('button').forEach(b=>b.onclick=()=>act(b.dataset.action));
  (root.querySelector('[autofocus]')||root.querySelector('main button'))?.focus();
}
function inputChoices(){
  if(challenges[selected].id!=='sun')return '';
  return `<fieldset class="input-choices"><legend>HOW WOULD YOU LIKE TO PLAY?</legend><div class="input-options">${button('<b>Manual play</b><small>Follow along, then confirm</small>','input:manual',inputMode==='manual'?'selected':'',`aria-pressed="${inputMode==='manual'}"`)}${button('<b>Camera sunshine</b><small>One player · OpenCV 5 on this Mac</small>','input:camera',inputMode==='camera'?'selected':'',`aria-pressed="${inputMode==='camera'}"`)}</div><p class="camera-setup-note">${inputMode==='camera'?'Camera is off. One person only: face the camera with both shoulders and wrists visible. Rest both arms below your shoulders, with hands clear of your face. After Start, wait for Ready, then follow the cue. Frames stay on this Mac; nothing is recorded.':'Manual play uses your own confirmation. No camera is needed.'}</p></fieldset>`;
}
function render(){
  // Remove the current image and invalidate requests before replacing the DOM.
  previewClient.stop();
  cancelAnimationFrame(frame);
  if(screen==='home'){
    shell(`<section class="hero"><div class="intro"><h1>A little movement.<br>A lot of together.</h1><p>Every move helps your garden grow.</p>${button('Let’s grow <span>→</span>','setup','primary','autofocus')}<p class="subtle">Seated or standing. Everyone belongs.</p></div><div class="garden-status">${progress.completed.length?`${progress.completed.length} of 3 moments grown`:'Your next little adventure'}</div></section><section class="challenge-list" aria-label="Three garden moments">${challenges.map((c,i)=>button(`<span class="number">0${i+1}</span><strong>${c.name.replace(/ (garden|sunshine|rain)$/,'<br>$1')}</strong><span class="symbol">${c.symbol}</span><small>${progress.completed.includes(c.id)?'✓ Grown together':c.id==='sun'?'30 seconds · Camera play available':'30 seconds · Your own pace'}</small>`,`choose:${i}`,'challenge',`style="--accent:${c.color}"`)).join('')}</section>`);
  }else if(screen==='setup'){
    shell(`<section class="panel setup-panel"><div><p class="step">MAKE YOURSELF AT HOME</p><h1>Move your way.</h1><p>Choose a starting position. Everyone can adapt<br class="desktop"> any movement, rest, or simply watch along.</p><div class="choices">${button('<b>Seated</b><small>Comfortably in your chair</small>','mode:seated',mode==='seated'?'selected':'',`aria-pressed="${mode==='seated'}"`)}${button('<b>Standing</b><small>A little room around you</small>','mode:standing',mode==='standing'?'selected':'',`aria-pressed="${mode==='standing'}"`)}</div>${inputChoices()}<p class="safety">Keep movements comfortable. Clear a little space.<br>Rest whenever you need. Manual play is always available.</p>${button(`Start ${challenges[selected].name.toLowerCase()} →`,'start','primary','autofocus')}</div><aside class="setup-art"><span>✿</span><h2>One little move.<br>A brighter garden.</h2><p>About 2 minutes for all three moments.<br>No accounts. No cloud processing.</p></aside></section>`);
  }else if(screen==='play'){
    const c=challenges[selected],camera=cameraMode();
    shell(`<section class="play-panel" style="--accent:${c.color}"><div class="instruction"><p class="step">MOMENT ${selected+1} OF 3 · ${mode.toUpperCase()}${camera?'<span id="motion-input-mode"> · CAMERA</span>':' · MANUAL'}</p><h1>${c.name}</h1><p id="${camera?'camera-cue':'cue'}" class="cue">${camera?'Start with both arms resting.':c[mode][phaseAt(elapsed)]}</p><div class="timer"><div class="track"><div id="bar"></div></div><span id="time"></span></div><p class="subtle">${camera?'Six alternating raises. Left, rest, right, rest. Your own pace.':'Go at your own pace. Small movements count.'}</p><div class="actions">${button(paused?'Resume →':'Pause Ⅱ','pause','primary','autofocus')}${button('Change position','switch')}${camera?button('Use manual play','manual'):''}${button('Back to garden','home')}</div></div>${camera?sunshineMarkup():`<div class="motion-art ${c.id}"><div class="halo"></div><span>${c.symbol}</span><p>Together is the whole point.</p></div>`}</section>${paused?'<div class="pause-note" role="status">Taking a breather. Resume whenever you’re ready.</div>':''}`);
    updateTimer();
    if(camera)updateSunshine({motion,packet,paused,disconnected,notice:motionNotice,revision});
    if(!paused){last=performance.now();frame=requestAnimationFrame(tick);}
  }else if(screen==='check'){
    const c=challenges[selected],camera=cameraMode();
    if(videoRound()){
      shell(`<section class="center-panel"><div class="bloom" style="color:${c.color}">${c.symbol}</div><p class="step">VIDEO REPLAY · NO CAMERA · ${motion.count} OF 6 SIMULATED RAYS</p><h1>Replay finished.</h1><p>These rays came from a local video file.</p><div class="actions">${button('View replay result','complete','primary','autofocus')}${button('Replay again','start')}${button('Back to garden','home')}</div><p class="subtle">Replay results do not change your saved garden.</p></section>`);
      syncPreview();return;
    }
    shell(`<section class="center-panel"><div class="bloom" style="color:${c.color}">${c.symbol}</div><p class="step">${camera?`${motion.count} OF 6 CAMERA RAYS · MANUAL CONFIRMATION BELOW`:'YOUR MOMENT, YOUR SAY'}</p><h1>How did that feel?</h1><p>${camera?'Every little move belongs. Try camera sunshine again,<br>or use your own confirmation to grow this moment.':'Only you know what you tried.<br>Choose “We joined in” to add this moment to your garden.'}</p><div class="actions">${button(camera?'Manual: we joined in ✦':'We joined in ✦','complete','primary','autofocus')}${button('Try it again','start')}${button('Skip this moment','skip')}</div><p class="subtle">${camera?'Manual confirmation is self-reported. It does not count as a camera recognition result.':'Manual play uses self-reported participation.'}</p></section>`);
  }else if(screen==='celebrate'){
    if(videoRound()){
      shell(`<section class="center-panel celebration"><div class="bloom" style="color:#ffcd70">☀</div><p class="step">VIDEO REPLAY · NO CAMERA · ${motion.count} OF 6 SIMULATED RAYS</p><h1>Replay result.</h1><p>Local video frames produced these simulated rays.</p><div class="actions">${button('Replay again →','start','primary','autofocus')}${button('Back to garden','home')}</div><p class="subtle">Your saved garden is unchanged. This replay does not verify live human camera recognition.</p></section>`);
      syncPreview();return;
    }
    const all=progress.completed.length===3;
    shell(`<section class="center-panel celebration"><div class="celebration-blooms" aria-hidden="true">${challenges.map(c=>`<span style="color:${c.color};opacity:${progress.completed.includes(c.id)?1:.2}">${c.symbol}</span>`).join('')}</div><p class="step">${progress.completed.length} OF 3 MOMENTS GROWN${cameraMode()&&motion.completed?` · ${roundSource==='synthetic'?'SYNTHETIC TEST':'CAMERA SUNSHINE'}`:''}</p><h1>${all?'Look what you grew.':'A little more life.'}</h1><p>${all?'Three little moments. One lovely thing you did together.':'Your shared garden grows with every moment you join.'}</p><div class="actions">${button(all?'Grow together again →':'Next moment →',all?'restart':'next','primary','autofocus')}${button('Back to garden','home')}</div><p class="subtle">${storageFailed?'Progress could not be saved on this device.':'Your garden is saved on this device.'}</p></section>`);
  }else if(screen==='help'){
    shell(`<section class="panel help-panel"><h1>A garden for everyone.</h1><div class="help-grid"><div><h2>1. Get comfortable</h2><p>Pick seated or standing. Adapt your movement, rest, or watch along. Manual play works without a camera.</p></div><div><h2>2. Catch sunshine</h2><p>Optional camera play is for one person. Rest both arms below your shoulders and wait for Ready. Raise the indicated hand, then rest both arms again. Visible markers alone do not mean Ready. Pause with Space or your remote.</p></div><div><h2>3. Keep it local</h2><p>OpenCV 5 processes camera frames on this Mac. The live view shows the same camera and its shoulder / wrist markers. Frames are not saved or uploaded; pausing clears the view and stops capture.</p></div></div><p class="safety">This is playful entertainment, not exercise instruction or medical advice. Stop if uncomfortable.<br>Camera play needs the local sidecar. Manual confirmation is always available.</p>${button('Back to garden','home','primary','autofocus')}</section>`);
  }
  syncPreview();
}
function updateTimer(){
  const c=challenges[selected];
  if(!cameraMode())document.querySelector('#cue').textContent=c[mode][phaseAt(elapsed)];
  document.querySelector('#time').textContent=`${Math.max(0,Math.ceil(c.duration-elapsed))}s`;
  document.querySelector('#bar').style.width=`${elapsed/c.duration*100}%`;
  document.querySelector('.motion-art')?.classList.toggle('still',paused);
  document.querySelector('.sunshine-garden')?.classList.toggle('still',paused);
}
function finish(){const next=complete(progress,challenges[selected].id,videoRound()?'video':roundSource||packet?.source||'manual');if(next!==progress){progress=next;save();}screen='celebrate';revision++;render();}
function tick(now){
  if(screen!=='play'||paused)return;
  elapsed+=Math.min((now-last)/1000,.25);last=now;
  if(elapsed>=challenges[selected].duration){
    if(cameraMode()&&motion.completed){finish();return;}
    screen='check';revision++;render();return;
  }
  updateTimer();frame=requestAnimationFrame(tick);
}
function resetRound(){roundId=crypto.randomUUID();motion=createMotionState(roundId);packet=null;disconnected=false;roundSource=null;motionNotice='';}
function act(action){
  revision++;
  if(action==='home'){screen='home';inputMode='manual';paused=false;}
  else if(action==='help'){returnScreen=screen;screen='help';}
  else if(action==='setup'){selected=0;inputMode='manual';screen='setup';}
  else if(action.startsWith('choose:')){selected=Number(action.split(':')[1]);inputMode='manual';screen='setup';}
  else if(action.startsWith('mode:'))mode=action.split(':')[1];
  else if(action.startsWith('input:')){inputMode=action.split(':')[1];if(cameraMode())motionClient.start();}
  else if(action==='start'){elapsed=0;paused=false;resetRound();screen='play';if(cameraMode())motionClient.start();}
  else if(action==='pause'){paused=!paused;if(!paused)motionNotice='';}
  else if(action==='switch'){mode=mode==='seated'?'standing':'seated';paused=true;}
  else if(action==='manual'){inputMode='manual';paused=true;}
  else if(action==='complete'){if(screen!=='check')return;finish();return;}
  else if(action==='next'||action==='skip'){selected=(selected+1)%3;inputMode='manual';elapsed=0;paused=false;screen='setup';}
  else if(action==='restart'){progress={completed:[],sessions:progress.sessions+1};save();selected=0;inputMode='manual';screen='setup';}
  render();
}
function back(){
  if(screen==='play'){paused=true;revision++;render();}
  else if(screen==='help'){screen=returnScreen==='play'?'play':'home';if(screen==='home')inputMode='manual';paused=true;revision++;render();}
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
  if(e.key.startsWith('Arrow')){e.preventDefault();const list=[...root.querySelectorAll('button')];(nearest(document.activeElement,list,e.key)||document.activeElement)?.focus();}
  else if(e.key==='Enter'){if(e.repeat)return;e.preventDefault();document.activeElement?.click();}
  else if(e.key==='Escape'||e.key==='Backspace'){e.preventDefault();back();}
  else if(e.key===' '||e.key==='MediaPlayPause'){e.preventDefault();if(screen==='play')act('pause');}
});
window.addEventListener('pagehide',()=>{previewClient.stop();motionClient.stop();});
render();
