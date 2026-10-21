import {defineConfig} from '@playwright/test';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const project=fileURLToPath(new URL('.',import.meta.url));
const output=fileURLToPath(new URL('./test-results/browser/',import.meta.url));
const chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browserPath=process.env.TOGETHERMOVE_BROWSER_PATH||(existsSync(chrome)?chrome:undefined);
const baseline=process.env.TOGETHERMOVE_BASELINE_DIR;
export default defineConfig({
  timeout:150000,workers:1,fullyParallel:false,
  outputDir:`${output}artifacts`,
  reporter:[['list'],['json',{outputFile:`${output}${process.env.TOGETHERMOVE_QA_REPORT||'results.json'}`}]],
  use:{baseURL:'http://127.0.0.1:4173',viewport:{width:1920,height:1080},
    launchOptions:browserPath?{executablePath:browserPath}:{},
    trace:'retain-on-failure',screenshot:'only-on-failure'},
  webServer:{command:'npm run dev',url:'http://127.0.0.1:4173',reuseExistingServer:true},
  projects:[
    {name:'journey',testDir:'tests/browser',testMatch:'app.spec.js'},
    {name:'motion',testDir:'tests/browser',testMatch:'motion.spec.js'},
    {name:'live-synthetic',testDir:'tests/browser',testMatch:'motion-live.spec.js'},
    ...(baseline?[{name:'baseline-regression',testDir:path.resolve(project,baseline),testMatch:'baseline.mac.spec.mjs'}]:[]),
  ],
});
