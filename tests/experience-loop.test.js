import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as model from '../src/model.js';
import {createMotionState,acceptMotionEvent} from '../src/motion.js';
import {roundTickDelta} from '../src/round-clock.js';
import {gardenMarkup} from '../src/garden-view.js';

// Run the actual navigation, completion and persistence code in memory. These
// are functional fixtures: no browser, service, capture, media or real clock.
function journey({search='', completed=['wake'], sessions=3, performanceNow=1000, saveFails=false}={}) {
  let callbacks, nextId=0, previewStarts=0;
  const writes=[], nodes={};
  const initial=JSON.stringify({completed,sessions},null,2)+'\n';
  let stored=initial;
  const focusTarget={focus(){},dataset:{action:'start'}};
  const root={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>focusTarget};
  const sandbox={...model,createMotionState,acceptMotionEvent,roundTickDelta,gardenMarkup,
    URLSearchParams,location:{search},
    createMotionClient:options=>{callbacks=options;return {start(){},stop(){}};},
    createPreviewClient:()=>({start(){previewStarts++;},stop(){}}),
    sunshineMarkup:()=>'',updateSunshine(){},updateCameraPreview(){},
    document:{activeElement:focusTarget,
      querySelector:selector=>selector==='#app'?root:nodes[selector]||= {
        textContent:'',style:{},classList:{toggle(){}}},
      addEventListener(){},dispatchEvent(){}},
    window:{addEventListener(){}},
    localStorage:{getItem:()=>stored,setItem:(key,value)=>{if(saveFails)throw Error('Fixture storage write refused');writes.push([key,value]);stored=value;}},
    crypto:{randomUUID:()=>`synthetic-round-${++nextId}`},
    performance:{now:()=>performanceNow},requestAnimationFrame:()=>1,cancelAnimationFrame(){},
  };
  const source=readFileSync(new URL('../src/main.js',import.meta.url),'utf8')
    .replace(/^import .*;\n/gm,'');
  const hooks=`\nglobalThis.journeyHooks={act,back,tick,
    read:()=>({screen,progress,roundId,revision,motion,elapsed,paused,manualCount,selected,journeyCompleted,harvestClaimed}),
    timing:()=>window.togetherMoveTiming(),
    end:()=>{elapsed=roundSeconds();tick(last===null?0:last);}};`;
  vm.runInNewContext(source+hooks,sandbox);
  const api=sandbox.journeyHooks;
  return {api,root,writes,initial,get stored(){return stored;},
    get context(){return callbacks.getContext();},get previewStarts(){return previewStarts;},
    startCamera(){api.act('choose:1');api.act('input:camera');api.act('start');},
    send(source,{rays=0,verified=true}={}) {
      const context=callbacks.getContext(), activity=context.policy==='activity';
      callbacks.onPacket({protocol:1,...context,source,streamId:'synthetic-experience-stream',
        runtime:{opencv:'5.0.0',verified,source},status:'tracking',
        expected:activity?'any':'left',heldMs:0,seq:rays,
        events:Array.from({length:rays},(_,i)=>({seq:i+1,roundId:context.roundId,
          gesture:activity?'activity':i%2?'right-raise':'left-raise',confidence:1,ageMs:0})),
        metrics:{armed:true}});
    },
  };
}

function unchanged(app) {
  assert.equal(app.writes.length,0,'Test inputs must never write participation');
  assert.equal(app.stored,app.initial,'The original saved bytes must be retained');
}

function diagnosticResult(app, source) {
  assert.match(app.root.innerHTML,source==='synthetic'?/SYNTHETIC TEST/i:/VIDEO REPLAY/i);
  assert.match(app.root.innerHTML,/saved garden (?:is )?unchanged|garden progress is unchanged|does not change your saved garden/i);
  assert.match(app.root.innerHTML,new RegExp(`<b>${app.api.read().motion.count}/6 simulated rays</b>`));
  assert.doesNotMatch(app.root.innerHTML,/data-action="(?:restart|next|harvest)"/);
  assert.doesNotMatch(app.root.innerHTML,/Your garden is saved on this device|Saved on this device\.|One lovely thing you did together|Manual: we joined in|Manual · self-reported · no camera/i);
}

