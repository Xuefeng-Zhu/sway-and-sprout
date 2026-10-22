import {calibrationFeedback} from './calibration.js';
import {validMotionRuntime} from './runtime.js';

const messages = {
  waiting:'Connecting…',
  tracking:'You’re in view. Follow the sunshine.',
  neutral:'Rest both arms, then follow the next sunshine cue.',
  hold:'Lovely. Hold your hand there for a moment…',
  'low-confidence':'I can’t see both shoulders and wrists clearly. Adjust your position, or use manual play.',
  'no-person':'Step into view with your shoulders and hands visible.',
  'camera-error':'Camera unavailable. Use manual play.',
  disconnected:'Camera connection lost. Use manual play.',
  paused:'Camera off. Resume when ready.',
};
const videoMessages={
  waiting:'Waiting for the next video frame.',
  tracking:'Video landmarks are armed. Watching for the next raise.',
  neutral:'Waiting for both arms in the video to rest.',
  hold:'The expected arm is holding in the video.',
  'low-confidence':'Video shoulders and wrists are not clear enough.',
  'no-person':'No person detected in this video frame.',
  'camera-error':'Local video replay is unavailable.',
  disconnected:'Local video replay connection lost.',
  paused:'Local video replay is paused.',
};
const activityMessages={
  waiting:'Finding your view…',
  ready:'Ready when you are.',
  tracking:'Small moves welcome.',
  neutral:'Ready when you are.',
  hold:'Small moves count.',
  'low-confidence':'Keep a hand or upper body in view.',
  'no-person':'Keep one person in view.',
  'camera-error':'Camera unavailable. Use manual play.',
};

export function sunshineMarkup({policy='strict'}={}){
  const activity=policy==='activity';
  return `<aside class="sunshine-garden" aria-label="Live sunshine garden" data-motion-count="0">
    <div class="camera-badge" id="camera-source">LOCAL CAMERA · CONNECTING</div>
    <section class="camera-preview" data-preview-state="off" aria-label="Camera framing and movement feedback">
      <div class="preview-heading"><b id="preview-title">Preview</b><span id="preview-state">Off</span></div>
      <div class="preview-viewport">
        <img id="camera-preview-image" alt="Live local camera view with shoulder, arm, and wrist markers" hidden>
      <div class="preview-placeholder" id="preview-placeholder"><b id="preview-placeholder-title">Camera off</b><span id="preview-placeholder-detail">${activity?'Start or resume to continue.':'Start or resume to see your shoulders and both hands.'}</span></div>
      </div>
      <div class="preview-confidence"${activity?' hidden style="display:none"':''}><span>Landmark confidence <b id="preview-confidence">—</b></span><meter id="preview-confidence-meter" min="0" max="1" value="0" aria-label="Landmark confidence" aria-valuetext="Not available"></meter></div>
      <div class="preview-visibility" aria-label="Visible landmarks"${activity?' hidden':''}>${[['leftShoulder','L shoulder'],['rightShoulder','R shoulder'],['leftWrist','L wrist'],['rightWrist','R wrist']].map(([key,label])=>`<span data-landmark="${key}">${label}<b>—</b></span>`).join('')}</div>
      <p id="preview-movement" class="preview-movement" role="note"></p>
    </section>
    <div class="sunshine-progress">
    <div class="sunshine-scene" aria-hidden="true">
      <svg class="garden-svg" viewBox="0 0 400 370">
        <defs><radialGradient id="sun-glow"><stop stop-color="#ffd985" stop-opacity=".32"/><stop offset="1" stop-color="#ffd985" stop-opacity="0"/></radialGradient></defs>
        <circle cx="200" cy="125" r="120" fill="url(#sun-glow)"/>
        <g class="sun-rays">${Array.from({length:6},(_,i)=>`<circle data-ray="${i}" cx="${200+85*Math.cos((i*60-90)*Math.PI/180)}" cy="${125+85*Math.sin((i*60-90)*Math.PI/180)}" r="10"/>`).join('')}</g>
        <g class="living-sun"><circle cx="200" cy="125" r="46"/><path d="M184 128q16 18 32 0"/><circle class="sun-eye" cx="185" cy="116" r="3"/><circle class="sun-eye" cx="215" cy="116" r="3"/></g>
        <path class="garden-stem" d="M200 327 Q178 286 200 246"/>
        <path class="garden-leaf leaf-left" d="M195 300Q143 300 148 262Q184 260 195 300"/>
        <path class="garden-leaf leaf-right" d="M194 282Q242 286 250 244Q212 243 194 282"/>
        <g class="garden-flower"><path d="M200 252C154 252 163 216 185 229C167 199 204 190 207 223C224 195 253 219 225 237C259 236 245 269 216 251C216 281 181 280 190 253Z"/><circle cx="205" cy="241" r="11"/></g>
        <ellipse cx="200" cy="333" rx="100" ry="12" fill="#183c2e"/><path d="M108 333Q128 308 146 333M250 333Q270 312 291 333" fill="none" stroke="#759a58" stroke-width="3"/>
      </svg>
      <span class="sunshine-pop" id="sunshine-pop"></span>
    </div>
    <div class="sunshine-details"><div class="sunshine-caption"><span class="sunshine-count"><b id="sunshine-count">0</b><span> / 6 rays</span></span><span id="sunshine-next"${activity?' hidden':''}>${activity?'':'Left hand next'}</span></div>
    <div class="signal-status" id="motion-status" role="status" aria-live="polite">Connecting…</div></div>
    </div>
    <p class="camera-local-note">${activity?'':'L/R are your left/right.<br>'}Frames stay on this device. No recording.</p>
  </aside>`;
}

