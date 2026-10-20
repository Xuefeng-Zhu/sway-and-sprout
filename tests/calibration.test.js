import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sanitizeCalibration,calibrationFeedback} from '../src/calibration.js';
import {createMotionClient} from '../src/motion.js';
import {updateSunshine} from '../src/motion-view.js';

const calibration=(overrides={})=>({reason:'needs-neutral',neutralMs:0,requiredNeutralMs:300,
  holdMs:0,requiredHoldMs:350,gates:{left:'down',right:'up'},lowConfidence:[],
  minimumConfidence:.9,fresh:true,ageMs:0,...overrides});
const context=()=>({clientId:'browser-1',roundId:'round-1',revision:1,active:true,mode:'seated',after:0});
const packet=(overrides={})=>({protocol:1,runtime:{opencv:'5.0.0',verified:true},source:'camera',
  ...context(),status:'tracking',expected:'left',heldMs:0,seq:0,events:[],
  metrics:{armed:false,calibration:calibration()},...overrides});

test('diagnostics copy only bounded known fields and reject invalid or image-like extensions',()=>{
  const original=calibration();
  const clean=sanitizeCalibration(original);
  assert.deepEqual(clean,original);assert.notEqual(clean,original);
  assert.notEqual(clean.gates,original.gates);assert.notEqual(clean.lowConfidence,original.lowConfidence);
  for(const value of [null,[],{},calibration({reason:'raise-anything'}),
    calibration({neutralMs:301}),calibration({neutralMs:-1}),calibration({neutralMs:.5}),
    calibration({requiredNeutralMs:0}),calibration({requiredHoldMs:5001}),
    calibration({holdMs:351}),calibration({minimumConfidence:NaN}),
    calibration({fresh:'yes'}),calibration({fresh:true,ageMs:null}),
    calibration({fresh:true,ageMs:301}),calibration({ageMs:60001}),
    calibration({minimumConfidence:1.01}),calibration({gates:{left:'down',right:'up',x:1}}),
    calibration({gates:{left:'down',right:'other'}}),calibration({lowConfidence:['private-path']}),
    calibration({lowConfidence:['leftWrist','leftWrist']}),calibration({jpeg:'data:image/jpeg;base64,AAAA'})]){
    assert.equal(sanitizeCalibration(value),null);
  }
});

test('valid optional diagnostics survive transport; malformed diagnostics do not break semantic packets',async()=>{
  for(const value of [calibration(),null,{reason:'unknown'},'untrusted',calibration({x:10})]){
    const input=packet({metrics:{fps:20,armed:false,calibration:value}});
    const errors=[];
    const client=createMotionClient({getContext:context,onPacket:()=>{},onError:error=>errors.push(error),
      fetchImpl:async()=>new Response(JSON.stringify(input))});
    try{
      const result=await client.pollOnce();
      assert.equal(result.source,'camera');assert.equal(result.metrics.fps,20);assert.deepEqual(errors,[]);
      assert.deepEqual(result.metrics.calibration,sanitizeCalibration(value));
    }finally{client.stop();}
  }
});

test('non-diagnostic nested metrics remain invalid instead of widening the event protocol',async()=>{
  const errors=[];
  const client=createMotionClient({getContext:context,onPacket:()=>assert.fail('invalid delivered'),
    onError:error=>errors.push(error),fetchImpl:async()=>new Response(JSON.stringify(packet({metrics:{raw:{x:1}}})))});
  try{assert.equal(await client.pollOnce(),null);assert.equal(errors[0].code,'invalid-response');}
  finally{client.stop();}
});

test('visibility, incomplete rest and authoritative readiness produce different guidance',()=>{
  assert.match(calibrationFeedback(calibration({reason:'low-confidence',lowConfidence:['leftWrist']})).cue,/left wrist/);
  assert.match(calibrationFeedback(calibration()).cue,/right wrist.*below its shoulder/);
  assert.match(calibrationFeedback(calibration({reason:'settling-neutral',neutralMs:200})).label,/0\.2 \/ 0\.3s/);
  assert.match(calibrationFeedback(calibration({reason:'ready'}),{armed:false}).cue,/Rest both arms/);
  assert.match(calibrationFeedback(calibration({reason:'ready'}),{armed:true}).cue,/^Raise your left hand/);
  assert.match(calibrationFeedback(calibration({reason:'holding'}),{armed:true,expected:'right'}).cue,/^Hold your right hand/);
  assert.match(calibrationFeedback(calibration({reason:'wrong-side'}),{expected:'left'}).cue,/Rest both arms/);
  assert.match(calibrationFeedback(calibration({reason:'ready',fresh:false,ageMs:301}),{armed:true}).cue,/fresh camera frame/);
  assert.match(calibrationFeedback(calibration({reason:'stale',fresh:false,ageMs:900}),{armed:true}).cue,/Rest both arms/);
});

function render(overrides={}){
  const nodes=Object.fromEntries(['#sunshine-count','#sunshine-next','#camera-source','#motion-status',
    '#camera-cue'].map(key=>[key,{textContent:''}]));
  const garden={dataset:{motionCount:'0'},style:{setProperty(){}},querySelectorAll:()=>[]};
  const old=globalThis.document;
  globalThis.document={querySelector:selector=>selector==='.sunshine-garden'?garden:nodes[selector]};
  try{
    updateSunshine({motion:{roundId:'round-1',count:0,expected:'left',completed:false},packet:packet(),
      revision:1,paused:false,...overrides});
    return {cue:nodes['#camera-cue'].textContent,status:nodes['#motion-status'].textContent};
  }finally{globalThis.document=old;}
}

test('renderer uses live calibration without reusing stale, inactive or unverified readiness',()=>{
  assert.match(render().status,/Calibration: Rest both arms.*right wrist/);
  const ready=packet({metrics:{armed:true,calibration:calibration({reason:'ready'})}});
  assert.match(render({packet:ready}).cue,/^Raise your left hand/);
  for(const override of [{revision:2},{paused:true},{disconnected:true},
    {packet:{...ready,active:false}},{packet:{...ready,roundId:'previous'}},
    {packet:{...ready,runtime:{verified:false}}},{packet:{...ready,status:'low-confidence'}}]){
    const actual=render({packet:ready,...override});
    assert.doesNotMatch(actual.cue,/^Raise your|^Hold your/);
  }
  for(const value of [null,calibration({reason:'ready',fresh:false,ageMs:301}),
    calibration({reason:'stale',fresh:false,ageMs:1000})]){
    assert.doesNotMatch(render({packet:{...ready,metrics:{armed:true,calibration:value}}}).cue,/^Raise your|^Hold your/);
  }
});

test('video and synthetic diagnostics retain their source and do not become live camera calibration',()=>{
  for(const source of ['video','synthetic']){
    const result=render({packet:packet({source})});
    assert.doesNotMatch(result.status,/^Calibration:/);
    assert.match(result.status,source==='video'?/video/i:/Synthetic input/);
    const stale=render({packet:packet({source,status:'hold',metrics:{armed:true,
      calibration:calibration({reason:'stale',fresh:false,ageMs:400})}})});
    assert.match(stale.status,/Fresh frame needed/);assert.doesNotMatch(stale.status,/armed|Lovely.*hold/i);
    assert.doesNotMatch(stale.cue,/raise your|hold your/i);
    const malformed=render({packet:packet({source,status:'tracking',metrics:{armed:true,calibration:null}})});
    assert.match(malformed.status,/Calibration unavailable/i);assert.doesNotMatch(malformed.status,/armed/i);
    assert.doesNotMatch(malformed.cue,/raise your|hold your/i);
  }
});
