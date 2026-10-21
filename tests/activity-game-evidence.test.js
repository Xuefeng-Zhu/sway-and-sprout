import test from 'node:test';
import assert from 'node:assert/strict';
import {createActivityGameHarness} from '../scripts/activity-game-evidence.mjs';

function packet(app,events){
  const c=app.context();
  return {protocol:1,source:'video',streamId:'offline-fixture',runtime:{opencv:'5.0.0-fixture',verified:true,source:'video'},
    ...c,status:'tracking',expected:'any',heldMs:0,seq:events.at(-1)?.seq||0,metrics:{armed:true},
    events:events.map(e=>({roundId:c.roundId,gesture:'activity',confidence:1,ageMs:0,...e}))};
}

test('actual app/reducer/view update from a semantic video event, retaining test source',async()=>{
  const app=await createActivityGameHarness();
  const result=app.receive(packet(app,[{seq:1}]));
  assert.equal(result.motion.count,1);assert.equal(result.displayedCount,1);
  assert.equal(result.collectedRays,1);assert.equal(result.growth,1/6);
  assert.equal(result.context.after,1);assert.equal(result.inputLabel,'VIDEO REPLAY · NO CAMERA');
  assert.equal(result.storedBytesUnchanged,true);assert.equal(result.storageWrites,0);
});

test('a repeated event is acknowledged once without more garden credit',async()=>{
  const app=await createActivityGameHarness(),value=packet(app,[{seq:1}]);
  app.receive(value);const result=app.receive(value);
  assert.equal(result.motion.count,1);assert.equal(result.collectedRays,1);assert.equal(result.context.after,1);
});

test('low-confidence event consumes sequence without adding growth',async()=>{
  const app=await createActivityGameHarness();const result=app.receive(packet(app,[{seq:1,confidence:.2}]));
  assert.equal(result.motion.count,0);assert.equal(result.collectedRays,0);assert.equal(result.context.after,1);
});

test('stale events retain the unchanged lease limit',async()=>{
  const app=await createActivityGameHarness();const result=app.receive(packet(app,[{seq:1,ageMs:1501}]));
  assert.equal(result.motion.count,0);assert.equal(result.context.after,0);
});

test('pause rejects stale active context and suppresses input',async()=>{
  const app=await createActivityGameHarness(),old=packet(app,[{seq:1}]);app.action('pause');
  assert.throws(()=>app.receive(old),/context mismatch/);
  const current=app.receive(packet(app,[{seq:1}]));
  assert.equal(current.motion.count,0);assert.equal(current.context.active,false);
});

test('six-ray bound stops active context and never saves test participation',async()=>{
  const app=await createActivityGameHarness();
  const result=app.receive(packet(app,Array.from({length:8},(_,i)=>({seq:i+1}))));
  assert.equal(result.motion.count,6);assert.equal(result.displayedCount,6);assert.equal(result.collectedRays,6);
  assert.equal(result.motion.completed,true);assert.equal(result.context.active,false);
  assert.equal(result.context.after,6);
  const final=app.finish();assert.equal(final.storedBytesUnchanged,true);assert.equal(final.storageWrites,0);
  assert.deepEqual(final.progress,{completed:['wake'],sessions:5});
});

test('the evidence adapter cannot relabel input as a human camera result',async()=>{
  const app=await createActivityGameHarness(),value=packet(app,[{seq:1}]);
  value.source='camera';value.runtime.source='camera';assert.throws(()=>app.receive(value),/video-source/);
});

test('wrong client/round context fails instead of crediting another session',async()=>{
  const app=await createActivityGameHarness(),value=packet(app,[{seq:1}]);value.roundId='another-round';
  assert.throws(()=>app.receive(value),/context mismatch/);assert.equal(app.snapshot().motion.count,0);
});
