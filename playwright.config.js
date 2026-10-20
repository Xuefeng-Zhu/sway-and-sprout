import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';

const browserPath=process.env.TOGETHERMOVE_BROWSER_PATH;
const output=fileURLToPath(new URL('./test-results/browser/',import.meta.url));
export default defineConfig({
  testDir:'tests/browser',timeout:150000,
  outputDir:`${output}artifacts`,
  reporter:[['list'],['json',{outputFile:`${output}results.json`}]],
  use:{baseURL:'http://127.0.0.1:4173',viewport:{width:1920,height:1080},
    launchOptions:browserPath?{executablePath:browserPath}:{}},
  webServer:{command:'npm run dev',url:'http://127.0.0.1:4173',reuseExistingServer:true},
});
