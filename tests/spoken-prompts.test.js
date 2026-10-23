import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSpokenPrompts,promptPath,manualPromptContext} from '../src/spoken-prompts.js';

const context=(overrides={})=>({active:true,challenge:'wake',mode:'seated',phase:0,...overrides});
function harness(play=()=>Promise.resolve()){
  const clips=[],messages=[];
  const controller=createSpokenPrompts({onStatus:value=>messages.push(value),createAudio:src=>{
    const clip={src,currentTime:4,paused:0,play, pause(){this.paused++;}};clips.push(clip);return clip;
  }});
  return {controller,clips,messages};
}

test('spoken prompts start off and only permit bundled known manual cue paths',()=>{
  const {controller,clips}=harness();controller.sync(context());assert.equal(clips.length,0);
  assert.equal(controller.enabled,false);
  for(const invalid of [{challenge:'../secret'},{mode:'camera'},{phase:-1},{phase:3},{phase:1.5}])assert.equal(promptPath(context(invalid)),null);
  assert.equal(promptPath(context({challenge:'rain',mode:'standing',phase:2})),'./audio/prompts/rain-standing-2.mp3');
});

test('one clip per phase; phase, position and challenge changes stop the old cue',()=>{
  const {controller,clips}=harness();controller.setEnabled(true);
  controller.sync(context());controller.sync(context());assert.equal(clips.length,1);
  for(const update of [{phase:1},{phase:1,mode:'standing'},{challenge:'sun',mode:'standing',phase:1}]){
    const old=clips.at(-1);controller.sync(context(update));assert.equal(old.paused,1);assert.equal(old.currentTime,0);
  }
  assert.equal(clips.length,4);assert.equal(clips.at(-1).src,'./audio/prompts/sun-standing-1.mp3');
});

test('pause, leaving manual play and disabling stop; resume restarts the current cue',()=>{
  const {controller,clips}=harness();controller.setEnabled(true);controller.sync(context({phase:2}));
  controller.sync(context({active:false,phase:2}));assert.equal(clips[0].paused,1);
  controller.sync(context({phase:2}));assert.equal(clips.length,2);assert.equal(clips[1].src,clips[0].src);
  controller.setEnabled(false);assert.equal(clips[1].paused,1);controller.sync(context());assert.equal(clips.length,2);
  controller.setEnabled(true);controller.sync(context({active:false}));assert.equal(clips.length,2);
});

test('blocked playback and missing clips expose useful text without throwing',async()=>{
  const blocked=Object.assign(new Error('blocked'),{name:'NotAllowedError'});
  const {controller,clips}=harness(()=>Promise.reject(blocked));controller.setEnabled(true);controller.sync(context());
  await Promise.resolve();assert.match(controller.message,/Sound was blocked/);
  controller.sync(context());assert.equal(clips.length,1,'failed clip must not retry every animation frame');
  controller.setEnabled(false);controller.setEnabled(true);controller.sync(context());assert.equal(clips.length,2);
  clips[1].onerror();assert.match(controller.message,/manual play still works/);
  await Promise.resolve();controller.stop();
});

test('late failures from stopped clips cannot replace the current status',async()=>{
  let reject;const pending=new Promise((_,fail)=>{reject=fail;});
  const {controller}=harness(()=>pending);controller.setEnabled(true);controller.sync(context());controller.setEnabled(false);
  reject(new Error('old clip'));await Promise.resolve();assert.match(controller.message,/prompts off/);
});

test('audio constructor errors keep the game usable and report unavailable audio',()=>{
  const controller=createSpokenPrompts({createAudio(){throw Error('unsupported');}});
  controller.setEnabled(true);assert.doesNotThrow(()=>controller.sync(context()));assert.match(controller.message,/manual play still works/);
});

test('app contexts stop audio on pause, position change, camera play and leaving the round',()=>{
  const state={screen:'play',inputMode:'manual',challenge:'sun',mode:'seated',elapsed:12,paused:false};
  const {controller,clips}=harness();controller.setEnabled(true);controller.sync(manualPromptContext(state));
  assert.equal(clips[0].src,'./audio/prompts/sun-seated-1.mp3');
  for(const change of [{paused:true},{mode:'standing',paused:true},{inputMode:'camera'},{screen:'check'},{screen:'home'}]){
    controller.sync(manualPromptContext({...state,...change}));assert.equal(clips.at(-1).paused,1);
    controller.sync(manualPromptContext(state));
  }
  controller.sync(manualPromptContext({...state,mode:'standing',elapsed:22}));
  assert.equal(clips.at(-1).src,'./audio/prompts/sun-standing-2.mp3');
});
