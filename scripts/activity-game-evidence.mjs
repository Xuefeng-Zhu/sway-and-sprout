#!/usr/bin/env node
// Offline adapter: real app/reducer/view code, in-memory DOM/storage, inert I/O.
// This is not a rendered browser or native-device test.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import readline from 'node:readline';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const plain=value=>JSON.parse(JSON.stringify(value));

export async function createActivityGameHarness(){
  const model=await import(pathToFileURL(path.join(project,'src/model.js')).href);
  const motionApi=await import(pathToFileURL(path.join(project,'src/motion.js')).href);
  const {roundTickDelta}=await import(pathToFileURL(path.join(project,'src/round-clock.js')).href);
  const {gardenMarkup}=await import(pathToFileURL(path.join(project,'src/garden-view.js')).href);
  const {sunshineMarkup,updateSunshine}=await import(pathToFileURL(path.join(project,'src/motion-view.js')).href);
  const nodes=new Map(),writes=[],raw='{"completed":["wake"],"sessions":5}\n';
  let stored=raw,callbacks,id=0;
  function element(name){
    if(nodes.has(name))return nodes.get(name);
    const classes=new Set(),properties={};
    const node={dataset:{},textContent:'',innerHTML:'',offsetWidth:400,
      style:{setProperty:(key,value)=>{properties[key]=value;}},
      properties,classes,classList:{toggle:(key,on)=>{if(on)classes.add(key);else classes.delete(key);},
        add:key=>classes.add(key),remove:key=>classes.delete(key)},focus(){},
      querySelector:selector=>element(selector),
      querySelectorAll:selector=>selector==='[data-ray]'?Array.from({length:6},(_,i)=>element(`ray-${i}`)):[]};
    nodes.set(name,node);return node;
  }
  const doc={querySelector:selector=>element(selector),querySelectorAll:()=>[],addEventListener(){},dispatchEvent(){}};
  element('meta[name="sway-garden-api"]').content=''; // No cloud endpoint, token, or network client in this adapter.
  element('.sunshine-garden').dataset.motionCount='0';
  // Imported view functions resolve document in this isolated Node process.
  globalThis.document=doc;
  const sandbox={...model,createMotionState:motionApi.createMotionState,acceptMotionEvent:motionApi.acceptMotionEvent,
    roundTickDelta,gardenMarkup,sunshineMarkup,updateSunshine,updateCameraPreview(){},
    createMotionClient:options=>{callbacks=options;return {start(){},stop(){}};},
    createPreviewClient:()=>({start(){},stop(){}}),
    URLSearchParams,location:{search:'?policy=activity'},document:doc,window:{addEventListener(){}},
    localStorage:{getItem:key=>key==='togethermove.v1'?stored:null,setItem:(key,value)=>{writes.push({key,value});if(key==='togethermove.v1')stored=value;}},
    crypto:{randomUUID:()=>`offline-activity-${++id}`},performance:{now:()=>0},
    requestAnimationFrame:()=>1,cancelAnimationFrame(){}};
  const main=readFileSync(path.join(project,'src/main.js'),'utf8');
  const hooks='\nglobalThis.evidenceHooks={act,read:()=>({motion,progress,screen,roundId,revision,clientId})};';
  vm.runInNewContext(main.replace(/^import .*;\n/gm,'')+hooks,sandbox,{timeout:1000});
  const api=sandbox.evidenceHooks;
  api.act('choose:1');api.act('input:camera');api.act('start');
  function snapshot(){
    const current=plain(api.read()),garden=element('.sunshine-garden');
    return {...current,context:plain(callbacks.getContext()),
      displayedCount:Number(element('#sunshine-count').textContent||0),
      growth:Number(garden.properties['--growth']||0),
      collectedRays:Array.from({length:6},(_,i)=>element(`ray-${i}`).classes.has('collected')).filter(Boolean).length,
      inputLabel:element('#camera-source').textContent,
      gameplayMarkupHasSunshineGarden:element('#app').innerHTML.includes('class="sunshine-garden"'),
      storedBytesUnchanged:stored===raw,storageWrites:writes.length};
  }
  return {context:()=>plain(callbacks.getContext()),snapshot,action:action=>{api.act(action);return snapshot();},
    receive(packet){
      if(!element('#app').innerHTML.includes('class="sunshine-garden"'))
        throw new Error('Actual app did not render the sunshine gameplay markup');
      const current=callbacks.getContext();
      for(const key of ['clientId','roundId','revision','mode','policy','active']){
        if(packet[key]!==current[key])throw new Error(`Packet context mismatch: ${key}`);
      }
      if(packet.source!=='video'||packet.runtime?.source!=='video'||packet.runtime?.verified!==true)
        throw new Error('Only explicitly verified video-source packets are accepted by this evidence adapter');
      callbacks.onPacket(packet);return snapshot();
    },
    finish(){api.act('home');return {...snapshot(),scope:'Actual cloud-disabled main/reducer/view code in a VM; inert clients, timers and in-memory DOM/storage',
      browserRendered:false,nativeRuntime:false,captureApisExposed:false,
      cloudEndpointConfigured:false,
      sourceHashes:Object.fromEntries(['src/main.js','src/motion.js','src/motion-view.js','src/model.js'].map(name=>
        [name,createHash('sha256').update(readFileSync(path.join(project,name))).digest('hex')]))};}};
}

async function main(){
  const app=await createActivityGameHarness();let packets=0;
  const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
  for await(const line of input){
    if(Buffer.byteLength(line,'utf8')>32768)throw new Error('Packet line exceeds 32 KiB');
    const request=JSON.parse(line);
    let result;
    if(request.op==='context')result={context:app.context()};
    else if(request.op==='packet'){
      if(++packets>512)throw new Error('Offline packet limit reached');
      result=app.receive(request.packet);
    }else if(request.op==='finish')result=app.finish();
    else throw new Error('Unknown offline evidence operation');
    process.stdout.write(JSON.stringify(result)+'\n');
    if(request.op==='finish'){input.close();break;}
  }
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main().catch(error=>{process.stderr.write(`${error.stack}\n`);process.exitCode=1;});
}
