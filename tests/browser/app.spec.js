import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const output=process.env.TOGETHERMOVE_QA_OUTPUT_DIR
 ?path.resolve(process.env.TOGETHERMOVE_QA_OUTPUT_DIR)
 :fileURLToPath(new URL('../../test-results/browser/',import.meta.url));
test.use({viewport:{width:1280,height:720}});
const logs=new Map();

// All app contexts and storage are disposable Playwright fixtures. Synthetic
// protocol packets are mocked, not observations of a person or native runtime.
async function fixture(context,page,{saved=null}={}){
 const configured=new URL(test.info().project.use.baseURL||'http://127.0.0.1:4173');
 if(!['localhost','127.0.0.1','[::1]'].includes(configured.hostname))throw Error('Journey fixtures require a loopback app URL');
 const appOrigin=configured.origin;
 const mock={source:'synthetic',seq:0,status:'tracking',armed:true,events:[],requests:[],drop:false,streamId:'synthetic-journey-browser-fixture'};
 if(saved)await context.addInitScript(value=>localStorage.setItem('togethermove.v1',JSON.stringify(value)),saved);
 await context.addInitScript(()=>{
  window.__qaCameraCalls=0;
  if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=()=>{window.__qaCameraCalls++;throw Error('Camera forbidden in UI fixture');};
 });
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin!==appOrigin){await route.abort('blockedbyclient');return;}
  if(url.pathname==='/motion/events'){
   const control=Object.fromEntries(url.searchParams);mock.requests.push(control);
   if(mock.drop){await route.abort('failed');return;}
   const packet={protocol:1,clientId:control.clientId,roundId:control.roundId,revision:Number(control.revision),active:control.active==='1',mode:control.mode,policy:control.policy||'strict',runtime:{opencv:'5.0.0',verified:true,source:mock.source},source:mock.source,streamId:mock.streamId,status:mock.status,expected:control.policy==='activity'?'any':'left',heldMs:0,seq:mock.seq,events:mock.events.splice(0).map(item=>({roundId:control.roundId,...item})),metrics:{fps:0,armed:mock.armed}};
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(packet)});return;
  }
  if(url.pathname==='/motion/preview'){
   const c=Object.fromEntries(url.searchParams);
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({clientId:c.clientId,roundId:c.roundId,revision:Number(c.revision),active:c.active==='1',mode:c.mode,policy:c.policy||'strict',source:mock.source,available:false,status:'synthetic'})});return;
  }
  await route.continue();
 });
 mock.emit=()=>mock.events.push({seq:++mock.seq,gesture:'activity',confidence:.99,ageMs:0});
 return mock;
}
async function inspect(page,name,{fit=true}={}){
 await expect(page.locator('main')).toBeVisible();
 // Let layout and remote focus settle before measuring. A
 // screenshot must represent the visible TV viewport, including its header.
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 const geometry=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollY,scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,header:document.querySelector('header').getBoundingClientRect().toJSON(),footer:document.querySelector('footer').getBoundingClientRect().toJSON(),focused:document.activeElement?.tagName==='BUTTON'?document.activeElement.getBoundingClientRect().toJSON():null,buttons:[...document.querySelectorAll('main button:not(:disabled)')].map(node=>({action:node.dataset.action,text:node.textContent.trim(),box:node.getBoundingClientRect().toJSON(),font:getComputedStyle(node).fontSize})),cameraCalls:window.__qaCameraCalls}));
 const path=output+'/'+name+'.png';await page.screenshot({path,fullPage:!fit});
 const afterCapture=await page.evaluate(()=>({scrollY,headerTop:document.querySelector('header').getBoundingClientRect().top,footerBottom:document.querySelector('footer').getBoundingClientRect().bottom}));
 const row={name,path,...geometry,afterCapture};
 const current=logs.get(test.info().testId);current.layouts.push(row);
 expect(geometry.cameraCalls).toBe(0);
 expect(geometry.scrollWidth,name+' has no horizontal overflow').toBeLessThanOrEqual(geometry.width+1);
 // Collect every screen first; layout assertions are grouped at test end.
 if(fit){current.fitScreens.push(row);}
 return row;
}
function requireFits(log){
 const failures=log.fitScreens.filter(row=>row.scrollHeight>row.height+1||row.scrollY>1||row.header.top<0||row.footer.bottom>row.height+1||row.afterCapture.scrollY>1||row.afterCapture.headerTop<0||row.afterCapture.footerBottom>row.height+1||row.buttons.some(button=>button.box.bottom>row.height+1||button.box.top<0)||row.focused&&(row.focused.top<6||row.focused.bottom>row.height-6||row.focused.left<6||row.focused.right>row.width-6));
 expect(failures.map(row=>({name:row.name,scrollHeight:row.scrollHeight,scrollY:row.scrollY,headerTop:row.header.top,viewport:row.height,footerBottom:row.footer.bottom,afterCapture:row.afterCapture,focused:row.focused,offscreen:row.buttons.filter(button=>button.box.bottom>row.height+1||button.box.top<0)})),'TV header controls focus ring and footer fit without scrolling').toEqual([]);
}
async function startManual(page,choice=0){
 await page.locator('[data-action="choose:'+choice+'"]').click();
 await expect(page.locator('.app.setup')).toBeVisible();
 await page.locator('[data-action="start"]').click();
 await expect(page.locator('#manual-count')).toHaveText('0 / 6 movements you counted');
}
async function sixCounts(page,{capture=false}={}){
 for(let n=1;n<=6;n++){
  await page.getByRole('button',{name:'Count my movement',exact:true}).click();
  await expect(page.locator('#manual-count')).toHaveText(n+' / 6 movements you counted');
  await expect(page.locator('#manual-garden .garden-view')).toHaveAttribute('data-growth',String(n));
  if(capture&&n===3)await inspect(page,'manual-three-counts-720');
 }
 await expect(page.getByRole('button',{name:'Count my movement',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Finish this moment →',exact:true})).toBeFocused();
}
async function cameraSetup(page,{strict=false}={}){
 await page.goto(strict?'/?policy=strict':'/');await page.waitForLoadState('networkidle');
 await page.locator('[data-action="choose:1"]').click();
 await page.locator('[data-action="input:camera"]').click();
 await page.locator('[data-action="start"]').click();
 await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
}

test.beforeEach(async({page})=>{
 await mkdir(output,{recursive:true});
 const log={pageErrors:[],consoleErrors:[],consoleWarnings:[],requestFailures:[],layouts:[],fitScreens:[]};logs.set(test.info().testId,log);
 page.on('pageerror',error=>log.pageErrors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')log.consoleErrors.push(message.text());else if(message.type()==='warning')log.consoleWarnings.push(message.text());});
 page.on('requestfailed',request=>log.requestFailures.push({url:request.url(),error:request.failure()?.errorText}));
});
test.afterEach(async({},info)=>{
 const log=logs.get(info.testId);await mkdir(output,{recursive:true});
 await writeFile(output+'/'+info.title.replace(/[^a-z0-9]+/gi,'-').toLowerCase()+'.evidence.json',JSON.stringify(log,null,2)+'\n');
 expect(log.pageErrors,'No uncaught UI errors').toEqual([]);
 if(!info.title.includes('unavailable'))expect(log.consoleErrors,'No unexpected browser errors').toEqual([]);
});

test('manual entry activity growth confirmation harvest and retained replay fit TV',async({context,page})=>{
 await fixture(context,page);await page.goto('/');await page.waitForLoadState('networkidle');
 await expect(page.getByRole('button',{name:'Start growing →',exact:true})).toBeFocused();
 await inspect(page,'home-720');
 await page.keyboard.press('Enter');await inspect(page,'setup-wake-720');
 await page.locator('[data-action="start"]').click();await inspect(page,'manual-play-720');
 for(let moment=0;moment<3;moment++){
  if(moment){await page.getByRole('button',{name:'Next moment →',exact:true}).click();await inspect(page,'setup-'+moment+'-720');await page.locator('[data-action="start"]').click();}
  await sixCounts(page,{capture:moment===0});
  const rawBefore=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));
  if(moment===0)expect(rawBefore).toBe(null);
  await page.getByRole('button',{name:'Finish this moment →',exact:true}).click();
  if(moment===0)await inspect(page,'manual-confirmation-720');
  expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(rawBefore);
  await page.getByRole('button',{name:'Grow this moment →',exact:true}).click();
  await inspect(page,'garden-'+(moment+1)+'-720');
  expect(JSON.parse(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).completed).toHaveLength(moment+1);
 }
 await page.getByRole('button',{name:'Back to garden',exact:true}).click();
 await expect(page.getByRole('button',{name:'Harvest your garden →',exact:true})).toBeVisible();
 await inspect(page,'unclaimed-harvest-home-720');
 const beforeHarvest=JSON.parse(await page.evaluate(()=>localStorage.getItem('togethermove.v1')));
 expect(beforeHarvest.sessions).toBe(0);
 await page.getByRole('button',{name:'Harvest your garden →',exact:true}).click();
 expect(JSON.parse(await page.evaluate(()=>localStorage.getItem('togethermove.v1')))).toEqual(beforeHarvest);
 await page.getByRole('button',{name:'Harvest garden →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Your garden, gathered.'})).toBeVisible();
 await inspect(page,'harvest-720');
 const harvested=JSON.parse(await page.evaluate(()=>localStorage.getItem('togethermove.v1')));
 expect(harvested).toEqual({completed:['wake','sun','rain'],sessions:1});
 await page.getByRole('button',{name:'Grow again →',exact:true}).click();
 await expect(page.locator('.app.setup')).toBeVisible();
 expect(JSON.parse(await page.evaluate(()=>localStorage.getItem('togethermove.v1')))).toEqual(harvested);
 await page.getByRole('button',{name:'Garden',exact:true}).click();
 await expect(page.getByText('3 of 3 blooms saved',{exact:true})).toBeVisible();
 await inspect(page,'saved-garden-after-replay-720');
 await page.reload();await expect(page.getByText('3 of 3 blooms saved',{exact:true})).toBeVisible();
 requireFits(logs.get(test.info().testId));
});

test('pause natural RAF resume help Back reset and remote focus preserve honest manual input',async({context,page})=>{
 await fixture(context,page);await page.goto('/');await page.waitForLoadState('networkidle');await startManual(page);
 const first=await page.locator('#time').textContent();await expect(page.locator('#time')).not.toHaveText(first,{timeout:2500});
 await page.getByRole('button',{name:'Count my movement',exact:true}).press('Enter');
 await expect(page.locator('#manual-count')).toHaveText('1 / 6 movements you counted');
 await page.keyboard.press('Space');await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await expect(page.getByRole('button',{name:'Count my movement',exact:true})).toBeDisabled();
 const paused=await page.locator('#time').textContent();await page.waitForTimeout(1100);await expect(page.locator('#time')).toHaveText(paused);
 await inspect(page,'paused-720');await page.keyboard.press('Enter');
 await expect(page.locator('#time')).not.toHaveText(paused,{timeout:2500});
 await page.getByRole('button',{name:'How to play',exact:true}).click();await inspect(page,'help-720');
 await page.getByRole('button',{name:'Return to where I was →',exact:true}).click();
 await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await expect(page.locator('#manual-count')).toHaveText('1 / 6 movements you counted');
 await page.keyboard.press('Escape');await expect(page.locator('.app.home')).toBeVisible();
 await startManual(page);await expect(page.locator('#manual-count')).toHaveText('0 / 6 movements you counted');
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await page.keyboard.press('Escape');await expect(page.locator('.app.home')).toBeVisible();
 expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(null);
 requireFits(logs.get(test.info().testId));
});

test('synthetic activity six score ACK duplicate and fallback result stay isolated',async({context,page})=>{
 const seed={completed:['wake'],sessions:7};const mock=await fixture(context,page,{saved:seed});
 await cameraSetup(page);const stored=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));
 await inspect(page,'synthetic-activity-play-720');
 for(let count=1;count<=6;count++){
  mock.emit();await expect(page.locator('#sunshine-count')).toHaveText(String(count));
  if(count===1){mock.events.push({seq:mock.seq,gesture:'activity',confidence:.99,ageMs:0});await page.waitForTimeout(400);await expect(page.locator('#sunshine-count')).toHaveText('1');}
 }
 await expect.poll(()=>mock.requests.at(-1)?.active).toBe('0');
 await expect.poll(()=>Number(mock.requests.at(-1)?.after)).toBe(6);
 expect(mock.requests.every(item=>item.policy==='activity')).toBe(true);
 await expect(page.locator('.sun-rays .collected')).toHaveCount(6);
 await inspect(page,'synthetic-six-rays-720');
 expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(stored);
 await page.getByRole('button',{name:'Use manual play',exact:true}).click();
 await page.getByRole('button',{name:'Resume →',exact:true}).click();await sixCounts(page);
 await page.getByRole('button',{name:'Finish this moment →',exact:true}).click();
 await expect(page.locator('.test-result')).toContainText('SYNTHETIC TEST · NO CAMERA');
 await expect(page.getByRole('button',{name:'Grow this moment →'})).toHaveCount(0);
 await page.getByRole('button',{name:'View test result',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Test result.',exact:true})).toBeVisible();
 await expect(page.locator('.test-result')).toContainText('Your saved garden is unchanged.');
 await expect(page.getByRole('button',{name:'Harvest garden →'})).toHaveCount(0);
 await inspect(page,'synthetic-result-720');
 expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(stored);
 await page.getByRole('button',{name:'Back to garden',exact:true}).click();
 await expect(page.getByText('1 of 3 blooms saved',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(stored);
 logs.get(test.info().testId).synthetic={source:'mocked semantic JSON only',seq:mock.seq,lastAfter:Number(mock.requests.at(-1)?.after),requests:mock.requests,cameraUsed:false,nativeRuntimeVerified:false};
 requireFits(logs.get(test.info().testId));
});

test('camera unavailable fallback strict diagnostics and responsive reduced motion remain readable',async({context,page})=>{
 const mock=await fixture(context,page);mock.drop=true;
 await page.goto('/');await page.waitForLoadState('networkidle');await page.locator('[data-action="choose:1"]').click();
 await inspect(page,'sun-manual-setup-720');
 await page.locator('[data-action="input:camera"]').click();await inspect(page,'camera-setup-720');
 await page.locator('[data-action="start"]').click();await expect(page.locator('#motion-status')).toContainText('connection lost');
 await inspect(page,'camera-unavailable-720');
 await expect(page.getByRole('button',{name:'Use manual play',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Use manual play',exact:true}).click();await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 mock.drop=false;await cameraSetup(page,{strict:true});await inspect(page,'strict-diagnostic-play-720');
 await page.getByRole('button',{name:'Back to garden',exact:true}).click();
 await page.setViewportSize({width:1920,height:1080});await inspect(page,'home-1080');
 await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
 await inspect(page,'home-mobile-390',{fit:false});
 await startManual(page);await inspect(page,'manual-mobile-390',{fit:false});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(await page.locator('.garden-illustration').evaluate(node=>getComputedStyle(node).animationName)).toBe('none');
 requireFits(logs.get(test.info().testId));
});


test('D-pad reaches sunshine and manual position changes keep deliberate remote focus',async({context,page})=>{
 await fixture(context,page);await page.goto('/');await page.waitForLoadState('networkidle');
 await expect(page.getByRole('button',{name:'Start growing →',exact:true})).toBeFocused();
 await page.keyboard.press('ArrowDown');
 await expect(page.locator('[data-action="choose:0"]')).toBeFocused();
 await page.keyboard.press('ArrowRight');
 await expect(page.locator('[data-action="choose:1"]')).toBeFocused();
 await page.keyboard.press('Enter');
 await expect(page.getByRole('button',{name:'Start catch the sunshine →',exact:true})).toBeFocused();
 await page.getByRole('button',{name:'Garden',exact:true}).click();await startManual(page);
 await page.keyboard.press('Escape');
 await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await page.keyboard.press('ArrowRight');
 await expect(page.getByRole('button',{name:'Change position',exact:true})).toBeFocused();
 await page.keyboard.press('Enter');
 await expect(page.getByText('MOMENT 1 OF 3 · STANDING · MANUAL',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await inspect(page,'remote-position-change-720');
 await page.keyboard.press('Escape');await expect(page.locator('.app.home')).toBeVisible();
 expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(null);
 requireFits(logs.get(test.info().testId));
});

test('native 960 by 540 TV canvas keeps the complete journey and camera controls onscreen',async({context,page})=>{
 await page.setViewportSize({width:960,height:540});
 await fixture(context,page);await page.goto('/');await page.waitForLoadState('networkidle');
 await inspect(page,'native-home-540');
 for(let moment=0;moment<3;moment++){
  if(moment===0)await page.locator('[data-action="choose:0"]').click();
  else await page.getByRole('button',{name:'Next moment →',exact:true}).click();
  await inspect(page,'native-setup-'+moment+'-540');
  await page.locator('[data-action="start"]').click();await inspect(page,'native-manual-'+moment+'-540');
  if(moment===0){
   await page.keyboard.press('Space');await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
   await inspect(page,'native-manual-paused-540');
   await page.getByRole('button',{name:'How to play',exact:true}).click();await inspect(page,'native-help-540');
   await page.getByRole('button',{name:'Return to where I was →',exact:true}).click();
   await page.getByRole('button',{name:'Resume →',exact:true}).click();
  }
  await sixCounts(page);await inspect(page,'native-six-counts-'+moment+'-540');
  await page.getByRole('button',{name:'Finish this moment →',exact:true}).click();
  await inspect(page,'native-confirm-'+moment+'-540');
  await page.getByRole('button',{name:'Grow this moment →',exact:true}).click();
  await inspect(page,'native-celebrate-'+moment+'-540');
 }
 await page.getByRole('button',{name:'Harvest garden →',exact:true}).click();await inspect(page,'native-harvest-540');
 await page.getByRole('button',{name:'Back to garden',exact:true}).click();await inspect(page,'native-saved-home-540');
 await page.locator('[data-action="choose:1"]').click();
 await page.locator('[data-action="input:camera"]').click();await inspect(page,'native-camera-setup-540');
 await page.locator('[data-action="start"]').click();
 await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
 await inspect(page,'native-camera-play-540');
 await page.keyboard.press('Space');await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await inspect(page,'native-camera-paused-540');
 await page.goto('/?policy=strict');await page.waitForLoadState('networkidle');
 await page.locator('[data-action="choose:1"]').click();await page.locator('[data-action="input:camera"]').click();
 await inspect(page,'native-strict-setup-540');await page.locator('[data-action="start"]').click();
 await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
 await inspect(page,'native-strict-play-540');
 await page.keyboard.press('Space');await expect(page.getByRole('button',{name:'Resume →',exact:true})).toBeFocused();
 await inspect(page,'native-strict-paused-540');
 requireFits(logs.get(test.info().testId));
});
