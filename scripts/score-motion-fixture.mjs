#!/usr/bin/env node
// Semantic fixture replay only. This does not open a camera, render video, or save progress.
import {fileURLToPath, pathToFileURL} from 'node:url';
import path from 'node:path';

const here=path.dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2);
let modulePath=path.resolve(here,'../src/motion.js');
if(args.length){
  if(args.length!==2||args[0]!=='--module')throw new Error('Usage: score-motion-fixture.mjs [--module /path/to/src/motion.js]');
  modulePath=path.resolve(args[1]);
}
const {createMotionState,acceptMotionEvent,sameContext}=await import(pathToFileURL(modulePath).href);
let stdin='';
for await(const chunk of process.stdin)stdin+=chunk.toString('utf8');
const input=JSON.parse(stdin);
if(!['synthetic','video'].includes(input.source)||!Array.isArray(input.packets)){
  throw new Error('Explicit fixture source and packets are required.');
}
let state=createMotionState(input.roundId);
let eventDeliveries=0,ignoredPackets=0;
const acceptedGestures=[];
for(const packet of input.packets){
  // currentContext is optional: it models an arrival after the request epoch changed.
  // This uses the same exported epoch comparison as the real motion client.
  if(packet.source!==input.source||packet.roundId!==input.roundId||packet.active!==true||packet.runtime?.verified!==true||
    (packet.currentContext&&!sameContext(packet,packet.currentContext))){
    ignoredPackets++;
    continue;
  }
  for(const event of packet.events||[]){
    eventDeliveries++;
    const next=acceptMotionEvent(state,event,{active:true,now:input.nowMs??0});
    if(next.count>state.count)acceptedGestures.push(event.gesture);
    state=next;
  }
}
console.log(JSON.stringify({source:input.source,
  evidenceType:input.source==='synthetic'?'synthetic-landmark-events':'video-inference-events',
  physicalCameraUsed:false,privateProgressSaved:false,
  count:state.count,target:state.target,completed:state.completed,expected:state.expected,
  lastSeq:state.lastSeq,acceptedGestures,packetCount:input.packets.length,
  eventDeliveries,ignoredPackets}));
