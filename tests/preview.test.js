import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPreviewClient} from '../src/preview.js';
import {updateCameraPreview} from '../src/motion-view.js';

// Transport fixtures only: this byte string is not a saved camera frame and
// these tests do not claim that a person or gesture was recognized.
const context=()=>({clientId:'browser-1',roundId:'round-1',revision:1,
  active:true,mode:'seated',after:0});
const preview=(overrides={})=>({...context(),source:'camera',available:true,
  jpeg:'data:image/jpeg;base64,/9j/2Q==',width:320,height:240,status:'tracking',
  visibility:{leftShoulder:true,rightShoulder:true,leftWrist:false,rightWrist:true},
  confidence:.8,expected:'left',heldMs:0,...overrides});
const response=value=>new Response(JSON.stringify(value));
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};

test('preview uses one fixed local request with the semantic context and no cache',async()=>{
  const pending=deferred();let received,calls=0,options;
  const client=createPreviewClient({getContext:context,onPreview:value=>{received=value;},
    fetchImpl:(url,opts)=>{calls++;options=opts;const parsed=new URL(url,'https://local');
      assert.equal(parsed.pathname,'/motion/preview');
      assert.deepEqual(Object.fromEntries(parsed.searchParams),{...context(),revision:'1',active:'1',after:'0'});
      return pending.promise;}});
  const first=client.pollOnce();assert.equal(client.pollOnce(),first);
  pending.resolve(response(preview()));
  assert.equal((await first).confidence,.8);assert.equal(received.source,'camera');
  assert.equal(calls,1);assert.equal(options.cache,'no-store');
  assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
  client.stop();
});

test('inactive rounds do not request a preview or activate capture',async()=>{
  let calls=0,cleared;
  const client=createPreviewClient({getContext:()=>({...context(),active:false}),
    onPreview:()=>assert.fail('inactive image delivered'),onClear:reason=>{cleared=reason;},
    fetchImpl:()=>{calls++;throw Error('must not fetch');}});
  client.start();assert.equal(await client.pollOnce(),null);
  assert.equal(calls,0);assert.equal(cleared,'off');client.stop();
});

test('late images are dropped after pause, position, revision, round or client changes',async()=>{
  for(const change of [{active:false},{mode:'standing'},{revision:2},{roundId:'round-2'},{clientId:'browser-2'}]){
    const current=context(),pending=deferred();let images=0,errors=0,cleared=0;
    const client=createPreviewClient({getContext:()=>current,onPreview:()=>images++,
      onClear:()=>cleared++,onError:()=>errors++,fetchImpl:()=>pending.promise});
    const result=client.pollOnce();Object.assign(current,change);pending.resolve(response(preview()));
    assert.equal(await result,null);assert.equal(images,0);assert.equal(errors,0);assert.equal(cleared,1);
    client.stop();
  }
});

test('stop aborts, clears immediately and blocks a pending image after rapid resume',async()=>{
  const current=context(),first=deferred();let images=0,calls=0,signal;const cleared=[];
  const client=createPreviewClient({getContext:()=>current,onPreview:()=>images++,
    onClear:reason=>cleared.push(reason),fetchImpl:(_url,options)=>{
      calls++;signal=options.signal;return calls===1?first.promise:Promise.resolve(response(preview({revision:2})));
    }});
  client.start();const old=client.pollOnce();
  client.stop('paused');assert.equal(signal.aborted,true);assert.equal(cleared.at(-1),'paused');
  current.revision=2;client.start();first.resolve(response(preview()));
  assert.equal(await old,null);assert.equal(images,0);
  assert.equal((await client.pollOnce()).revision,2);assert.equal(images,1);
  client.stop('complete');assert.equal(cleared.at(-1),'complete');
});

test('synthetic and unavailable responses stay visibly separate from camera images',async()=>{
  for(const [source,status] of [['synthetic','synthetic'],['camera','stale'],['camera','expired']]){
    let received;
    const packet={...context(),source,status,available:false};
    const client=createPreviewClient({getContext:context,onPreview:value=>{received=value;},
      fetchImpl:async()=>response(packet)});
    assert.equal((await client.pollOnce()).available,false);assert.equal(received.source,source);
    assert.equal(received.jpeg,undefined);client.stop();
  }
});

test('identity, image type, size and confidence failures clear instead of displaying',async()=>{
  const invalid=[preview({source:'synthetic'}),preview({revision:99}),preview({active:false}),
    preview({jpeg:'https://external.invalid/image.jpg'}),preview({jpeg:'data:image/png;base64,AAAA'}),
    preview({jpeg:`data:image/jpeg;base64,${'A'.repeat(206*1024)}`}),preview({width:321}),
    preview({height:641}),preview({confidence:1.1}),preview({heldMs:-1}),
    preview({visibility:{leftShoulder:true}}),preview({available:false})];
  for(const packet of invalid){
    const errors=[];let cleared=0;
    const client=createPreviewClient({getContext:context,onPreview:()=>assert.fail('invalid image delivered'),
      onClear:()=>cleared++,onError:error=>errors.push(error),fetchImpl:async()=>response(packet)});
    assert.equal(await client.pollOnce(),null);assert.equal(errors.length,1);assert.equal(cleared,1);client.stop();
  }
});

test('oversized body or declared length is rejected and subsequent polling recovers',async()=>{
  for(const bad of [()=>new Response(' '.repeat(220*1024+1)),
    ()=>new Response('{}',{headers:{'content-length':String(220*1024+1)}})]){
    let calls=0,errors=0;
    const client=createPreviewClient({getContext:context,onPreview:()=>{},onError:()=>errors++,
      fetchImpl:async()=>++calls===1?bad():response(preview())});
    assert.equal(await client.pollOnce(),null);assert.equal(errors,1);
    assert.equal((await client.pollOnce()).available,true);client.stop();
  }
});

test('preview view removes src and confidence/landmark feedback on pause and completion',()=>{
  const node=()=>({textContent:'',dataset:{},attributes:{},setAttribute(key,value){this.attributes[key]=value;},
    removeAttribute(key){delete this.attributes[key];if(key==='src')delete this.src;}});
  const selectors=Object.fromEntries(['camera-preview-image','preview-placeholder','preview-state',
    'preview-placeholder-title','preview-placeholder-detail','preview-confidence','preview-confidence-meter',
    'preview-movement'].map(id=>[`#${id}`,node()]));
  const landmarks=['leftShoulder','rightShoulder','leftWrist','rightWrist'].map(key=>{
    const label=node();return {dataset:{landmark:key},querySelector:()=>label,label};});
  const panel={dataset:{},querySelector:selector=>selectors[selector],querySelectorAll:()=>landmarks};
  const oldDocument=globalThis.document;
  globalThis.document={querySelector:()=>panel};
  try{
    updateCameraPreview({preview:preview(),expected:'left'});
    assert.equal(selectors['#camera-preview-image'].hidden,false);
    assert.equal(selectors['#preview-placeholder'].hidden,true);
    assert.equal(selectors['#preview-confidence'].textContent,'80%');
    assert.equal(landmarks[2].label.textContent,'Not clear');
    for(const reason of ['paused','complete','off','unavailable','synthetic']){
      updateCameraPreview({reason});
      assert.equal(selectors['#camera-preview-image'].hidden,true);
      assert.equal(selectors['#camera-preview-image'].src,undefined);
      assert.equal(selectors['#preview-confidence'].textContent,'—');
      assert.equal(landmarks[0].label.textContent,'—');
    }
  }finally{globalThis.document=oldDocument;}
});
