#!/usr/bin/env node
// Execute the actual app logic in a VM with in-memory storage/DOM and inert clients.
// This never accesses real browser storage, cameras, media APIs, HTTP, or UI.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {pathToFileURL,fileURLToPath,URLSearchParams} from 'node:url';
import vm from 'node:vm';

const project=path.resolve(process.argv[2]||fileURLToPath(new URL('../',import.meta.url)));
const output=path.resolve(process.argv[3]||'simulated-progress-preservation-result.json');
const model=await import(pathToFileURL(path.join(project,'src/model.js')).href);
const {createMotionState,acceptMotionEvent}=await import(pathToFileURL(path.join(project,'src/motion.js')).href);
const {createSpokenPrompts,manualPromptContext}=await import(pathToFileURL(path.join(project,'src/spoken-prompts.js')).href);
const main=readFileSync(path.join(project,'src/main.js'),'utf8');
const seeds=[
  {name:'existing-other',completed:['wake'],sessions:3},
  {name:'existing-sun',completed:['sun'],sessions:7},
  {name:'multiple-without-sun',completed:['wake','rain'],sessions:23},
  {name:'multiple-with-sun',completed:['sun','rain'],sessions:42},
  {name:'all-challenges',completed:['wake','sun','rain'],sessions:57},
  {name:'all-alternate-order',completed:['rain','wake','sun'],sessions:101},
];
const results=[];
const plain=value=>JSON.parse(JSON.stringify(value));

function harness(seed,{manual=false}={}){
  // Deliberately non-canonical formatting/order detects even a semantically
  // identical rewrite. The seed contains no real user data.
  const raw=JSON.stringify({sessions:seed.sessions,completed:seed.completed},null,2)+'\n';
  let stored=raw,callbacks,id=0;
  const writes=[],nodes={};
  const root={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>({focus(){}})};
  const sandbox={...model,createMotionState,acceptMotionEvent,createSpokenPrompts,manualPromptContext,
    URLSearchParams,location:{search:''},
    createMotionClient:options=>{callbacks=options;return {start(){},stop(){}};},
    createPreviewClient:()=>({start(){},stop(){}}),sunshineMarkup:()=>'',
    updateSunshine(){},updateCameraPreview(){},
    document:{querySelector:selector=>selector==='#app'?root:
      nodes[selector]||= {textContent:'',style:{},classList:{toggle(){}}},
      addEventListener(){},dispatchEvent(){}},window:{addEventListener(){}},
    localStorage:{getItem:key=>key==='togethermove.v1'?stored:null,
      setItem:(key,value)=>{writes.push({key,value});if(key==='togethermove.v1')stored=value;}},
    crypto:{randomUUID:()=>`fixture-id-${++id}`},performance:{now:()=>0},
    requestAnimationFrame:()=>1,cancelAnimationFrame(){},
  };
  const hooks=`\nglobalThis.hooks={act,read:()=>({progress,screen,roundId,revision,clientId,motion}),
    check:()=>{screen='check';render();},
    advanceToEnd:()=>{elapsed=challenges[selected].duration;tick(0);}};`;
  vm.runInNewContext(main.replace(/^import .*;\n/gm,'')+hooks,sandbox);
  const api=sandbox.hooks;
  const before=api.read().progress;
  const beforeValue=plain(before);
  api.act('choose:1');
  if(!manual)api.act('input:camera');
  api.act('start');
  return {api,writes,raw,before,beforeValue,stored:()=>stored,
    send(source,rays){
      const current=api.read();
      callbacks.onPacket({protocol:1,source,streamId:'offline-fixture-stream',
        runtime:{opencv:'5.0.0-fixture',verified:true,source},
        clientId:current.clientId,roundId:current.roundId,revision:current.revision,
        active:true,mode:'seated',status:'tracking',expected:rays===6?'left':'left',
        heldMs:0,seq:rays,metrics:{armed:true},
        events:Array.from({length:rays},(_,index)=>({seq:index+1,roundId:current.roundId,
          gesture:index%2?'right-raise':'left-raise',confidence:1,ageMs:0}))});
    }};
}

function record(name,run){
  try{results.push({name,passed:true,...run()});}
  catch(error){results.push({name,passed:false,error:error.message});}
}

