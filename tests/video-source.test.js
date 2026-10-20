import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as model from '../src/model.js';
import {createMotionClient,createMotionState,acceptMotionEvent} from '../src/motion.js';
import {createPreviewClient} from '../src/preview.js';
import {updateSunshine,updateCameraPreview} from '../src/motion-view.js';

const context=()=>({clientId:'browser-1',roundId:'round-1',revision:1,active:true,mode:'seated',after:0});
const packet=(source='video')=>({protocol:1,...context(),source,
  runtime:{opencv:'5.0.0',verified:true,source},status:'tracking',expected:'left',heldMs:0,
  seq:0,events:[],metrics:{armed:true}});
const preview=()=>({...context(),source:'video',available:true,
  jpeg:'data:image/jpeg;base64,/9j/2Q==',width:320,height:240,status:'tracking',
  visibility:{leftShoulder:true,rightShoulder:true,leftWrist:true,rightWrist:true},confidence:.9,expected:'left',heldMs:0});
const response=value=>new Response(JSON.stringify(value));

test('video semantic packets preserve explicit video provenance',async()=>{
  const client=createMotionClient({getContext:context,onPacket:()=>{},fetchImpl:async()=>response(packet())});
  const result=await client.pollOnce();
  assert.equal(result.source,'video');assert.equal(result.runtime.source,'video');client.stop();
});

test('conflicting runtime and packet provenance is rejected',async()=>{
  for(const [source,runtimeSource] of [['camera','video'],['video','camera']]){
    const value={...packet(source),runtime:{...packet(source).runtime,source:runtimeSource}};
    let errors=0;
    const client=createMotionClient({getContext:context,onPacket:()=>assert.fail('mixed provenance accepted'),
      onError:()=>errors++,fetchImpl:async()=>response(value)});
    assert.equal(await client.pollOnce(),null);assert.equal(errors,1);client.stop();
  }
});

test('bounded preview accepts replay frames without relabelling them as camera',async()=>{
  const client=createPreviewClient({getContext:context,onPreview:()=>{},fetchImpl:async()=>response(preview())});
  const result=await client.pollOnce();assert.equal(result.source,'video');assert.equal(result.available,true);client.stop();
});

function withView(run){
  const node=()=>({textContent:'',dataset:{},attributes:{},setAttribute(key,value){this.attributes[key]=value;},
    removeAttribute(key){delete this.attributes[key];if(key==='src')delete this.src;}});
  const ids=['sunshine-count','sunshine-next','camera-source','motion-input-mode','motion-status','camera-cue',
    'camera-preview-image','preview-placeholder','preview-title','preview-state','preview-placeholder-title',
    'preview-placeholder-detail','preview-confidence','preview-confidence-meter','preview-movement'];
  const nodes=Object.fromEntries(ids.map(id=>[`#${id}`,node()]));
  const landmarks=['leftShoulder','rightShoulder','leftWrist','rightWrist'].map(key=>({dataset:{landmark:key},querySelector:()=>node()}));
  const garden={dataset:{motionCount:'0'},style:{setProperty(){}},querySelectorAll:()=>[]};
  const panel={dataset:{},querySelector:selector=>nodes[selector],querySelectorAll:()=>landmarks};
  const pop={textContent:'',offsetWidth:0,classList:{remove(){},add(){}}};
  const previous=globalThis.document;
  globalThis.document={querySelector:selector=>selector==='.sunshine-garden'?garden:
    selector==='.camera-preview'?panel:selector==='#sunshine-pop'?pop:nodes[selector]};
  try{run(nodes,garden,panel);}finally{globalThis.document=previous;}
}

test('actual garden renderer labels video scoring and cues as a replay with no camera',()=>withView((nodes,garden)=>{
  updateSunshine({motion:createMotionState('round-1'),packet:packet(),paused:false,revision:1});
  assert.equal(nodes['#camera-source'].textContent,'VIDEO REPLAY · NO CAMERA');
  assert.match(nodes['#motion-input-mode'].textContent,/VIDEO REPLAY.*NO CAMERA/);
  assert.match(nodes['#camera-cue'].textContent,/^Video replay:/);
  assert.equal(garden.dataset.motionSource,'video');
  assert.doesNotMatch(nodes['#motion-status'].textContent,/You’re in view|Camera input/);
}));

