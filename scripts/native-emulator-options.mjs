import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
export const projectRoot=fileURLToPath(new URL('../',import.meta.url));
export const caseNames=['clear','frontal','nearface','right-negative','both-up-negative','natural-original','natural-mirror'];
export function nativeOptions(){
 const args=process.argv.slice(2),values={adb:'adb','adb-port':'5038',serial:'emulator-5556',model:'int8',refinement:'image',completion:'false',out:path.join(projectRoot,'verification-results/native-video')},cases=[];
 while(args.length){const a=args.shift();if(a.startsWith('--')){const key=a.slice(2);if(!Object.hasOwn(values,key)||!args.length||args[0].startsWith('--'))throw Error('Unknown or incomplete option: '+a);values[key]=args.shift();}else{if(!caseNames.includes(a))throw Error('Unknown frozen case: '+a);cases.push(a);}}
 if(!['int8','float16'].includes(values.model))throw Error('Unknown native model');
 if(!['image','tracked'].includes(values.refinement))throw Error('Unknown native refinement profile');
 if(!['false','true'].includes(values.completion))throw Error('Completion must be false or true');
 if(!/^emulator-[0-9]+$/.test(values.serial))throw Error('Only an emulator serial is permitted');
 const port=Number(values['adb-port']);if(!Number.isInteger(port)||port<1||port>65535)throw Error('Invalid ADB port');
 const run=promisify(execFile),prefix=['-P',String(port),'-s',values.serial];
 const adb=async a=>(await run(values.adb,[...prefix,...a],{timeout:20000,maxBuffer:8*1024*1024})).stdout;
 const out=path.resolve(values.out);fs.mkdirSync(out,{recursive:true});
 return {adb,out,model:values.model,refinement:values.refinement,completion:values.completion==='true',cases:cases.length?cases:caseNames,async guard(){if((await adb(['shell','getprop','ro.kernel.qemu'])).trim()!=='1')throw Error('Target is not a verified emulator');if((await adb(['shell','getprop','sys.boot_completed'])).trim()!=='1')throw Error('Emulator is not booted');}};
}
