import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as model from '../src/model.js';
import {createMotionState,acceptMotionEvent} from '../src/motion.js';
import {roundTickDelta} from '../src/round-clock.js';
import {gardenMarkup} from '../src/garden-view.js';
import * as cloud from '../src/cloud-garden.js';

const endpoint='https://garden.example.test/api';
const reply=(progress,version=1)=>new Response(JSON.stringify({schemaVersion:1,generation:'c059ed64-f482-45bb-858d-9664dd126aae',version,progress,
  updatedAt:'2026-10-21T21:00:00+00:00',expiresAt:1800000000}),{headers:{'Content-Type':'application/json'}});
function app({configured=endpoint,hostname='garden.example.test',search='',fetchImpl,storageBlocked=false}={}){
  const initial=JSON.stringify({completed:['wake'],sessions:4}),storage=new Map([['togethermove.v1',initial]]),calls=[];
  let callbacks;
  const root={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>({focus(){}})};
  const nodes={},listeners={};
  const sandbox={...model,...cloud,createMotionState,acceptMotionEvent,roundTickDelta,gardenMarkup,URLSearchParams,
    location:{hostname,protocol:'https:',search},crypto:webcrypto,
    createCloudGardenClient:options=>cloud.createCloudGardenClient({...options,cryptoImpl:webcrypto,timeoutMs:500,
      fetchImpl:async(url,options)=>{calls.push([url,options]);return fetchImpl?fetchImpl(url,options):reply(JSON.parse(options.body).progress);}}),
    createMotionClient:options=>{callbacks=options;return{start(){},stop(){}};},
    createPreviewClient:()=>({start(){},stop(){}}),sunshineMarkup:()=>'',updateSunshine(){},updateCameraPreview(){},
    document:{activeElement:{dataset:{action:'start'}},querySelector:selector=>selector==='#app'?root:
      selector==='meta[name="sway-garden-api"]'?{content:configured}:nodes[selector]||={textContent:'',style:{},classList:{toggle(){}}},
      addEventListener(){},dispatchEvent(){}},window:{addEventListener:(key,fn)=>{listeners[key]=fn;}},
    localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},
    performance:{now:()=>0},requestAnimationFrame:()=>1,cancelAnimationFrame(){},
  };
  if(storageBlocked)Object.defineProperty(sandbox,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError');}});
  const source=readFileSync(new URL('../src/main.js',import.meta.url),'utf8').replace(/^import .*;\n/gm,'');
  vm.runInNewContext(source+`\nglobalThis.api={act,back,read:()=>({progress,screen,journeyCompleted,harvestClaimed,cloudStatus,manualCount})};`,sandbox);
  return {api:sandbox.api,root,storage,calls,listeners,initial,
    synthetic(){sandbox.api.act('choose:1');sandbox.api.act('input:camera');sandbox.api.act('start');
      const context=callbacks.getContext();callbacks.onPacket({...context,source:'synthetic',streamId:'generated',
        runtime:{opencv:'5.0.0',verified:true},events:[],status:'tracking',metrics:{},seq:0});sandbox.api.act('home');},
  };
}

test('actual app has no cloud controls or calls by default, on native hosts, or in diagnostic URLs',async()=>{
  for(const options of [{configured:''},{hostname:'app.togethermove.local'},{hostname:'togethermove.local'},
    {search:'?input=video-verification'},{search:'?source=synthetic'},{search:'?policy=strict'}]){
    const current=app(options);assert.doesNotMatch(current.root.innerHTML,/data-action="cloud"/);
    await current.api.act('cloud');await current.api.act('cloud-backup');assert.equal(current.calls.length,0);
    assert.equal(current.storage.size,1);assert.equal(current.storage.get('togethermove.v1'),current.initial);
  }
});

test('configured controls only appear at rest and never send until an explicit backup action',async()=>{
  const current=app();assert.match(current.root.innerHTML,/data-action="cloud"/);assert.equal(current.calls.length,0);
  current.api.act('cloud');assert.equal(current.api.read().screen,'cloud');assert.equal(current.calls.length,0);
  assert.match(current.root.innerHTML,/This browser holds your backup key/);assert.match(current.root.innerHTML,/Clearing its data removes access/);
  await current.api.act('cloud-backup');assert.equal(current.calls.length,1);
  assert.equal(current.storage.get('togethermove.v1'),current.initial,'Backup never rewrites local participation');
  current.api.act('home');current.api.act('choose:0');current.api.act('start');
  assert.doesNotMatch(current.root.innerHTML,/data-action="cloud"/);await current.api.act('cloud-backup');assert.equal(current.calls.length,1);
});

