import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {generate,usdToMicros,entries} from '../scripts/generate-spoken-prompts.mjs';
function fixture(t){const dir=mkdtempSync(path.join(os.tmpdir(),'sway-polly-'));t.after(()=>rmSync(dir,{recursive:true,force:true}));return {ledgerPath:path.join(dir,'usage.json'),outDir:path.join(dir,'audio'),apply:true,promptEntries:[{id:'wake-seated-0',text:'Sit comfortably.'}]};}
test('Polly cost parsing is exact and all 18 authored cues are present',()=>{
  assert.equal(usdToMicros('0.054720'),54720);assert.equal(entries().length,18);
  for(const v of ['-1','NaN','1e3','1.0000001'])assert.throws(()=>usdToMicros(v));
});
test('budget exhaustion prevents any provider call',async t=>{
  const opts=fixture(t);let calls=0;
  await assert.rejects(generate({...opts,priorMicros:999999,runner:()=>{calls++;}}),/budget/);assert.equal(calls,0);
});
test('completed output is verified and reused without another billed request',async t=>{
  const opts=fixture(t);let calls=0;
  const runner=(args,file)=>{calls++;assert.equal(args.includes('--cli-input-json'),false);for(const flag of ['--output-format','--text','--voice-id'])assert.ok(args.includes(flag));assert.equal(args[args.indexOf('--text')+1],'Sit comfortably.');writeFileSync(file,Buffer.alloc(150,1));return {status:0,stdout:JSON.stringify({RequestCharacters:16,ContentType:'audio/mpeg'})};};
  await generate({...opts,runner});await generate({...opts,runner});assert.equal(calls,1);
  const ledger=JSON.parse(readFileSync(opts.ledgerPath));assert.equal(ledger.requests.length,1);assert.equal(ledger.requests[0].status,'completed');
  writeFileSync(path.join(opts.outDir,'wake-seated-0.mp3'),'corrupt');
  await assert.rejects(generate({...opts,runner}),/integrity/);assert.equal(calls,1);
});
test('uncertain requests retain their reservation and are never automatically retried',async t=>{
  const opts=fixture(t);let calls=0;const runner=()=>{calls++;return {status:1,stdout:''};};
  await assert.rejects(generate({...opts,runner}),/reservation retained/);
  await assert.rejects(generate({...opts,runner}),/previous request/);assert.equal(calls,1);
  assert.equal(JSON.parse(readFileSync(opts.ledgerPath)).requests[0].reservedMicros,16*16);
});
test('concurrent writer is rejected before synthesis',async t=>{
  const opts=fixture(t);writeFileSync(opts.ledgerPath+'.lock','');let calls=0;
  await assert.rejects(generate({...opts,runner:()=>{calls++;}}),/locked/);assert.equal(calls,0);
});
