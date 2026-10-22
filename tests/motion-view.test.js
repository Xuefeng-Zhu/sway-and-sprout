import {test} from 'node:test';
import assert from 'node:assert/strict';
import {updateSunshine} from '../src/motion-view.js';

const motion=()=>({roundId:'round-current',count:0,target:6,expected:'left',completed:false});
const packet=(overrides={})=>({roundId:'round-current',revision:3,active:true,source:'camera',
  runtime:{opencv:'5.0.0',verified:true},status:'tracking',metrics:{armed:false},...overrides});

// Exercise the real renderer, including its initial call before a packet arrives.
// This supplies only DOM nodes it updates; no camera, network, storage or timers.
function renderFeedback(options={}){
  const nodes=Object.fromEntries(['#sunshine-count','#sunshine-next','#camera-source',
    '#motion-status','#camera-cue'].map(key=>[key,{textContent:''}]));
  const garden={dataset:{motionCount:'0'},style:{setProperty(){}},querySelectorAll:()=>[]};
  const pop={textContent:'',offsetWidth:0,classList:{remove(){},add(){}}};
  const previous=globalThis.document;
  globalThis.document={querySelector:selector=>selector==='.sunshine-garden'?garden:
    selector==='#sunshine-pop'?pop:nodes[selector]};
  try{
    updateSunshine({motion:motion(),packet:packet(),paused:false,disconnected:false,revision:3,...options});
    return {cue:nodes['#camera-cue'].textContent,status:nodes['#motion-status'].textContent,
      badge:nodes['#camera-source'].textContent};
  }finally{globalThis.document=previous;}
}
const renderCue=options=>renderFeedback(options).cue;
const assertRest=cue=>{assert.match(cue,/rest both arms/i);assert.doesNotMatch(cue,/raise your|hold your/i);};

test('initial renderer preserves a rest cue before the first camera packet',()=>{
  assertRest(renderCue({packet:null}));
});

test('high confidence and tracking do not prompt raising before authoritative arming',()=>{
  for(const metrics of [{armed:false},{},undefined]){
    assertRest(renderCue({packet:packet({metrics})}));
  }
});

test('armed tracking and shoulder-height transition keep the next arm raise cue',()=>{
  for(const status of ['tracking','neutral']){
    assert.match(renderCue({packet:packet({status,metrics:{armed:true}})}),/^Raise your left hand/i);
    assert.match(renderCue({motion:{...motion(),expected:'right'},
      packet:packet({status,metrics:{armed:true}})}),/^Raise your right hand/i);
  }
});

test('armed hold gives a hold cue instead of asking for another raise',()=>{
  const cue=renderCue({motion:{...motion(),expected:'right'},
    packet:packet({status:'hold',metrics:{armed:true}})});
  assert.match(cue,/^Hold your right hand/i);assert.doesNotMatch(cue,/raise your/i);
});

test('a scored gesture or lost arming returns to resting before the next arm',()=>{
  assertRest(renderCue({motion:{...motion(),count:1,expected:'right'},
    packet:packet({status:'neutral',metrics:{armed:false}})}));
  assertRest(renderCue({packet:packet({status:'hold',metrics:{armed:false}})}));
});

test('pause and disconnect override an old armed or hold packet',()=>{
  for(const status of ['tracking','hold']){
    const armed=packet({status,metrics:{armed:true}});
    assertRest(renderCue({paused:true,packet:armed}));
    assertRest(renderCue({disconnected:true,packet:armed}));
  }
});

test('waiting, loss, camera errors and unverified input never prompt a raise',()=>{
  for(const status of ['waiting','ready','paused','no-person','low-confidence','camera-error']){
    assertRest(renderCue({packet:packet({status,metrics:{armed:true}})}));
  }
  for(const runtime of [{verified:false},undefined]){
    assertRest(renderCue({packet:packet({runtime,metrics:{armed:true}})}));
  }
});

test('inactive and previous-round packets cannot reuse their armed cue',()=>{
  assertRest(renderCue({packet:packet({active:false,metrics:{armed:true}})}));
  assertRest(renderCue({packet:packet({roundId:'round-old',metrics:{armed:true}})}));
});

