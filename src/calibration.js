// Optional, bounded diagnostics. These never create events or change scoring.
const REASONS=new Set(['waiting','no-person','low-confidence','needs-neutral',
  'settling-neutral','ready','holding','wrong-side','both-raised','ambiguous',
  'cooldown','return-to-neutral','paused','camera-error','stale']);
const GATES=new Set(['up','down','transition','unknown']);
const POINTS=new Set(['person','leftShoulder','rightShoulder','leftWrist','rightWrist']);
const FIELDS=new Set(['reason','neutralMs','requiredNeutralMs','holdMs','requiredHoldMs',
  'gates','lowConfidence','minimumConfidence','fresh','ageMs']);
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const bounded=(value,max)=>Number.isInteger(value)&&value>=0&&value<=max;

export function sanitizeCalibration(value){
  if(!object(value)||Object.keys(value).length!==FIELDS.size||
    Object.keys(value).some(key=>!FIELDS.has(key))||!REASONS.has(value.reason)||
    typeof value.fresh!=='boolean'||
    !(value.ageMs===null||bounded(value.ageMs,60000))||
    (value.fresh&&(value.ageMs===null||value.ageMs>300))||
    !bounded(value.requiredNeutralMs,5000)||value.requiredNeutralMs===0||
    !bounded(value.requiredHoldMs,5000)||value.requiredHoldMs===0||
    !bounded(value.neutralMs,value.requiredNeutralMs)||!bounded(value.holdMs,value.requiredHoldMs)||
    !object(value.gates)||Object.keys(value.gates).length!==2||
    !GATES.has(value.gates.left)||!GATES.has(value.gates.right)||
    !Array.isArray(value.lowConfidence)||value.lowConfidence.length>POINTS.size||
    value.lowConfidence.some(key=>!POINTS.has(key))||
    new Set(value.lowConfidence).size!==value.lowConfidence.length||
    typeof value.minimumConfidence!=='number'||!Number.isFinite(value.minimumConfidence)||
    value.minimumConfidence<0||value.minimumConfidence>1)return null;
  return {reason:value.reason,neutralMs:value.neutralMs,requiredNeutralMs:value.requiredNeutralMs,
    holdMs:value.holdMs,requiredHoldMs:value.requiredHoldMs,
    gates:{left:value.gates.left,right:value.gates.right},
    lowConfidence:[...value.lowConfidence],minimumConfidence:value.minimumConfidence,
    fresh:value.fresh,ageMs:value.ageMs};
}

const pointLabels={person:'your position',leftShoulder:'your left shoulder',
  rightShoulder:'your right shoulder',leftWrist:'your left wrist',rightWrist:'your right wrist'};

export function calibrationFeedback(value,{expected='left',armed=false}={}){
  const c=sanitizeCalibration(value);
  if(!c)return null;
  const side=expected==='right'?'right':'left';
  const rest='Rest both arms below your shoulders. Wait for Ready.';
  const feedback=(label,detail,cue=detail)=>({label,detail,cue});
  if(!c.fresh&&['ready','holding','settling-neutral'].includes(c.reason))
    return feedback('Fresh frame needed','Rest both arms while waiting for a fresh camera frame.');
  switch(c.reason){
    case 'waiting':return feedback('Calibration waiting','Keep one person in view, with both wrists visible.',rest);
    case 'no-person':return feedback('Find your position','Face the camera with both shoulders and wrists in view.');
    case 'low-confidence':{
      const unclear=c.lowConfidence.map(key=>pointLabels[key]);
      return feedback('Visibility first',unclear.length>0&&unclear.length<=2?`Make ${unclear.join(' and ')} clear in the view.`:
        'Keep both shoulders and wrists clear in the view.');
    }
    case 'settling-neutral':return feedback(`Resting · ${(c.neutralMs/1000).toFixed(1)} / ${(c.requiredNeutralMs/1000).toFixed(1)}s`,
      'Keep both arms resting until Ready.');
    case 'ready':return armed?feedback('Ready',`Raise your ${side} hand above your shoulder. Hold briefly.`):feedback('Rest both arms',rest);
    case 'holding':return armed?feedback('Holding',`Hold your ${side} hand above your shoulder for a moment.`):feedback('Rest both arms',rest);
    case 'wrong-side':return feedback('Other hand next',`Rest both arms, then follow the ${side}-hand cue.`,rest);
    case 'both-raised':return feedback('Both hands are raised','Rest both arms below your shoulders before the next raise.');
    case 'cooldown':return feedback('A moment to rest','Rest both arms while the next cue gets ready.');
    case 'return-to-neutral':return feedback('Ray gathered','Rest both arms below your shoulders for the next cue.');
    case 'paused':return feedback('Paused','Camera paused. Rest both arms.');
    case 'camera-error':return feedback('Camera unavailable','Use manual play, or check the local camera connection.');
    case 'stale':return feedback('Fresh frame needed','Rest both arms while waiting for a fresh camera frame.');
    default:{
      const lower=['left','right'].filter(key=>c.gates[key]!=='down');
      const detail=lower.length===1?`Lower your ${lower[0]} wrist below its shoulder. Wait for Ready.`:rest;
      return feedback('Rest both arms',detail);
    }
  }
}
