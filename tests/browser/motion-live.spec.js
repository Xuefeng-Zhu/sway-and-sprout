import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const evidence=process.env.TOGETHERMOVE_QA_OUTPUT_DIR
  ?`${process.env.TOGETHERMOVE_QA_OUTPUT_DIR.replace(/\/$/,'')}/`
  :fileURLToPath(new URL('../../test-results/browser/',import.meta.url));

// Opt-in only. Ordinary browser QA uses mocked routes and needs no sidecar.
// Example: TOGETHERMOVE_LIVE_SYNTHETIC=1 npm run test:e2e:mac -- --project=live-synthetic
test.skip(process.env.TOGETHERMOVE_LIVE_SYNTHETIC!=='1',
  'Explicitly enable the local synthetic relay test after starting a synthetic sidecar.');

test('real HTTP relay synthetic landmarks grow sunshine with pause standing and unchanged persistence',async({page})=>{
  // Intentionally no page.route: Chrome -> Vite -> actual Python service.
  // The sidecar is in --synthetic mode; this is not human-camera verification.
  const log={source:'synthetic',humanGestureVerified:false,pageErrors:[],consoleErrors:[],
    consoleWarnings:[],failedRequests:[],httpErrors:[],captureErrors:[],packets:[],responseCount:0,
    timingsMs:{},viewport:{width:1920,height:1080}};
  page.on('pageerror',error=>log.pageErrors.push(error.message));
  page.on('console',message=>{
    if(message.type()==='error')log.consoleErrors.push(message.text());
    if(message.type()==='warning')log.consoleWarnings.push(message.text());
  });
  page.on('requestfailed',request=>log.failedRequests.push({url:request.url(),error:request.failure()?.errorText}));
  const captures=[];
  page.on('response',response=>{
    if(!response.url().includes('/motion/events?'))return;
    log.responseCount++;
    if(!response.ok())log.httpErrors.push({status:response.status(),url:response.url()});
    captures.push((async()=>{
      try{
        await response.finished();
        const packet=await response.json();
        if(response.ok()&&(log.packets.length<8||packet.events?.length))log.packets.push(packet);
      }catch(error){
        // CDP may retire a response body after navigation. Preserve diagnostic
        // capture failures separately from actual HTTP status/console failures.
        log.captureErrors.push({status:response.status(),error:error.message});
      }
    })());
  });
  await mkdir(evidence,{recursive:true});
  try{
    await page.goto('/');
    const savedBefore=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));
    await expect(page).toHaveTitle('Sway & Sprout — Grow together');
    await page.getByRole('button',{name:/02 Catch/}).click();
    // Selecting the input while still on setup sends active=false. Refuse a
    // camera/video/unverified service before any Start action can activate it.
    const initialResponse=page.waitForResponse(response=>response.ok()&&response.url().includes('/motion/events?'));
    await page.locator('[data-action="input:camera"]').click();
    await expect(page.locator('[data-action="input:camera"]')).toHaveClass(/selected/);
    const initialPacket=await (await initialResponse).json();
    expect(initialPacket.active,'Setup probe must be inactive').toBe(false);
    expect(initialPacket.source,'Only explicitly synthetic relay input is allowed').toBe('synthetic');
    expect(initialPacket.runtime?.verified,'Synthetic relay runtime is verified').toBe(true);
    const started=Date.now();
    await page.getByRole('button',{name:/^Start catch/}).click();
    await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
    await expect(page.locator('#sunshine-count')).toHaveText('2',{timeout:15000});
    log.timingsMs.secondRay=Date.now()-started;
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
    const pausedCount=await page.locator('#sunshine-count').textContent();
    const pausedTime=await page.locator('#time').textContent();
    await page.waitForTimeout(900);
    await expect(page.locator('#sunshine-count')).toHaveText(pausedCount);
    await expect(page.locator('#time')).toHaveText(pausedTime);
    await page.getByRole('button',{name:'Change position'}).click();
    await expect(page.getByText('MOMENT 2 OF 3 · STANDING · SYNTHETIC TEST · NO CAMERA')).toBeVisible();
    await page.screenshot({path:`${evidence}live-http-synthetic-paused-standing.png`,fullPage:true});
    await page.getByRole('button',{name:'Resume →'}).click();
    await expect(page.locator('#sunshine-count')).toHaveText('6',{timeout:15000});
    log.timingsMs.sixthRay=Date.now()-started;
    await expect(page.locator('.sun-rays .collected')).toHaveCount(6);
    await expect(page.getByRole('button',{name:'Pause Ⅱ'})).toBeFocused();
    await page.screenshot({path:`${evidence}live-http-synthetic-six-rays.png`,fullPage:true});
    await expect(page.getByRole('heading',{name:'A little more life.'})).toBeVisible({timeout:35000});
    log.timingsMs.completed=Date.now()-started;
    await expect(page.getByText(/0 OF 3 MOMENTS GROWN · SYNTHETIC TEST/)).toBeVisible();
    await page.screenshot({path:`${evidence}live-http-synthetic-completed.png`,fullPage:true});
    await Promise.allSettled(captures);
    expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
    await page.reload();await expect(page.getByText('Your next little adventure')).toBeVisible();
    expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
    expect(log.responseCount).toBeGreaterThan(20);
    expect(log.packets.some(packet=>packet.events?.length)).toBe(true);
    expect(log.packets.every(packet=>packet.source==='synthetic')).toBe(true);
    expect(log.packets.every(packet=>packet.runtime.verified&&/^5\./.test(packet.runtime.opencv))).toBe(true);
    expect(log.pageErrors).toEqual([]);expect(log.consoleErrors).toEqual([]);expect(log.httpErrors).toEqual([]);
    log.passed=true;
  }finally{
    await Promise.allSettled(captures);
    await writeFile(`${evidence}live-http-synthetic.json`,JSON.stringify(log,null,2));
  }
});
