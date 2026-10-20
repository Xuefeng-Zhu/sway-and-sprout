import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validMotionRuntime} from '../src/runtime.js';
import {createMotionClient} from '../src/motion.js';

const runtime=(overrides={})=>({engine:'litert',engineVersion:'1.2.0',platform:'android',
  modelSha256:'a'.repeat(64),verified:true,...overrides});
const context=()=>({clientId:'client-1',roundId:'round-1',revision:1,active:true,mode:'seated',after:0});
const packet=identity=>({protocol:1,...context(),source:'video',runtime:identity,status:'tracking',
  expected:'left',heldMs:0,seq:0,events:[],metrics:{armed:true}});
const response=value=>new Response(JSON.stringify(value));

const invalidRuntimes=()=>[
  null,[],{},
  runtime({engine:'unknown'}),runtime({engine:'opencv'}),
  runtime({engine:undefined}),runtime({engineVersion:undefined}),runtime({engineVersion:'fake'}),
  runtime({engineVersion:'1.2'}),runtime({engineVersion:'v1.2.0'}),runtime({engineVersion:'01.2.0'}),
  runtime({engineVersion:'1.2.0-01'}),runtime({engineVersion:'1.2.0\n'}),
  runtime({engineVersion:'1.2.0+'+'a'.repeat(80)}),runtime({engineVersion:1.2}),
  runtime({platform:'macos'}),runtime({platform:undefined}),runtime({verified:'true'}),
  runtime({modelSha256:undefined}),runtime({modelSha256:'a'.repeat(63)}),
  runtime({modelSha256:'A'.repeat(64)}),runtime({modelSha256:'g'.repeat(64)}),
  runtime({modelSha256:'a'.repeat(64)+'\n'}),
  runtime({opencv:'5.0.0'}),runtime({opencv:null}),
  {opencv:'5.0.0',verified:true,engine:'unknown'},
  {opencv:'4.13.0',verified:true},
];

test('explicit pinned Android LiteRT identities accept bounded semantic versions without OpenCV',()=>{
  for(const engineVersion of ['1.2.0','2.0.1','1.3.0-rc.1','1.2.0+android.1']){
    assert.equal(validMotionRuntime(runtime({engineVersion})),true,engineVersion);
  }
  assert.equal(validMotionRuntime(runtime({verified:false})),true);
  assert.equal(Object.hasOwn(runtime(),'opencv'),false);
});

test('legacy OpenCV runtime and unverified diagnostics retain their existing acceptance',()=>{
  for(const identity of [
    {opencv:'5.0.0',verified:true},
    {opencv:'5.0.0-pre',verified:true,poseBackend:'mediapipe-full-image',
      modelSha256:'b'.repeat(64),mediapipe:'0.10.32',numpy:'2.2.6'},
    {opencv:'unavailable',verified:false},
    {opencv:'4.13.0',verified:false},
  ])assert.equal(validMotionRuntime(identity),true);
});

test('unknown, incomplete, oversized and contradictory runtime identities fail closed',()=>{
  for(const identity of invalidRuntimes())assert.equal(validMotionRuntime(identity),false,JSON.stringify(identity));
});

test('the actual motion client rejects invalid runtime identities before delivering semantic packets',async()=>{
  for(const identity of invalidRuntimes()){
    let error;
    const client=createMotionClient({getContext:context,onPacket:()=>assert.fail('invalid identity delivered'),
      onError:value=>{error=value;},fetchImpl:async()=>response(packet(identity))});
    try{
      assert.equal(await client.pollOnce(),null,JSON.stringify(identity));
      assert.equal(error?.code,'invalid-response',JSON.stringify(identity));
    }finally{client.stop();}
  }
});

test('unverified LiteRT diagnostics are delivered without impersonating OpenCV',async()=>{
  const value={...packet(runtime({verified:false})),status:'camera-error',metrics:{armed:false}};
  let delivered;
  const client=createMotionClient({getContext:context,onPacket:result=>{delivered=result;},
    fetchImpl:async()=>response(value)});
  try{
    assert.equal(await client.pollOnce(),delivered);
    assert.equal(delivered.runtime.engine,'litert');
    assert.equal(delivered.runtime.verified,false);
    assert.equal(Object.hasOwn(delivered.runtime,'opencv'),false);
    assert.deepEqual(delivered.events,[]);
  }finally{client.stop();}
});

test('LiteRT runtime provenance cannot conflict with its video packet source',async()=>{
  const client=createMotionClient({getContext:context,onPacket:()=>assert.fail('mixed provenance delivered'),
    fetchImpl:async()=>response(packet(runtime({source:'camera'})))});
  try{assert.equal(await client.pollOnce(),null);}finally{client.stop();}
});
