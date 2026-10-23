#!/usr/bin/env node
// Build-time Polly integration. The shipped app reads bundled MP3s only.
import {spawnSync} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {existsSync,readFileSync,writeFileSync,mkdirSync,renameSync,openSync,closeSync,unlinkSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {challenges} from '../src/model.js';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const RATE_MICROS=16; // Neural speech: $16 per million characters; no free-tier assumption.
export const usdToMicros=value=>{
  if(!/^\d+(\.\d{1,6})?$/.test(String(value)))throw new Error('USD amount must be nonnegative with at most six decimals');
  const [whole,fraction='']=String(value).split('.');
  const result=Number(whole)*1e6+Number(fraction.padEnd(6,'0'));
  if(!Number.isSafeInteger(result))throw new Error('USD amount is too large');
  return result;
};
const dollars=micros=>(micros/1e6).toFixed(6);
const hash=content=>createHash('sha256').update(content).digest('hex');
const readJson=file=>JSON.parse(readFileSync(file,'utf8'));
function atomicJson(file,value){const temp=`${file}.${randomUUID()}.tmp`;writeFileSync(temp,JSON.stringify(value,null,2)+'\n');renameSync(temp,file);}
export function entries(){return challenges.flatMap(c=>['seated','standing'].flatMap(mode=>c[mode].map((text,phase)=>({id:`${c.id}-${mode}-${phase}`,text}))));}
function requestPayload(text){return {Engine:'neural',LanguageCode:'en-US',OutputFormat:'mp3',SampleRate:'24000',Text:text,TextType:'text',VoiceId:'Joanna'};}
function validateLedger(ledger){
  if(ledger.schemaVersion!==1||!Array.isArray(ledger.requests)||ledger.requests.some(r=>!Number.isSafeInteger(r.reservedMicros)||r.reservedMicros<0))throw new Error('Invalid local usage ledger');
}
export async function generate({promptEntries=entries(),outDir=path.join(ROOT,'public/audio/prompts'),ledgerPath,priorMicros=0,maxTotalMicros=1e6,maxNewMicros=1e5,profile='default',apply=false,runner}){
  if(!ledgerPath)throw new Error('An explicit ignored ledger path is required');
  if(!Number.isSafeInteger(priorMicros)||priorMicros<0||!Number.isSafeInteger(maxTotalMicros)||maxTotalMicros<0||!Number.isSafeInteger(maxNewMicros)||maxNewMicros<0)throw new Error('Invalid budget');
  if(new Set(promptEntries.map(e=>e.id)).size!==promptEntries.length||promptEntries.some(e=>!/^[-a-z0-9]+$/.test(e.id)||typeof e.text!=='string'||!e.text.length||e.text.length>3000))throw new Error('Invalid prompt entries');
  const plannedMicros=promptEntries.reduce((sum,e)=>sum+e.text.length*RATE_MICROS,0);
  if(!apply)return {dryRun:true,clips:promptEntries.length,upperBoundNewUsd:dollars(plannedMicros),priorUsd:dollars(priorMicros),maxTotalUsd:dollars(maxTotalMicros)};
  mkdirSync(path.dirname(ledgerPath),{recursive:true});
  const lockPath=ledgerPath+'.lock';let lock;
  try{lock=openSync(lockPath,'wx',0o600);}catch{throw new Error('Usage ledger is locked; no request sent');}
  try{
    const ledger=existsSync(ledgerPath)?readJson(ledgerPath):{schemaVersion:1,rateUsdPerMillionCharacters:16,requests:[]};
    validateLedger(ledger);
    mkdirSync(outDir,{recursive:true});
    const clips=[];
    for(const entry of promptEntries){
      const payload=requestPayload(entry.text),cacheKey=hash(JSON.stringify({region:'us-west-2',...payload}));
      const target=path.join(outDir,entry.id+'.mp3');
      let record=ledger.requests.findLast(r=>r.id===entry.id&&r.cacheKey===cacheKey&&r.status!=='reviewed-cli-validation-failure');
      if(record){
        if(record.status!=='completed')throw new Error('A previous request has uncertain or failed billing; review the retained reservation before retrying');
        if(!existsSync(target)||hash(readFileSync(target))!==record.sha256)throw new Error('Cached audio integrity mismatch; no request sent');
      }else{
        const reservedMicros=entry.text.length*RATE_MICROS;
        const used=ledger.requests.reduce((sum,r)=>sum+r.reservedMicros,0);
        if(used+reservedMicros>maxNewMicros||priorMicros+used+reservedMicros>maxTotalMicros)throw new Error('Polly budget would be exceeded; no request sent');
        record={id:entry.id,cacheKey,status:'reserved',reservedMicros,startedAtUtc:new Date().toISOString(),automaticRetries:0};
        ledger.requests.push(record);atomicJson(ledgerPath,ledger);
        const temp=target+'.'+randomUUID()+'.tmp';
        let response;
        try{
          const args=['--profile',profile,'--region','us-west-2','polly','synthesize-speech','--engine',payload.Engine,'--language-code',payload.LanguageCode,'--output-format',payload.OutputFormat,'--sample-rate',payload.SampleRate,'--text',payload.Text,'--text-type',payload.TextType,'--voice-id',payload.VoiceId,'--output','json','--no-cli-pager','--cli-read-timeout','30','--cli-connect-timeout','10',temp];
          response=runner?await runner(args,temp):spawnSync('aws',args,{encoding:'utf8',timeout:45000,env:{...process.env,AWS_MAX_ATTEMPTS:'1',AWS_RETRY_MODE:'standard',AWS_CLI_AUTO_PROMPT:'off'}});
          if(response.status!==0||response.error)throw new Error('AWS synthesis did not complete');
          const metadata=JSON.parse(response.stdout);
          if(!Number.isInteger(metadata.RequestCharacters)||metadata.RequestCharacters<0||metadata.RequestCharacters>entry.text.length||metadata.ContentType!=='audio/mpeg')throw new Error('Unexpected Polly receipt');
          const bytes=readFileSync(temp);if(bytes.length<100)throw new Error('Polly returned empty audio');
          Object.assign(record,{status:'completed',completedAtUtc:new Date().toISOString(),requestCharacters:metadata.RequestCharacters,sha256:hash(bytes),bytes:bytes.length});
          renameSync(temp,target);atomicJson(ledgerPath,ledger);
        }catch(error){
          Object.assign(record,{status:'uncertain-reservation-retained',failureType:error.name,awsCliExitStatus:response?.status??null,serviceErrorCode:response?.stderr?.match(/\(([A-Za-z][A-Za-z0-9_-]{0,60})\)/)?.[1]??null});atomicJson(ledgerPath,ledger);
          throw new Error('Polly request failed or was interrupted; reservation retained, no automatic retry');
        }
      }
      clips.push({id:entry.id,text:entry.text,file:entry.id+'.mp3',sha256:record.sha256,bytes:record.bytes,requestCharacters:record.requestCharacters,generatedAtUtc:record.completedAtUtc});
    }
    const provenance={schemaVersion:1,service:'Amazon Polly',engine:'neural',voice:'Joanna',language:'en-US',region:'us-west-2',sampleRate:24000,integration:'Build-time synthesis; offline bundled playback; no user input is sent to AWS',pricingUrl:'https://aws.amazon.com/polly/pricing/',clips};
    atomicJson(path.join(outDir,'provenance.json'),provenance);
    return {clips:clips.length,reservedNewUsd:dollars(ledger.requests.reduce((sum,r)=>sum+r.reservedMicros,0)),priorUsd:dollars(priorMicros),provenance:path.join(outDir,'provenance.json')};
  }finally{closeSync(lock);unlinkSync(lockPath);}
}

async function main(){
  const args=process.argv.slice(2),value=key=>{const i=args.indexOf(key);return i<0?undefined:args[i+1];};
  const priorFile=value('--prior-ledger');
  if(!priorFile)throw new Error('--prior-ledger is required to include previous narration spend');
  const prior=readJson(priorFile);
  const declared=usdToMicros(prior.totalCostUpperBoundUsd);
  const sum=prior.requests.reduce((s,r)=>s+usdToMicros(r.actualCostUpperBoundUsd??r.reservedCostUsd),0);
  const result=await generate({ledgerPath:value('--ledger'),priorMicros:Math.max(declared,sum),profile:value('--profile')??'default',maxTotalMicros:usdToMicros(value('--max-total-usd')??'1'),maxNewMicros:usdToMicros(value('--max-new-usd')??'0.10'),apply:args.includes('--apply')});
  console.log(JSON.stringify(result));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(error=>{console.error(error.message);process.exitCode=1;});
