import {cp,mkdir,access,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const source=fileURLToPath(new URL('../dist/',import.meta.url));
const target=fileURLToPath(new URL('../android/app/src/main/assets/web/',import.meta.url));
// Validate the build before replacing only this generated asset directory.
await access(new URL('../dist/index.html',import.meta.url));
await rm(target,{recursive:true,force:true});
await mkdir(target,{recursive:true});
await cp(source,target,{recursive:true});
console.log('Copied current production app into Fire OS assets. Next: cd android && ./gradlew assembleDebug');