const previewOffMessages={
  off:['Camera is off','Start or resume to see your shoulders and both hands.'],
  paused:['Camera paused','Camera off. Resume when ready.'],
  complete:['Six rays gathered','Camera off.'],
  waiting:['Opening your local view…','Keep both shoulders and wrists inside the view.'],
  synthetic:['No camera preview','Simulated input only.'],
  unavailable:['Preview unavailable','No current image.'],
  expired:['Camera stopped','Round ended. Start a new round.'],
  'camera-error':['Camera unavailable','Check camera permission or use manual play.'],
  unauthorized:['Preview unavailable','Connected to another round.'],
  stale:['Refreshing preview…','Last image cleared.'],
  stopped:['Camera stopped','No current image.'],
};

export function updateCameraPreview({preview,reason='off',expected='left',source}={}){
  const panel=document.querySelector('.camera-preview');
  if(!panel)return;
  const image=panel.querySelector('#camera-preview-image');
  const placeholder=panel.querySelector('#preview-placeholder');
  const video=(preview?.source||source)==='video';
  const activity=expected==='any'||preview?.policy==='activity';
  const live=preview?.available===true&&['camera','video'].includes(preview.source);
  const state=live?'live':preview?.source==='synthetic'?'synthetic':preview?.status||reason;
  panel.dataset.previewState=state;
  const title=panel.querySelector('#preview-title');
  if(title)title.textContent=video?'Replay preview':'Preview';
  panel.querySelector('#preview-state').textContent=video?'Replay':live?'Live':state==='waiting'||state==='stale'?'Connecting':state==='synthetic'?'Test':'Off';
  image.alt=video?'Local video replay with shoulder, arm, and wrist markers':'Live local camera view with shoulder, arm, and wrist markers';
  image.hidden=!live;
  placeholder.hidden=live;
  if(live){
    image.src=preview.jpeg;
    image.width=preview.width;
    image.height=preview.height;
  }else{
    image.removeAttribute('src');
    const [title,detail]=video?[state==='complete'?'Replay complete':state==='paused'?'Replay paused':'Replay off','Local file frames only.']:activity&&state==='waiting'?['Opening preview…','Keep a hand or upper body in view.']:activity&&state==='off'?['Camera off','Start or resume to continue.']:previewOffMessages[state]||previewOffMessages.unavailable;
    panel.querySelector('#preview-placeholder-title').textContent=title;
    panel.querySelector('#preview-placeholder-detail').textContent=detail;
  }
  const confidence=live?preview.confidence:0;
  panel.querySelector('#preview-confidence').textContent=live?`${Math.round(confidence*100)}%`:'—';
  const meter=panel.querySelector('#preview-confidence-meter');
  meter.value=confidence;
  meter.setAttribute('aria-valuetext',live?`${Math.round(confidence*100)} percent`:'Not available');
  panel.querySelectorAll('[data-landmark]').forEach(node=>{
    const visible=live&&preview.visibility[node.dataset.landmark];
    node.dataset.visible=live?String(visible):'off';
    node.querySelector('b').textContent=live?(visible?'Visible':'Not clear'):'—';
  });
  let movement='';
  if(live&&activity){
    movement=preview.status==='no-person'?'No person in preview.':
      preview.status==='low-confidence'?'View unclear.':'';
  }else if(live&&video){
    movement=['tracking','neutral','hold'].includes(preview.status)?
      'Video frame visibility · follow the current replay calibration cue.':
      `Video replay · ${videoMessages[preview.status]||'Local file frames only.'}`;
  }else if(live){
    movement=preview.status==='no-person'?'Move into view with shoulders and both wrists visible.':
      preview.status==='low-confidence'?'Bring both shoulders and wrists into view.':
      Object.values(preview.visibility).every(Boolean)?
        'Landmarks visible · wait for the calibration cue before raising.':
        'Make both shoulders and wrists clear in the view.';
  }else if(state==='unavailable')movement='Movement input may still work.';
  else if(state==='camera-error')movement='Use manual play.';
  const message=panel.querySelector('#preview-movement');
  if(message.textContent!==movement)message.textContent=movement;
}

