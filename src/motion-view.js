import {calibrationFeedback} from './calibration.js';

const messages = {
  waiting:'Connecting to your local camera…',
  tracking:'You’re in view. Follow the sunshine.',
  neutral:'Rest both arms, then follow the next sunshine cue.',
  hold:'Lovely. Hold your hand there for a moment…',
  'low-confidence':'I can’t see both shoulders and wrists clearly. Adjust your position, or use manual play.',
  'no-person':'Step into view with your shoulders and hands visible.',
  'camera-error':'Camera unavailable. Manual play is always here.',
  disconnected:'Camera connection lost. Your sunshine is safe. Reconnect or use manual play.',
  paused:'Camera input paused. Rest whenever you like.',
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

export function sunshineMarkup(){
  return `<aside class="sunshine-garden" aria-label="Live sunshine garden" data-motion-count="0">
    <div class="camera-badge" id="camera-source">LOCAL CAMERA · CONNECTING</div>
    <section class="camera-preview" data-preview-state="off" aria-label="Camera framing and movement feedback">
      <div class="preview-heading"><b id="preview-title">Your camera view</b><span id="preview-state">Off</span></div>
      <div class="preview-viewport">
        <img id="camera-preview-image" alt="Live local camera view with shoulder, arm, and wrist markers" hidden>
        <div class="preview-placeholder" id="preview-placeholder"><b id="preview-placeholder-title">Camera is off</b><span id="preview-placeholder-detail">Start or resume to see your shoulders and both hands.</span></div>
      </div>
      <div class="preview-confidence"><span>Landmark confidence <b id="preview-confidence">—</b></span><meter id="preview-confidence-meter" min="0" max="1" value="0" aria-label="Landmark confidence" aria-valuetext="Not available"></meter></div>
      <div class="preview-visibility" aria-label="Visible landmarks">${[['leftShoulder','L shoulder'],['rightShoulder','R shoulder'],['leftWrist','L wrist'],['rightWrist','R wrist']].map(([key,label])=>`<span data-landmark="${key}">${label}<b>—</b></span>`).join('')}</div>
      <p id="preview-movement" class="preview-movement" role="status">Preview off · no camera image</p>
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
    <div class="sunshine-details"><div class="sunshine-caption"><span class="sunshine-count"><b id="sunshine-count">0</b><span> / 6 rays</span></span><span id="sunshine-next">Left hand next</span></div>
    <div class="signal-status" id="motion-status" role="status" aria-live="polite">Connecting to your local camera…</div></div>
    </div>
    <p class="camera-local-note">Unmirrored · L/R are your left/right.<br>Frames stay on this Mac. Nothing is recorded.</p>
  </aside>`;
}

const previewOffMessages={
  off:['Camera is off','Start or resume to see your shoulders and both hands.'],
  paused:['Camera paused','Your camera is off. Resume when you’re ready.'],
  complete:['Six rays gathered','Camera is off. Enjoy your sunshine.'],
  waiting:['Opening your local view…','Keep both shoulders and wrists inside the view.'],
  synthetic:['Synthetic test · no camera','Test events have no real camera preview.'],
  unavailable:['Preview unavailable','The local camera is not providing a current image.'],
  expired:['Camera stopped','This camera window ended. Start a new round when you’re ready.'],
  'camera-error':['Camera unavailable','Check camera permission or use manual play.'],
  unauthorized:['Preview unavailable','The local camera is connected to another round.'],
  stale:['Waiting for a fresh frame…','Your last camera image has been cleared.'],
  stopped:['Camera stopped','No camera image is being shown.'],
};

export function updateCameraPreview({preview,reason='off',expected='left',source}={}){
  const panel=document.querySelector('.camera-preview');
  if(!panel)return;
  const image=panel.querySelector('#camera-preview-image');
  const placeholder=panel.querySelector('#preview-placeholder');
  const video=(preview?.source||source)==='video';
  const live=preview?.available===true&&['camera','video'].includes(preview.source);
  const state=live?'live':preview?.source==='synthetic'?'synthetic':preview?.status||reason;
  panel.dataset.previewState=state;
  const title=panel.querySelector('#preview-title');
  if(title)title.textContent=video?'Local video replay':'Your camera view';
  panel.querySelector('#preview-state').textContent=video?'Replay · no camera':live?'Live · local':state==='waiting'||state==='stale'?'Connecting':state==='synthetic'?'Test · no camera':'Off';
  image.alt=video?'Local video replay with shoulder, arm, and wrist markers':'Live local camera view with shoulder, arm, and wrist markers';
  image.hidden=!live;
  placeholder.hidden=live;
  if(live){
    image.src=preview.jpeg;
    image.width=preview.width;
    image.height=preview.height;
  }else{
    image.removeAttribute('src');
    const [title,detail]=video?[state==='complete'?'Replay complete':state==='paused'?'Video replay paused':'Video replay off','No camera is active. Replay frames are local.']:previewOffMessages[state]||previewOffMessages.unavailable;
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
  let movement='Preview off · no camera image';
  if(live&&video){
    movement=['tracking','neutral','hold'].includes(preview.status)?
      'Video frame visibility · follow the current replay calibration cue.':
      `Video replay · ${videoMessages[preview.status]||'Local file frames only.'}`;
  }else if(live){
    movement=preview.status==='no-person'?'Move into view with shoulders and both wrists visible.':
      preview.status==='low-confidence'?'Bring both shoulders and wrists into view.':
      Object.values(preview.visibility).every(Boolean)?
        'Landmarks visible · wait for the calibration cue before raising.':
        'Make both shoulders and wrists clear in the view.';
  }else if(state==='synthetic')movement='Synthetic test only · no human camera result';
  else if(state==='waiting'||state==='stale')movement='Waiting for the local inference camera…';
  else if(state==='paused')movement='Paused · camera and preview off';
  else if(state==='complete')movement='Six rays complete · camera and preview off';
  else if(state==='unavailable'||state==='camera-error')movement='No current camera image · manual play is available';
  if(video&&!live)movement=state==='complete'?'Replay complete · simulated rays · no camera':'Video replay off · no camera';
  const message=panel.querySelector('#preview-movement');
  if(message.textContent!==movement)message.textContent=movement;
}

function currentPacket(motion,packet,revision){
  return packet?.runtime?.verified===true&&packet.active===true&&
    (!motion.roundId||packet.roundId===motion.roundId)&&
    (revision===undefined||packet.revision===revision);
}

function packetFeedback(motion,packet,revision){
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
  document.querySelector('#sunshine-next').textContent=motion.completed?'Your sunshine is gathered!':`${motion.expected==='left'?'Left':'Right'} hand next`;
  garden.querySelectorAll('[data-ray]').forEach((ray,i)=>ray.classList.toggle('collected',i<motion.count));
  const synthetic=packet?.source==='synthetic',video=packet?.source==='video';
  const badge=document.querySelector('#camera-source');
  badge.textContent=video?'VIDEO REPLAY · NO CAMERA':synthetic?'SYNTHETIC TEST · NO CAMERA':packet?.source==='camera'?'LOCAL CAMERA · OPENCV 5':'LOCAL CAMERA · CONNECTING';
  const inputLabel=document.querySelector('#motion-input-mode');
  if(inputLabel)inputLabel.textContent=video?' · VIDEO REPLAY · NO CAMERA':synthetic?' · SYNTHETIC TEST · NO CAMERA':' · CAMERA';
  garden.dataset.motionSource=packet?.source||'waiting';
  let status=paused?'Camera input paused. Rest whenever you like.':motion.completed?'Six rays! Enjoy your garden until the timer ends.':messages[disconnected?'disconnected':packet?.status]||messages.waiting;
  if(video)status=motion.completed?'Six simulated rays from this video. Garden progress is unchanged.':videoMessages[paused?'paused':disconnected?'disconnected':packet?.status]||videoMessages.waiting;
  if(packet?.runtime?.verified===false)status=video?'OpenCV 5 runtime is not verified. Video replay progress is unavailable.':'OpenCV 5 runtime is not verified. Camera progress is unavailable; use manual play.';
  const feedback=!paused&&!disconnected&&!motion.completed?packetFeedback(motion,packet,revision):null;
  if(feedback)status=`${video?'Video replay calibration':'Calibration'}: ${feedback.label}. ${feedback.detail}`;
  if(synthetic)status=`Synthetic input — ${status}`;
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