for(const seed of seeds){
  for(const source of ['video','synthetic']){
    record(`${seed.name}/${source}/model-reference`,()=>{
      const progress={completed:[...seed.completed],sessions:seed.sessions};
      const before=plain(progress);
      assert.equal(model.complete(progress,'sun',source),progress);
      assert.deepEqual(progress,before);
      return {kind:'model-reference',source,seed:seed.name};
    });
    for(const rays of [0,6])for(const flow of ['automatic','confirmation']){
      record(`${seed.name}/${source}/${rays}-rays/${flow}`,()=>{
        const app=harness(seed);app.send(source,rays);
        if(flow==='automatic')app.api.advanceToEnd();
        else{app.api.check();app.api.act('complete');}
        const after=app.api.read();
        assert.equal(after.screen,flow==='automatic'&&rays===0?'check':'celebrate');
        assert.equal(after.motion.count,rays);
        assert.equal(app.writes.length,0);
        assert.equal(app.stored(),app.raw);
        assert.equal(after.progress,app.before);
        assert.deepEqual(plain(after.progress),app.beforeValue);
        assert.deepEqual([...after.progress.completed],seed.completed);
        assert.equal(after.progress.sessions,seed.sessions);
        return {kind:'simulated-preservation',source,seed:seed.name,rays,flow,
          setItemWrites:app.writes.length,storedJsonBytesUnchanged:true,
          memoryValueUnchanged:true,memoryReferenceUnchanged:true};
      });
    }
  }
  for(const rays of [0,6])for(const flow of ['automatic','confirmation']){
    record(`${seed.name}/camera/${rays}-rays/${flow}`,()=>{
      const app=harness(seed);app.send('camera',rays);
      if(flow==='automatic')app.api.advanceToEnd();
      else{app.api.check();app.api.act('complete');}
      const shouldSave=flow==='confirmation'||rays===6;
      const expected=shouldSave?model.complete(app.beforeValue,'sun','camera'):app.beforeValue;
      assert.equal(app.writes.length,shouldSave?1:0);
      assert.deepEqual(plain(app.api.read().progress),expected);
      assert.equal(app.api.read().progress.sessions,seed.sessions);
      if(shouldSave)assert.deepEqual(JSON.parse(app.stored()),expected);
      else assert.equal(app.stored(),app.raw);
      return {kind:'camera-retained-behavior',source:'camera',seed:seed.name,rays,flow,
        expectedSetItemWrites:shouldSave?1:0,setItemWrites:app.writes.length};
    });
  }
  record(`${seed.name}/manual/confirmation`,()=>{
    const app=harness(seed,{manual:true});app.api.check();app.api.act('complete');
    const expected=model.complete(app.beforeValue,'sun','manual');
    assert.equal(app.writes.length,1);
    assert.deepEqual(plain(app.api.read().progress),expected);
    assert.equal(app.api.read().progress.sessions,seed.sessions);
    assert.deepEqual(JSON.parse(app.stored()),expected);
    return {kind:'manual-retained-behavior',source:'manual',seed:seed.name,setItemWrites:1};
  });
}

const hash=file=>createHash('sha256').update(readFileSync(path.join(project,file))).digest('hex');
const summary={project,passed:results.every(result=>result.passed),checksRun:results.length,
  checksPassed:results.filter(result=>result.passed).length,
  simulatedScenarios:results.filter(result=>result.kind==='simulated-preservation').length,
  modelReferenceChecks:results.filter(result=>result.kind==='model-reference').length,
  cameraManualScenarios:results.filter(result=>/retained-behavior$/.test(result.kind||'')).length,
  seeds,sourceHashes:{'src/model.js':hash('src/model.js'),'src/main.js':hash('src/main.js')},
  cameraOpened:false,servicesOpened:false,realAppStorageAccessed:false,actualProjectFilesWritten:false,
  testMethod:'Actual main module in a VM; actual model and reducer; in-memory DOM/storage; inert clients/timers',
  failures:results.filter(result=>!result.passed),results};
writeFileSync(output,JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify({...summary,results:undefined,seeds:undefined}));
process.exitCode=summary.passed?0:1;