function currentPacket(motion,packet,revision){
  return packet?.runtime?.verified===true&&validMotionRuntime(packet.runtime)&&packet.active===true&&
    (!motion.roundId||packet.roundId===motion.roundId)&&
    (revision===undefined||packet.revision===revision)&&
    (packet.policy??'strict')===(motion.policy??'strict');
}

function packetFeedback(motion,packet,revision){
  if(motion.policy==='activity')return null;
  if(!['camera','video','synthetic'].includes(packet?.source)||!currentPacket(motion,packet,revision))return null;
  if(!Object.hasOwn(packet.metrics||{},'calibration'))return null;
  const feedback=calibrationFeedback(packet.metrics.calibration,{expected:motion.expected,
    armed:packet.metrics?.armed===true&&['tracking','neutral','hold'].includes(packet.status)})||
    {label:'Calibration unavailable',detail:'Rest both arms. Waiting for current calibration feedback.',
      cue:'Rest both arms. Wait for current calibration feedback before raising.'};
  if(packet.source==='camera')return feedback;
  const input=packet.source==='video'?'Video replay':'Synthetic test';
  return {label:feedback.label,detail:`${input} input only. No camera is active.`,
    cue:`${input} calibration: ${feedback.label.toLowerCase()}. No camera is active.`};
}

function sunshineCue({motion,packet,paused,disconnected,revision}){
  const video=packet?.source==='video';
  const activity=motion.policy==='activity';
  if(activity){
    if(packet?.source==='synthetic')return paused?'Test paused.':motion.completed?'Simulated rays gathered.':'Simulated activity.';
    if(video)return paused?'Replay paused.':motion.completed?'Simulated rays gathered.':'Video activity replay.';
    if(motion.completed)return 'Six rays gathered.';
    if(paused)return 'Paused.';
    if(disconnected)return 'Camera interrupted.';
    return 'Wave, reach, stretch or sway.';
  }
  if(video&&motion.completed)return 'Replay gathered six simulated rays. No camera was used.';
  if(video&&paused)return 'Video replay paused. No camera is active.';
  if(video&&disconnected)return 'Waiting for the local video replay connection.';
  if(motion.completed)return 'You caught the sunshine. Take a little breather.';
  if(paused)return 'Camera paused. Rest both arms.';
  if(disconnected)return 'Rest both arms while the camera reconnects.';
  const feedback=packetFeedback(motion,packet,revision);
  if(feedback)return feedback.cue;
  // A visible, confident pose has not necessarily rested long enough to arm.
  // A previous round/revision must not reuse its armed cue after a transition.
  const armed=currentPacket(motion,packet,revision)&&packet.metrics?.armed===true&&
    ['tracking','neutral','hold'].includes(packet.status);
  if(!armed)return video?'Video replay: waiting for both arms to rest.':'Rest both arms below your shoulders for a moment.';
  if(video)return packet.status==='hold'?`Video replay: holding the ${motion.expected} hand up.`:`Video replay: waiting for the ${motion.expected} hand raise.`;
  if(packet.status==='hold')return `Hold your ${motion.expected} hand above your shoulder for a moment.`;
  return `Raise your ${motion.expected} hand above your shoulder. Hold briefly.`;
}

