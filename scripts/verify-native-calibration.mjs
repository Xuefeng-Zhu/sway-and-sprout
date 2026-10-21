import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';

const project=fileURLToPath(new URL('../',import.meta.url));
const values={adb:'adb','adb-port':'5038',serial:'emulator-5556',model:'float16',split:'calibration',manifest:'',sha256:'',out:path.join(project,'verification-results/native-calibration')};
const args=process.argv.slice(2);
while(args.length){const option=args.shift();if(!option.startsWith('--')||!Object.hasOwn(values,option.slice(2))||!args.length||args[0].startsWith('--'))throw Error('Unknown/incomplete calibration option');values[option.slice(2)]=args.shift();}
if(!/^emulator-[0-9]+$/.test(values.serial))throw Error('Only emulator serials are permitted');
if(!['calibration','heldout'].includes(values.split)||!['int8','float16'].includes(values.model))throw Error('Unknown split/model');
const port=Number(values['adb-port']);if(!Number.isInteger(port)||port<1||port>65535)throw Error('Invalid ADB port');
if(!values.manifest||!(/^[0-9a-f]{64}$/).test(values.sha256))throw Error('Frozen manifest path and SHA256 required');
const bytes=fs.readFileSync(values.manifest),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
if(bytes.length>4194304||hash(bytes)!==values.sha256)throw Error('Frozen manifest mismatch');
const manifest=JSON.parse(bytes),images=manifest.images?.filter(row=>row.split===values.split);
if(manifest.schemaVersion!==1||!images?.length||images.length>1000)throw Error('Frozen split unavailable');
const expected=new Map(images.map(row=>[row.id,row]));if(expected.size!==images.length)throw Error('Duplicate frozen image id');
const modelHash=values.model==='float16'?'0fac2226112d0371903ca86e3853cec24ef603a0b2f96f589b180f0ebdd135ab':'cd7cc22fa946e5d146a7b98d496853e1923e22828d3972d579973f27f91bb105';
const run=promisify(execFile),adb=async args=>(await run(values.adb,['-P',String(port),'-s',values.serial,...args],{timeout:20000,maxBuffer:12*1024*1024})).stdout;
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const runId=crypto.randomUUID(),result={startedAt:new Date().toISOString(),runId,manifestSha256:values.sha256,model:values.model,modelSha256:modelHash,split:values.split,cameraUsed:false,physicalDevice:false,fireOSVerified:false,macInference:false,records:[]};
fs.mkdirSync(values.out,{recursive:true});let guarded=false;
try{
 if((await adb(['shell','getprop','ro.kernel.qemu'])).trim()!=='1'||(await adb(['shell','getprop','sys.boot_completed'])).trim()!=='1')throw Error('Target is not a booted emulator');guarded=true;
 result.device={api:(await adb(['shell','getprop','ro.build.version.sdk'])).trim(),abi:(await adb(['shell','getprop','ro.product.cpu.abi'])).trim()};
 await adb(['shell','am','force-stop','com.togethermove.tv.motion']);
 await adb(['shell','am','start','-W','-n','com.togethermove.tv.motion/com.togethermove.tv.NativeCalibrationActivity','--es','calibrationRunId',runId,'--es','calibrationSplit',values.split,'--es','nativeModel',values.model]);
 const started=Date.now();let closed;const collected=new Map();
 while(Date.now()-started<300000){
  const text=await adb(['logcat','-d','-s','SwayCalibration:I']);
  for(const line of text.split('\n')){
   let row;try{row=JSON.parse(line.slice(line.indexOf('{')));}catch{continue;}
   if(row.runId!==runId)continue;
   const key=row.kind+':'+(row.kind==='sample'?row.id:'');
   const previous=collected.get(key);
   if(previous&&JSON.stringify(previous)!==JSON.stringify(row))throw Error('Conflicting duplicate native record: '+key);
   collected.set(key,row);
  }
  const records=[...collected.values()];result.records=records;
  if(records.some(row=>row.kind==='failure'))throw Error('Native calibration failure: '+records.find(row=>row.kind==='failure').reason);
  closed=records.find(row=>row.kind==='closed');if(closed)break;
  await wait(400);
 }
 if(!closed)throw Error('Bounded native calibration timeout');
 const startedRow=result.records.find(row=>row.kind==='started'),finished=result.records.find(row=>row.kind==='finished'),samples=result.records.filter(row=>row.kind==='sample');
 if(!startedRow||!finished||!closed.complete||closed.resourcesClosed!==true||closed.cancelled||samples.length!==expected.size||startedRow.expectedSamples!==expected.size||finished.samples!==expected.size||closed.samples!==expected.size)throw Error('Incomplete dataset/cleanup');
 const seen=new Set();
 for(const row of result.records){if(row.manifestSha256!==values.sha256||row.datasetId!=='dataset-'+values.sha256.slice(0,16)||row.modelId!==values.model||row.modelSha256!==modelHash||row.inputSize!==192||row.split!==values.split||row.engine!=='litert'||row.engineVersion!=='1.4.2'||row.profile!=='image'||row.modelInferencesPerImage!==3||row.referenceCalls!==0||row.cameraEnabled!==false||row.scoringEnabled!==false)throw Error('Actual native identity/profile mismatch');}
 for(const row of samples){const image=expected.get(row.id);if(!image||seen.has(row.id)||row.imageSha256!==image.sha256||row.width!==image.width||row.height!==image.height)throw Error('Actual source-image mismatch');seen.add(row.id);
  for(const name of ['leftShoulder','rightShoulder','leftWrist','rightWrist']){const p=row[name];if(!p||![p.x,p.y,p.score].every(Number.isFinite)||p.score<0||p.score>1)throw Error('Invalid actual keypoint');}}
 result.status='passed';result.samples=samples.length;result.resourcesClosed=true;result.sampleEvidenceScope='Actual in-process NativeMoveNet three-pass image outputs; no gesture/UI or camera acceptance';
}catch(error){result.status='failed';result.error=error.message;process.exitCode=1;}
finally{if(guarded)await adb(['shell','am','force-stop','com.togethermove.tv.motion']).catch(()=>{});result.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(values.out,'result-'+values.split+'.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,split:values.split,samples:result.samples,error:result.error,resourcesClosed:result.resourcesClosed}));}