test('blocked localStorage getter preserves manual play and reports backup storage failure before HTTP',async()=>{
  const current=app({storageBlocked:true});
  assert.equal(current.api.read().screen,'home');assert.match(current.root.innerHTML,/Start growing/);
  assert.equal(current.calls.length,0);
  current.api.act('cloud');await current.api.act('cloud-backup');
  assert.match(current.root.innerHTML,/backup key could not be saved on this device/);
  assert.match(current.root.innerHTML,/No backup request was sent/);assert.equal(current.calls.length,0);
  current.api.act('home');current.api.act('choose:0');current.api.act('start');
  for(let i=0;i<6;i++)current.api.act('manual-count');
  current.api.act('finish-moment');current.api.act('complete');
  assert.equal(current.api.read().screen,'celebrate');
  assert.deepEqual(Array.from(current.api.read().progress.completed),['wake']);
  assert.match(current.root.innerHTML,/Progress could not be saved on this device/);
  assert.equal(current.calls.length,0);assert.equal(current.storage.get('togethermove.v1'),current.initial);
});

test('explicit restore merges saved blooms without awarding a visit, harvest or duplicate session',async()=>{
  const current=app({fetchImpl:async(url,options)=>options.method==='GET'?
    reply({completed:['sun'],sessions:2},2):reply(JSON.parse(options.body).progress)});
  current.api.act('cloud');await current.api.act('cloud-backup');await current.api.act('cloud-restore');
  assert.deepEqual(JSON.parse(current.storage.get('togethermove.v1')),{completed:['wake','sun'],sessions:4});
  assert.equal(current.api.read().journeyCompleted.length,0);assert.equal(current.api.read().harvestClaimed,false);
  assert.match(current.root.innerHTML,/Blooms restored\. Current visit unchanged\./);
  current.api.act('home');assert.doesNotMatch(current.root.innerHTML,/data-action="return-harvest"/);
});

test('test packets hide backup controls and cannot reach cloud actions after returning home',async()=>{
  const current=app();current.synthetic();assert.doesNotMatch(current.root.innerHTML,/data-action="cloud"/);
  current.api.act('cloud');await current.api.act('cloud-backup');assert.equal(current.calls.length,0);
  assert.equal(current.storage.get('togethermove.v1'),current.initial);
});

test('leaving during restore ignores a late cloud result and retains every original local byte',async()=>{
  let release;
  const current=app({fetchImpl:(url,options)=>options.method==='GET'?new Promise(resolve=>{release=resolve;}):reply(JSON.parse(options.body).progress)});
  current.api.act('cloud');await current.api.act('cloud-backup');const pending=current.api.act('cloud-restore');
  current.api.act('home');await pending;release(reply({completed:['rain'],sessions:9},2));
  await new Promise(resolve=>setImmediate(resolve));assert.equal(current.api.read().screen,'home');
  assert.equal(current.storage.get('togethermove.v1'),current.initial);assert.equal(current.api.read().journeyCompleted.length,0);
});

test('Help cancels a pending restore and Return shows cancellation instead of a stale busy status',async()=>{
  let release;
  const current=app({fetchImpl:(url,options)=>options.method==='GET'?new Promise(resolve=>{release=resolve;}):reply(JSON.parse(options.body).progress)});
  current.api.act('cloud');await current.api.act('cloud-backup');const pending=current.api.act('cloud-restore');
  assert.match(current.root.innerHTML,/Restoring blooms…/);
  current.api.act('help');await pending;current.api.act('return');
  assert.equal(current.api.read().screen,'cloud');assert.match(current.root.innerHTML,/request was cancelled/);
  assert.doesNotMatch(current.root.innerHTML,/Restoring blooms…|Backing up…/);
  release(reply({completed:['rain'],sessions:9},2));await new Promise(resolve=>setImmediate(resolve));
  assert.match(current.root.innerHTML,/request was cancelled/);
  assert.equal(current.storage.get('togethermove.v1'),current.initial);
});

test('deleting requires confirmation and never deletes the garden saved on this device',async()=>{
  const current=app({fetchImpl:async(url,options)=>options.method==='DELETE'?new Response(null,{status:204}):reply(JSON.parse(options.body).progress)});
  current.api.act('cloud');await current.api.act('cloud-backup');await current.api.act('cloud-delete-confirm');assert.equal(current.calls.length,1);
  current.api.act('cloud-delete');assert.match(current.root.innerHTML,/Delete cloud copy\? Your local garden stays\./);
  current.api.act('cloud-delete-cancel');assert.equal(current.calls.length,1);
  current.api.act('cloud-delete');await current.api.act('cloud-delete-confirm');assert.equal(current.calls.length,2);
  assert.equal(current.storage.get('togethermove.v1'),current.initial);assert.match(current.root.innerHTML,/Cloud copy deleted/);
});

test('pagehide cancels a pending restore without applying or rendering its late response',async()=>{
  let release;
  const current=app({fetchImpl:(url,options)=>options.method==='GET'?new Promise(resolve=>{release=resolve;}):reply(JSON.parse(options.body).progress)});
  current.api.act('cloud');await current.api.act('cloud-backup');const pending=current.api.act('cloud-restore');
  const before=current.root.innerHTML;current.listeners.pagehide();await pending;
  release(reply({completed:['rain'],sessions:99},2));await new Promise(resolve=>setImmediate(resolve));
  assert.equal(current.root.innerHTML,before);assert.equal(current.storage.get('togethermove.v1'),current.initial);
});
