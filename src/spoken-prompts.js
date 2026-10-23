import {challenges,phaseAt} from './model.js';

const ready='Spoken prompts on. The current instruction plays during manual play.';
const off='Spoken prompts off. Follow the words on screen.';

export function manualPromptContext({screen,inputMode,challenge,mode,elapsed,paused}){
  return {active:screen==='play'&&inputMode==='manual'&&!paused,challenge,mode,phase:phaseAt(elapsed)};
}

// AWS Polly prepares these bundled clips at build time. Playback never calls AWS.
export function promptPath({challenge,mode,phase}){
  if(!challenges.some(item=>item.id===challenge)||!['seated','standing'].includes(mode)||!Number.isInteger(phase)||phase<0||phase>2)return null;
  return `./audio/prompts/${challenge}-${mode}-${phase}.mp3`;
}

export function createSpokenPrompts({createAudio=src=>new Audio(src),onStatus=()=>{}}={}){
  let enabled=false,audio=null,current=null,generation=0,message=off;
  function status(value){if(message!==value){message=value;onStatus(value);}}
  function stop(){
    generation++;current=null;
    if(audio){audio.onerror=null;audio.onended=null;audio.pause();try{audio.currentTime=0;}catch{}audio=null;}
  }
  function fail(error,token){
    if(token!==generation)return;
    status(error?.name==='NotAllowedError'?'Sound was blocked. Turn spoken prompts off and on to retry, or follow the words on screen.':'Spoken audio is unavailable. Follow the words on screen; manual play still works.');
  }
  return {
    get enabled(){return enabled;},
    get message(){return message;},
    setEnabled(value){enabled=Boolean(value);stop();status(enabled?ready:off);},
    sync(context){
      const path=promptPath(context);
      if(!enabled||!context.active||!path){stop();return;}
      if(current===path)return;
      stop();current=path;const token=generation;
      try{
        audio=createAudio(path);audio.preload='auto';
        audio.onerror=()=>fail(null,token);
        const playing=audio.play();
        status(ready);
        playing?.catch(error=>fail(error,token));
      }catch(error){fail(error,token);}
    },
    stop,
  };
}