function confirmDiagnostic(app, source) {
  if(app.api.read().screen!=='check')return;
  assert.match(app.root.innerHTML,source==='synthetic'?/SYNTHETIC TEST/i:/VIDEO REPLAY/i);
  assert.doesNotMatch(app.root.innerHTML,/Manual: we joined in|We joined in ✦|YOUR MOMENT, YOUR SAY|Manual · self-reported · no camera/i);
  app.api.act('complete');
}

function assertManualProvenance(app) {
  const label='Manual · self-reported · no camera',html=app.root.innerHTML;
  assert.equal(html.split(label).length-1,1,'Manual provenance is rendered once');
  const node=html.match(/<([a-z][\w-]*)\b([^>]*)>Manual · self-reported · no camera<\/\1>/i);
  assert.ok(node,'Manual provenance is rendered as readable text');
  assert.doesNotMatch(node[2],/\bhidden\b|aria-hidden=["']true/i);
}

function confirmManualVisit(app) {
  app.api.act('choose:0');
  for(let index=0;index<3;index++){
    app.api.act('start');
    for(let count=0;count<6;count++)app.api.act('manual-count');
    app.api.act('finish-moment');app.api.act('complete');
    if(index<2)app.api.act('next');
  }
}

test('explicit recorded diagnostic cannot become saved participation when no packet arrives',()=>{
  const app=journey({search:'?input=video-verification'});
  app.startCamera();app.api.end();
  assert.equal(app.api.read().screen,'check');
  assert.match(app.root.innerHTML,/VIDEO REPLAY/i);
  assert.doesNotMatch(app.root.innerHTML,/Manual: we joined in/i);
  app.api.act('complete');
  assert.equal(app.api.read().screen,'celebrate');
  diagnosticResult(app,'video');unchanged(app);
  app.api.act('start');app.api.end();app.api.act('complete');
  diagnosticResult(app,'video');unchanged(app);
  app.api.act('home');unchanged(app);
});

test('an unverified packet cannot replace the explicit recorded round origin or authorize a reward',()=>{
  for(const source of ['video','camera']) {
    const app=journey({search:'?input=video-verification'});app.startCamera();
    app.send(source,{rays:6,verified:false});
    assert.equal(app.api.read().motion.count,0);
    if(app.api.read().paused)app.api.act('pause');
    app.api.end();app.api.act('complete');
    diagnosticResult(app,'video');unchanged(app);
  }
});

test('synthetic zero/six-ray results and their replay/home actions preserve every saved garden',()=>{
  for(const completed of [[],['wake'],['wake','sun','rain']]) {
    for(const rays of [0,6]) {
      const app=journey({completed});app.startCamera();app.send('synthetic',{rays});
      app.api.end();
      confirmDiagnostic(app,'synthetic');
      assert.equal(app.api.read().screen,'celebrate');
      diagnosticResult(app,'synthetic');unchanged(app);
      // The primary repeat action starts another diagnostic, never a garden reset.
      assert.match(app.root.innerHTML,/data-action="start"/);
      app.api.act('start');app.send('synthetic',{rays});app.api.end();
      confirmDiagnostic(app,'synthetic');
      diagnosticResult(app,'synthetic');unchanged(app);
      app.api.act('home');unchanged(app);
    }
  }
});

test('manual fallback inside a synthetic round retains the original test provenance',()=>{
  const app=journey({completed:['wake','sun','rain']});
  app.startCamera();app.send('synthetic');app.api.act('manual');
  app.api.act('pause');app.api.end();confirmDiagnostic(app,'synthetic');
  diagnosticResult(app,'synthetic');unchanged(app);
});

test('growing again keeps earned garden moments instead of erasing participation',()=>{
  const app=journey({completed:['wake','sun','rain'],sessions:8});
  app.api.act('choose:0');app.api.act('start');app.api.end();app.api.act('complete');
  assert.equal(app.api.read().screen,'celebrate');
  app.api.act('restart');
  assert.equal(app.api.read().screen,'setup');
  assert.deepEqual(Array.from(app.api.read().progress.completed),['wake','sun','rain']);
  assert.deepEqual(JSON.parse(app.stored).completed,['wake','sun','rain']);
  assert.match(app.root.innerHTML,/data-action="start"/);
});

test('manual animation reaching its timer remains self-report and never saves automatically',()=>{
  const app=journey({completed:[]});app.api.act('choose:0');app.api.act('start');app.api.end();
  assert.equal(app.api.read().screen,'check');unchanged(app);
  assertManualProvenance(app);
  app.api.act('complete');
  assert.deepEqual(JSON.parse(app.stored).completed,['wake']);
  assert.equal(app.writes.length,1,'Only explicit self-report confirmation writes participation');
});

test('every manual moment renders one source label in activity and confirmation without saving early',()=>{
  for(let choice=0;choice<3;choice++){
    const app=journey({completed:[]});app.api.act('choose:'+choice);
    assert.match(app.root.innerHTML,/data-action="start"[^>]*>Start →<\/button>/);
    app.api.act('start');assertManualProvenance(app);
    assert.match(app.root.innerHTML,/<p id="manual-count" role="status" aria-live="polite">0 \/ 6 counted<\/p>/);
    app.api.act('manual-count');assertManualProvenance(app);
    assert.match(app.root.innerHTML,/>1 \/ 6 counted<\/p>/);unchanged(app);
    app.api.act('pause');assertManualProvenance(app);app.api.act('pause');
    app.api.end();assert.equal(app.api.read().screen,'check');assertManualProvenance(app);unchanged(app);
    app.api.act('complete');assert.equal(app.writes.length,1);
  }
});

test('camera consent stays inactive before Start and recorded setup discloses its diagnostic source',()=>{
  const camera=journey({completed:[]});camera.api.act('choose:1');camera.api.act('input:camera');
  assert.equal(camera.api.read().screen,'setup');assert.equal(camera.context.active,false);
  assert.equal(camera.previewStarts,0,'Selecting camera mode cannot start its preview');
  assert.match(camera.root.innerHTML,/data-action="start"[^>]*>Start camera →<\/button>/);
  assert.match(camera.root.innerHTML,/Camera.*off.*Start/i);
  assert.match(camera.root.innerHTML,/one (?:person|player)/i);
  assert.match(camera.root.innerHTML,/Frames.*(?:local|this device)/i);
  assert.match(camera.root.innerHTML,/not recorded|no recording|nothing is recorded/i);unchanged(camera);
  camera.api.act('start');assert.equal(camera.context.active,true);unchanged(camera);

  const replay=journey({search:'?input=video-verification',completed:[]});
  replay.api.act('choose:1');replay.api.act('input:camera');
  assert.equal(replay.context.active,false);assert.equal(replay.previewStarts,0);
  assert.match(replay.root.innerHTML,/data-action="start"[^>]*>Start replay →<\/button>/);
  assert.match(replay.root.innerHTML,/Bundled test · no camera/);
  assert.match(replay.root.innerHTML,/120(?:-second|s)/);
  assert.match(replay.root.innerHTML,/diagnostic/i);
  assert.match(replay.root.innerHTML,/no camera|does not open a camera/i);
  assert.match(replay.root.innerHTML,/does not.*change.*saved garden|saved garden.*unchanged/i);unchanged(replay);
});

test('failed local persistence keeps original bytes and renders failure instead of a saved claim',()=>{
  const app=journey({completed:[],saveFails:true});
  app.api.act('choose:0');app.api.act('start');app.api.end();app.api.act('complete');
  assert.equal(app.api.read().screen,'celebrate');
  assert.deepEqual(Array.from(app.api.read().progress.completed),['wake']);
  unchanged(app);
  assert.match(app.root.innerHTML,/Progress could not be saved on this device/);
  assert.doesNotMatch(app.root.innerHTML,/>Saved on this device\.</);
  app.api.act('help');app.api.act('return');
  assert.equal(app.api.read().screen,'celebrate');
  assert.match(app.root.innerHTML,/Progress could not be saved on this device/);unchanged(app);
});

test('actual RAF baseline tolerates a frame timestamp before the click clock and excludes pause time',()=>{
  const app=journey({completed:[],performanceNow:1000});
  app.api.act('choose:0');app.api.act('start');
  // Browser RAF timestamps describe frame start and may precede performance.now()
  // sampled by the click handler. The first frame must only establish a baseline.
  assert.doesNotThrow(()=>app.api.tick(950));
  assert.equal(app.api.read().elapsed,0);
  assert.equal(app.api.timing().creditedMs,0);
  app.api.tick(1000);
  assert.equal(app.api.read().elapsed,.05);
  app.api.act('pause');
  app.api.tick(9000);
  assert.equal(app.api.read().elapsed,.05);
  app.api.act('pause');
  assert.doesNotThrow(()=>app.api.tick(10000));
  assert.equal(app.api.read().elapsed,.05,'The first resumed frame must not include the paused gap');
  app.api.tick(10050);
  assert.equal(app.api.read().elapsed,.1);
  assert.equal(app.api.timing().creditedMs,100);
  assert.equal(app.api.timing().wallMs,100);
  assert.equal(app.api.timing().stalledMs,0);
  unchanged(app);
});

test('manual counts require an active manual round, cap at six, and never save automatically',()=>{
  const app=journey({completed:[]});
  app.api.act('manual-count');assert.equal(app.api.read().manualCount,0);
  app.api.act('choose:0');app.api.act('manual-count');
  assert.equal(app.api.read().manualCount,0);
  app.api.act('start');
  const firstRound=app.api.read().roundId;
  app.api.act('finish-moment');assert.equal(app.api.read().screen,'play');
  app.api.act('pause');app.api.act('manual-count');
  assert.equal(app.api.read().manualCount,0);
  app.api.act('pause');
  for(let count=1;count<=6;count++){
    app.api.act('manual-count');assert.equal(app.api.read().manualCount,count);
    assert.equal(app.api.read().screen,'play');unchanged(app);
  }
  const cappedRevision=app.api.read().revision;
  for(let i=0;i<20;i++)app.api.act('manual-count');
  assert.equal(app.api.read().manualCount,6);
  assert.equal(app.api.read().revision,cappedRevision,'Ignored capped input must not create new control revisions');
  app.api.act('pause');app.api.act('finish-moment');
  assert.equal(app.api.read().screen,'play');
  app.api.act('pause');app.api.act('finish-moment');
  assert.equal(app.api.read().screen,'check');unchanged(app);
  app.api.act('start');
  assert.equal(app.api.read().manualCount,0);
  assert.notEqual(app.api.read().roundId,firstRound);
  unchanged(app);
  app.api.act('home');app.startCamera();app.api.act('manual-count');
  assert.equal(app.api.read().manualCount,0,'Camera mode cannot take manual-count credit');
  unchanged(app);
});

test('three confirmed manual moments lead to one harvest, and growing again keeps every bloom',()=>{
  const app=journey({completed:[],sessions:2});
  app.api.act('choose:0');
  for(let index=0;index<3;index++){
    app.api.act('start');
    for(let count=0;count<6;count++)app.api.act('manual-count');
    assert.equal(app.writes.length,index,'Counting movement alone never persists participation');
    app.api.act('finish-moment');
    assert.equal(app.api.read().screen,'check');
    assert.equal(app.writes.length,index);
    app.api.act('complete');
    assert.equal(app.api.read().screen,'celebrate');
    assert.equal(app.writes.length,index+1);
    assert.equal(app.api.read().journeyCompleted.length,index+1);
    if(index<2){
      app.api.act('harvest');
      assert.equal(app.api.read().screen,'celebrate','Harvest stays unavailable until all three moments are tended');
      assert.equal(app.writes.length,index+1);
      app.api.act('next');
    }
  }
  assert.match(app.root.innerHTML,/data-action="harvest"/);
  assert.deepEqual(Array.from(app.api.read().progress.completed),['wake','sun','rain']);
  const beforeHarvest=app.writes.length;
  app.api.act('harvest');
  assert.equal(app.api.read().screen,'harvest');
  assert.equal(app.writes.length,beforeHarvest+1);
  assert.equal(app.api.read().progress.sessions,3);
  const harvested=app.stored;
  app.api.act('harvest');
  assert.equal(app.writes.length,beforeHarvest+1);
  assert.equal(app.stored,harvested);
  app.api.act('restart');
  assert.equal(app.api.read().screen,'setup');
  assert.deepEqual(Array.from(app.api.read().journeyCompleted),[]);
  assert.deepEqual(Array.from(app.api.read().progress.completed),['wake','sun','rain']);
  assert.equal(app.stored,harvested,'Starting another visit never rewrites or clears the earned garden');
  app.api.act('start');assert.equal(app.api.read().manualCount,0);
});

test('an earned unclaimed harvest remains reachable from home and can only be claimed once',()=>{
  const app=journey({completed:[],sessions:2});
  confirmManualVisit(app);
  assert.equal(app.writes.length,3);
  assert.deepEqual(Array.from(app.api.read().journeyCompleted),['wake','sun','rain']);
  app.api.act('home');
  assert.match(app.root.innerHTML,/data-action="return-harvest"/);
  assert.doesNotMatch(app.root.innerHTML,/data-action="restart"/);
  const earned=app.stored;
  app.api.act('return-harvest');
  assert.equal(app.api.read().screen,'celebrate');
  assert.match(app.root.innerHTML,/data-action="harvest"/);
  assert.equal(app.writes.length,3,'Returning to an earned reward does not save again');
  assert.equal(app.stored,earned);
  app.api.act('harvest');
  assert.equal(app.api.read().screen,'harvest');
  assert.equal(app.api.read().progress.sessions,3);
  assert.equal(app.writes.length,4);
  const harvested=app.stored;
  app.api.act('harvest');
  assert.equal(app.writes.length,4);
  app.api.act('home');
  assert.match(app.root.innerHTML,/data-action="restart"/);
  assert.doesNotMatch(app.root.innerHTML,/data-action="return-harvest"/);
  app.api.act('return-harvest');
  assert.equal(app.api.read().screen,'home','A claimed reward cannot be reopened as unclaimed');
  app.api.act('restart');
  assert.equal(app.api.read().screen,'setup');
  assert.deepEqual(Array.from(app.api.read().journeyCompleted),[]);
  assert.deepEqual(Array.from(app.api.read().progress.completed),['wake','sun','rain']);
  assert.equal(app.stored,harvested);
  assert.equal(app.writes.length,4);
});

test('later diagnostics and their inactive callbacks cannot hide or relabel an earned harvest',()=>{
  for(const source of ['synthetic','video']){
    const app=journey({completed:[],sessions:2});
    confirmManualVisit(app);
    const earned=app.stored;
    app.startCamera();app.send(source,{rays:6});app.api.end();
    confirmDiagnostic(app,source);
    assert.equal(app.api.read().screen,'celebrate');
    diagnosticResult(app,source);
    assert.equal(app.writes.length,3,'A later diagnostic cannot save participation');
    assert.equal(app.stored,earned);
    assert.deepEqual(Array.from(app.api.read().journeyCompleted),['wake','sun','rain']);
    app.api.act('home');
    assert.match(app.root.innerHTML,/data-action="return-harvest"/);
    app.api.act('return-harvest');
    assert.match(app.root.innerHTML,/data-action="harvest"/);
    assert.doesNotMatch(app.root.innerHTML,/SIMULATED RAYS|TEST RESULT|REPLAY RESULT/i);
    // An outstanding poll can deliver a response after the screen has changed.
    // Even a packet matching the new inactive context cannot relabel this reward.
    app.send(source);
    app.api.act('help');app.api.act('return');
    assert.match(app.root.innerHTML,/data-action="harvest"/);
    assert.doesNotMatch(app.root.innerHTML,/SIMULATED RAYS|TEST RESULT|REPLAY RESULT/i);
    assert.equal(app.writes.length,3);
    assert.equal(app.stored,earned);
    app.api.act('harvest');
    assert.equal(app.api.read().screen,'harvest');
    assert.equal(app.writes.length,4);
    assert.equal(app.api.read().progress.sessions,3);
    const harvested=app.stored;
    app.api.act('harvest');
    assert.equal(app.writes.length,4);
    assert.equal(app.stored,harvested);
  }
});

test('help returns to setup or check and returns to a paused play round without losing counted growth',()=>{
  const app=journey({completed:[]});
  app.api.act('choose:0');app.api.act('mode:standing');app.api.act('help');
  app.api.act('help');app.api.act('return');
  assert.equal(app.api.read().screen,'setup','Repeated Help must not overwrite the return screen');
  app.api.act('start');app.api.act('manual-count');app.api.act('help');
  app.api.act('return');
  assert.equal(app.api.read().screen,'play');
  assert.equal(app.api.read().paused,true);
  assert.equal(app.api.read().manualCount,1);
  app.api.act('manual-count');assert.equal(app.api.read().manualCount,1);
  app.api.act('pause');app.api.end();app.api.act('help');app.api.back();
  assert.equal(app.api.read().screen,'check');unchanged(app);
});