test('rapid pause/resume cannot reuse an armed packet from the earlier revision',()=>{
  const armed=packet({status:'hold',metrics:{armed:true}});
  assertRest(renderCue({paused:true,revision:4,packet:armed}));
  assertRest(renderCue({paused:false,revision:5,packet:armed}));
  assert.match(renderCue({revision:5,packet:packet({revision:5,metrics:{armed:true}})}),/^Raise your left hand/i);
});

test('completion gives a breather even with a stale armed packet',()=>{
  const cue=renderCue({motion:{...motion(),count:6,completed:true},paused:true,
    packet:packet({metrics:{armed:true}})});
  assert.match(cue,/caught the sunshine.*breather/i);assert.doesNotMatch(cue,/raise your|hold your/i);
});


test('a claimed verified runtime with invalid identity cannot authorize an armed cue',()=>{
  const litert={engine:'litert',engineVersion:'1.2.0',platform:'android',
    modelSha256:'a'.repeat(64),verified:true};
  for(const runtime of [{verified:true}, {...litert,modelSha256:undefined},
    {...litert,opencv:'5.0.0'}, {...litert,engine:'unknown'}]){
    assertRest(renderCue({packet:packet({runtime,metrics:{armed:true}})}));
  }
});

test('activity cues encourage comfortable movement without sides, height or holding requirements',()=>{
  const move={...motion(),policy:'activity',expected:'any'};
  for(const status of ['waiting','tracking','neutral','hold','ready']){
    const feedback=renderFeedback({motion:move,packet:packet({policy:'activity',expected:'any',status})});
    assert.match(feedback.cue,/\b(?:wave|reach|stretch|sway)\b/i);
    assert.doesNotMatch(feedback.cue,/left hand|right hand|above your shoulder|rest both|hold your/i);
    assert.ok(feedback.status.trim(),'Activity has separate status feedback');
    assert.equal(feedback.badge,'LOCAL CAMERA');
    if(['tracking','hold'].includes(status))assert.match(feedback.status,/\bsmall moves\b/i);
  }
  const initial=renderFeedback({motion:move,packet:null});
  assert.match(initial.cue,/\b(?:wave|reach|stretch|sway)\b/i);
  assert.match(initial.status,/finding.*view|connecting/i);
  assert.doesNotMatch(initial.cue,/left hand|right hand|above your shoulder|rest both|hold your/i);
});

test('activity status preserves visibility and recovery guidance without prescribing a pose',()=>{
  const move={...motion(),policy:'activity',expected:'any'};
  const options=status=>({motion:move,packet:packet({policy:'activity',expected:'any',status})});
  const visibility=renderFeedback(options('low-confidence'));
  assert.match(visibility.status,/hand.*(?:or|\/).*upper body/i);
  assert.doesNotMatch(visibility.status,/both wrists|raise|hold|below your shoulders/i);
  assert.match(renderFeedback(options('no-person')).status,/one person.*view/i);
  const paused=renderFeedback({...options('tracking'),paused:true});
  assert.match(paused.cue,/paused/i);assert.match(paused.status,/camera off/i);assert.match(paused.status,/resume/i);
  const disconnected=renderFeedback({...options('tracking'),disconnected:true});
  assert.match(disconnected.cue,/interrupted|connection/i);
  assert.match(disconnected.status,/connection lost/i);assert.match(disconnected.status,/manual play/i);
  const unavailable=renderFeedback(options('camera-error'));
  assert.match(unavailable.status,/camera unavailable/i);assert.match(unavailable.status,/manual play/i);
  const unverified=renderFeedback({...options('tracking'),packet:packet({policy:'activity',expected:'any',runtime:{opencv:'5.0.0',verified:false}})});
  assert.match(unverified.status,/not verified/i);assert.match(unverified.status,/manual play/i);
  for(const feedback of [visibility,paused,disconnected,unavailable,unverified]){
    assert.doesNotMatch(feedback.cue,/left hand|right hand|above your shoulder|rest both|hold your/i);
  }
});