test('actual preview renderer keeps live and paused replay distinct from camera capture',()=>withView(nodes=>{
  updateCameraPreview({preview:preview()});
  assert.equal(nodes['#preview-title'].textContent,'Local video replay');
  assert.equal(nodes['#preview-state'].textContent,'Replay · no camera');
  assert.match(nodes['#camera-preview-image'].alt,/video replay/);
  assert.equal(nodes['#camera-preview-image'].hidden,false);
  updateCameraPreview({reason:'paused',source:'video'});
  assert.equal(nodes['#camera-preview-image'].src,undefined);
  assert.equal(nodes['#camera-preview-image'].hidden,true);
  assert.match(nodes['#preview-placeholder-detail'].textContent,/No camera is active/);
  assert.match(nodes['#preview-movement'].textContent,/no camera/);
}));

test('video and synthetic completion return unchanged progress; camera and manual complete normally',()=>{
  const progress={completed:['wake'],sessions:3};
  for(const source of ['video','synthetic'])assert.equal(model.complete(progress,'sun',source),progress);
  assert.deepEqual(progress,{completed:['wake'],sessions:3});
  for(const source of ['manual','camera'])assert.deepEqual(model.complete(progress,'sun',source),{completed:['wake','sun'],sessions:3});
});

// Execute the real main module offline with in-memory DOM and clients. No UI,
// network, media API or timers run; the test hooks exist only in this VM string.
function appHarness(){
  let callbacks,id=0;const writes=[];const nodes={};
  const root={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>({focus(){}})};
  const sandbox={...model,createMotionState,acceptMotionEvent,
    createMotionClient:options=>{callbacks=options;return {start(){},stop(){}};},
    createPreviewClient:()=>({start(){},stop(){}}),sunshineMarkup:()=>'',updateSunshine(){},updateCameraPreview(){},
    document:{querySelector:selector=>selector==='#app'?root:nodes[selector]||= {textContent:'',style:{},classList:{toggle(){}}},
      addEventListener(){},dispatchEvent(){}},window:{addEventListener(){}},
    localStorage:{getItem:()=>JSON.stringify({completed:['wake'],sessions:3}),setItem:(key,value)=>writes.push([key,value])},
    crypto:{randomUUID:()=>`id-${++id}`},performance:{now:()=>0},requestAnimationFrame:()=>1,cancelAnimationFrame(){},
  };
  const main=readFileSync(new URL('../src/main.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
  const hooks=`\nglobalThis.hooks={act,finish,read:()=>({progress,screen,roundId,revision}),check:()=>{screen='check';render();},advanceToEnd:()=>{elapsed=challenges[selected].duration;tick(0);}};`;
  vm.runInNewContext(main+hooks,sandbox);
  const api=sandbox.hooks;
  api.act('choose:1');api.act('input:camera');api.act('start');
  return {api,writes,root,send(source,six=true){
    const current=api.read();
    callbacks.onPacket({...packet(source),roundId:current.roundId,revision:current.revision,
      seq:six?6:0,events:six?Array.from({length:6},(_,index)=>({seq:index+1,roundId:current.roundId,
        gesture:index%2?'right-raise':'left-raise',confidence:1,ageMs:0})):[]});
  }};
}

test('real automatic finish path saves camera progress but never saves six video or synthetic rays',()=>{
  for(const source of ['video','synthetic','camera']){
    const app=appHarness();app.send(source);app.api.advanceToEnd();
    const simulated=source==='video'||source==='synthetic';
    assert.equal(app.api.read().screen,'celebrate');
    assert.equal(app.writes.length,simulated?0:1);
    assert.deepEqual([...app.api.read().progress.completed],simulated?['wake']:['wake','sun']);
    if(source==='video'){
      assert.match(app.root.innerHTML,/VIDEO REPLAY · NO CAMERA/);
      assert.match(app.root.innerHTML,/does not verify live human camera recognition/);
      assert.doesNotMatch(app.root.innerHTML,/data-action="restart"/);
    }
  }
});

test('real synthetic check confirmation never persists progress, with zero or six rays',()=>{
  for(const six of [false,true]){
    const app=appHarness();app.send('synthetic',six);app.api.check();
    app.api.act('complete');
    assert.equal(app.api.read().screen,'celebrate');
    assert.equal(app.writes.length,0);
    assert.deepEqual([...app.api.read().progress.completed],['wake']);
  }
});

test('real manual confirmation still saves participation without a test source',()=>{
  const app=appHarness();app.api.act('manual');app.api.check();app.api.act('complete');
  assert.equal(app.writes.length,1);
  assert.deepEqual([...app.api.read().progress.completed],['wake','sun']);
});

test('real replay check confirmation cannot persist self-reported human progress',()=>{
  const app=appHarness();app.send('video',false);app.api.check();
  assert.match(app.root.innerHTML,/VIDEO REPLAY · NO CAMERA/);
  assert.doesNotMatch(app.root.innerHTML,/Manual: we joined in/);
  app.api.act('complete');assert.equal(app.writes.length,0);
  assert.deepEqual([...app.api.read().progress.completed],['wake']);
});