export function updateSunshine({motion,packet,paused,disconnected=false,notice='',revision}){
  const garden=document.querySelector('.sunshine-garden');
  if(!garden)return;
  const changed=Number(garden.dataset.motionCount)!==motion.count;
  garden.dataset.motionCount=String(motion.count);
  garden.style.setProperty('--growth',String(motion.count/6));
  document.querySelector('#sunshine-count').textContent=motion.count;
  const activity=motion.policy==='activity';
  document.querySelector('#sunshine-next').textContent=motion.completed?'Your sunshine is gathered!':activity?'Every little move counts':`${motion.expected==='left'?'Left':'Right'} hand next`;
  garden.querySelectorAll('[data-ray]').forEach((ray,i)=>ray.classList.toggle('collected',i<motion.count));
  const synthetic=packet?.source==='synthetic',video=packet?.source==='video';
  const badge=document.querySelector('#camera-source');
  badge.textContent=video?'VIDEO REPLAY · NO CAMERA':synthetic?'SYNTHETIC TEST · NO CAMERA':packet?.source==='camera'?'LOCAL CAMERA':'LOCAL CAMERA · CONNECTING';
  const inputLabel=document.querySelector('#motion-input-mode');
  if(inputLabel)inputLabel.textContent=video?' · VIDEO REPLAY · NO CAMERA':synthetic?' · SYNTHETIC TEST · NO CAMERA':' · CAMERA';
  garden.dataset.motionSource=packet?.source||'waiting';
  let status=paused?'Camera off. Resume when ready.':motion.completed?'Camera off. Finishing this moment…':messages[disconnected?'disconnected':packet?.status]||messages.waiting;
  if(activity&&!paused&&!motion.completed&&!disconnected)status=activityMessages[packet?.status]||activityMessages.waiting;
  if(video)status=motion.completed?'Six simulated rays from this video. Garden progress is unchanged.':videoMessages[paused?'paused':disconnected?'disconnected':packet?.status]||videoMessages.waiting;
  if(video&&activity&&!paused&&!disconnected&&!motion.completed&&packet?.status!=='camera-error')status='Simulated activity. Garden unchanged.';
  if(synthetic&&activity)status=paused?'Test paused.':disconnected?'Test connection lost.':motion.completed?'Saved garden unchanged.':packet?.status==='camera-error'?'Test input unavailable. Saved garden unchanged.':'Simulated input. Garden unchanged.';
  if(packet?.runtime?.verified===false){
    const runtimeLabel=packet.runtime.engine==='litert'?'Local inference runtime':'OpenCV 5 runtime';
    status=video?`${runtimeLabel} is not verified. Video replay progress is unavailable.`:`${runtimeLabel} is not verified. Camera progress is unavailable; use manual play.`;
  }
  const feedback=!paused&&!disconnected&&!motion.completed?packetFeedback(motion,packet,revision):null;
  if(feedback)status=`${video?'Video replay calibration':'Calibration'}: ${feedback.label}. ${feedback.detail}`;
  if(synthetic&&!activity)status=`Synthetic input — ${status}`;
  if(notice)status=notice;
  const node=document.querySelector('#motion-status');
  if(node.textContent!==status)node.textContent=status;
  const cue=document.querySelector('#camera-cue');
  if(cue)cue.textContent=sunshineCue({motion,packet,paused,disconnected,revision});
  if(changed){
    const pop=document.querySelector('#sunshine-pop');
    pop.textContent=video?'+1 replay ray':'+1 sunshine';
    pop.classList.remove('pop');void pop.offsetWidth;pop.classList.add('pop');
  }
}
