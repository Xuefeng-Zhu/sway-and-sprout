import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {CLOUD_STORAGE_PREFIX,cloudBackupLocationAllowed,normalizeCloudEndpoint,
  cleanGardenProgress,mergeGardenProgress,createCloudGardenClient,cloudGardenErrorMessage} from '../src/cloud-garden.js';

const endpoint='https://garden.example.test/api';
const context={active:false,source:'confirmed'};
const generation='c059ed64-f482-45bb-858d-9664dd126aae';
const progress={completed:['sun'],sessions:2};
const record=(extra={})=>({schemaVersion:1,generation,version:1,progress,updatedAt:'2026-10-21T20:00:00+00:00',expiresAt:1800000000,...extra});
const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
function memoryStorage(){const values=new Map(),writes=[];return {values,writes,getItem:k=>values.get(k)??null,
  setItem(k,v){values.set(k,v);writes.push([k,v]);},removeItem(k){values.delete(k);}};}
function setup(fetchImpl=async()=>response(record()),options={}){
  const storage=options.storage||memoryStorage(),calls=[];
  const client=createCloudGardenClient({endpoint,storage,cryptoImpl:webcrypto,
    fetchImpl:async(...args)=>{calls.push(args);return fetchImpl(...args);},...options});
  return {client,storage,calls};
}
const rejects=(promise,code)=>assert.rejects(promise,error=>error.code===code);

test('backup stays disabled and inert without an approved HTTPS endpoint',async()=>{
  for(const value of ['',undefined,'/api','http://garden.example.test','https://a:b@garden.example.test',
    'https://garden.example.test/?token=bad','https://garden.example.test/#key','javascript:alert(1)']){
    const app=setup(undefined,{endpoint:value});
    assert.equal(app.client.snapshot().configured,false);
    assert.equal(app.calls.length,0);assert.equal(app.storage.writes.length,0);
    await rejects(app.client.backup(progress,context),'disabled');assert.equal(app.calls.length,0);
  }
  assert.equal(normalizeCloudEndpoint(endpoint+'/'),endpoint);
  assert.equal(normalizeCloudEndpoint('http://localhost:8769'), '');
  assert.equal(normalizeCloudEndpoint('http://localhost:8769',{allowLocalHttp:true}),'http://localhost:8769');
  assert.equal(normalizeCloudEndpoint('http://example.test',{allowLocalHttp:true}),'');
});

test('native and diagnostic locations cannot enable the web-only cloud feature',()=>{
  const location={protocol:'https:',hostname:'web.example.test',search:''};
  assert.equal(cloudBackupLocationAllowed(location),true);
  for(const hostname of ['app.togethermove.local','togethermove.local'])assert.equal(cloudBackupLocationAllowed({...location,hostname}),false);
  assert.equal(cloudBackupLocationAllowed({...location,protocol:'file:'}),false);
  for(const search of ['?input=video-verification','?input=video','?input=synthetic','?source=video','?source=synthetic','?policy=strict'])
    assert.equal(cloudBackupLocationAllowed({...location,search}),false,search);
});

test('only strict confirmed summary fields are accepted; restore merges without losing local blooms',()=>{
  assert.deepEqual(cleanGardenProgress({completed:['rain','wake'],sessions:0}),{completed:['wake','rain'],sessions:0});
  for(const value of [null,{...progress,frames:[1]},{completed:['sun','sun'],sessions:2},
    {completed:['other'],sessions:2},{completed:[],sessions:NaN},{completed:[],sessions:-1},
    {completed:[],sessions:Number.MAX_SAFE_INTEGER+1}])assert.throws(()=>cleanGardenProgress(value));
  assert.deepEqual(mergeGardenProgress({completed:['wake'],sessions:8},progress),{completed:['wake','sun'],sessions:8});
});

test('active, synthetic and video calls cannot create keys or send a request',async()=>{
  const app=setup();
  for(const source of ['video','synthetic','camera','manual',undefined])
    await rejects(app.client.backup(progress,{active:false,source}),'blocked');
  await rejects(app.client.backup(progress,{active:true,source:'confirmed'}),'blocked');
  await rejects(app.client.restore(),'blocked');
  assert.equal(app.storage.writes.length,0);assert.equal(app.calls.length,0);
});

test('first explicit backup saves its key before HTTPS and sends no movement or AWS credentials',async()=>{
  const storage=memoryStorage();
  const app=setup(async(url,options)=>{
    const saved=JSON.parse(storage.getItem(CLOUD_STORAGE_PREFIX+endpoint));
    assert.equal(saved.version,0);assert.match(saved.gardenId,/^[0-9a-f-]{36}$/);
    assert.match(saved.token,/^[A-Za-z0-9_-]{43}$/);
    assert.equal(new Uint8Array(Buffer.from(saved.token,'base64url')).length,32);
    assert.equal(options.headers.Authorization,`Bearer ${saved.token}`);
    assert.equal(url,`${endpoint}/gardens/${saved.gardenId}`);assert.ok(!url.includes(saved.token));
    assert.deepEqual(JSON.parse(options.body),{schemaVersion:1,expectedVersion:0,progress});
    for(const [key,value] of Object.entries({credentials:'omit',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'}))
      assert.equal(options[key],value);
    return response(record(),201);
  },{storage});
  assert.equal(app.calls.length,0);await app.client.backup(progress,context);
  assert.equal(app.calls.length,1);assert.equal(app.client.snapshot().version,1);
  assert.deepEqual(Object.keys(app.client.snapshot()).sort(),['busy','configured','hasIdentity','version']);
});

test('storage failure prevents an orphaned create, and service changes never reuse another endpoint key',async()=>{
  for(const storage of [
    {getItem:()=>null,setItem(){throw new Error('private mode');}},
    {getItem:()=>null,setItem(){}},
  ]){
    const app=setup(undefined,{storage});await rejects(app.client.backup(progress,context),'storage');assert.equal(app.calls.length,0);
  }
  const storage=memoryStorage(),app=setup(undefined,{storage});await app.client.backup(progress,context);
  const other=setup(undefined,{endpoint:'https://other.example.test',storage});
  assert.equal(other.client.snapshot().hasIdentity,false);assert.equal(other.calls.length,0);
});

test('version conflict preserves identity and needs an explicit GET before another PUT',async()=>{
  let stage=0;
  const app=setup(async(url,options)=>{
    stage++;
    if(stage===1)return response(record());
    if(stage===2)return response({error:'conflict'},409);
    if(stage===3){assert.equal(options.method,'GET');return response(record({version:3}));}
    assert.equal(JSON.parse(options.body).expectedVersion,3);assert.equal(JSON.parse(options.body).expectedGeneration,generation);return response(record({version:4}));
  });
  await app.client.backup(progress,context);const before=app.storage.getItem(CLOUD_STORAGE_PREFIX+endpoint);
  await rejects(app.client.backup(progress,context),'conflict');assert.equal(app.storage.getItem(CLOUD_STORAGE_PREFIX+endpoint),before);
  assert.equal(app.calls.length,2,'No automatic retry');await app.client.restore(context);await app.client.backup(progress,context);
  assert.equal(app.client.snapshot().version,4);
});

test('malformed, oversized, stale and mismatched responses cannot become a restored garden',async()=>{
  for(const bad of [record({version:0}),record({schemaVersion:2}),record({progress:{...progress,rawPose:[]}}),
    record({updatedAt:'not a timestamp'}),record({secret:'unexpected'}),record({progress:{completed:['unknown'],sessions:1}})]){
    const app=setup(async()=>response(bad));await rejects(app.client.backup(progress,context),'invalid');assert.equal(app.client.snapshot().version,0);
  }
  const tooLarge=setup(async()=>new Response(' '.repeat(2050),{headers:{'Content-Type':'application/json'}}));
  await rejects(tooLarge.client.backup(progress,context),'invalid');assert.equal(tooLarge.calls.length,1);
  const wrong=setup(async()=>response(record({progress:{completed:['wake'],sessions:1}})));
  await rejects(wrong.client.backup(progress,context),'invalid');assert.equal(wrong.client.snapshot().version,0);
  const wrongType=setup(async()=>new Response(JSON.stringify(record()),{headers:{'Content-Type':'application/jsonp'}}));
  await rejects(wrongType.client.backup(progress,context),'invalid');
});

test('failed and timed-out requests never retry automatically and preserve the recoverable key',async()=>{
  const unavailable=setup(async()=>{throw new Error('network');});
  await rejects(unavailable.client.backup(progress,context),'unavailable');assert.equal(unavailable.calls.length,1);
  assert.equal(unavailable.client.snapshot().hasIdentity,true);assert.equal(unavailable.client.snapshot().version,0);
  const timed=setup(()=>new Promise(()=>{}),{timeoutMs:100});
  await rejects(timed.client.backup(progress,context),'timeout');assert.equal(timed.calls.length,1);assert.equal(timed.client.snapshot().busy,false);
  assert.equal(timed.client.snapshot().hasIdentity,true);
});

test('leaving cancels a stalled request; a late result cannot update its identity version',async()=>{
  let release;const app=setup(()=>new Promise(resolve=>{release=resolve;}));
  const pending=app.client.backup(progress,context);assert.equal(app.client.snapshot().busy,true);
  await rejects(app.client.backup(progress,context),'busy');app.client.cancel();await rejects(pending,'cancelled');
  release(response(record()));await new Promise(resolve=>setImmediate(resolve));
  assert.equal(app.client.snapshot().version,0);assert.equal(app.calls.length,1);
});

test('delete requires an owned version, uses If-Match and keeps unrelated local progress',async()=>{
  const app=setup(async(url,options)=>options.method==='DELETE'?new Response(null,{status:204}):response(record()));
  app.storage.setItem('togethermove.v1','original local garden');
  await app.client.backup(progress,context);await app.client.remove(context);
  const [,options]=app.calls[1];assert.equal(options.method,'DELETE');assert.equal(options.headers['If-Match'],`"${generation}:1"`);
  assert.equal(options.body,undefined);assert.equal(app.client.snapshot().hasIdentity,false);
  assert.equal(app.storage.getItem('togethermove.v1'),'original local garden');
});

test('untrusted error strings are never shown to players',()=>{
  assert.equal(cloudGardenErrorMessage(new Error('<script>token</script>')),
    'Garden backup is unavailable. Your local garden is unchanged.');
});

test('a response from another generation cannot update or restore this backup identity',async()=>{
  let stage=0;const other='dcf1e138-bffd-4a8f-b283-27a3d904b197';
  const app=setup(async()=>response(record(++stage===1?{}:{generation:other,version:2})));
  await app.client.backup(progress,context);const before=app.storage.getItem(CLOUD_STORAGE_PREFIX+endpoint);
  await rejects(app.client.backup(progress,context),'invalid');
  await rejects(app.client.restore(context),'conflict');assert.equal(app.storage.getItem(CLOUD_STORAGE_PREFIX+endpoint),before);
});

test('one explicit retry after an uncertain create reuses its exact body and recovers the server generation',async()=>{
  let stage=0;const app=setup(async()=>++stage===1?new Promise(()=>{}):response(record()),{timeoutMs:100});
  await rejects(app.client.backup(progress,context),'timeout');assert.equal(app.calls.length,1);
  await app.client.backup(progress,context);assert.equal(app.calls.length,2);
  assert.equal(app.calls[0][0],app.calls[1][0]);assert.equal(app.calls[0][1].body,app.calls[1][1].body);
  assert.equal(Object.hasOwn(JSON.parse(app.calls[1][1].body),'expectedGeneration'),false);
  assert.equal(app.client.snapshot().version,1);
});

test('not-found and owner-validated revocation retire the key; the next explicit backup uses fresh identity',async()=>{
  for(const status of [404,410]){
    let stage=0;const other='dcf1e138-bffd-4a8f-b283-27a3d904b197';
    const app=setup(async()=>{
      stage++;if(stage===1)return response(record());
      if(stage===2)return response({error:'unavailable'},status);
      return response(record({generation:other}),201);
    });
    await app.client.backup(progress,context);
    await rejects(status===404?app.client.restore(context):app.client.backup(progress,context),status===404?'missing':'retired');
    assert.equal(app.client.snapshot().hasIdentity,false);assert.equal(app.calls.length,2,'No retry on the response');
    await app.client.backup(progress,context);
    assert.notEqual(app.calls[0][0],app.calls[2][0]);
    assert.notEqual(app.calls[0][1].headers.Authorization,app.calls[2][1].headers.Authorization);
    const body=JSON.parse(app.calls[2][1].body);assert.equal(body.expectedVersion,0);assert.equal(Object.hasOwn(body,'expectedGeneration'),false);
  }
});

test('a failed metadata write after a successful response retains a recoverable pre-request key',async()=>{
  const storage=memoryStorage(),write=storage.setItem;let writes=0;
  storage.setItem=function(...args){if(++writes===2)throw new Error('quota');write.apply(this,args);};
  const app=setup(undefined,{storage});await rejects(app.client.backup(progress,context),'storage-after-request');
  const saved=JSON.parse(storage.getItem(CLOUD_STORAGE_PREFIX+endpoint));assert.equal(saved.version,0);
  assert.equal(app.calls.length,1);assert.match(saved.token,/^[A-Za-z0-9_-]{43}$/);
});
