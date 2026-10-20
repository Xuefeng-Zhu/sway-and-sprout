import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

// These tests mock semantic JSON events. They never open a camera or establish
// that a real person, a pose model, or a native TV runtime was verified.
const evidence=process.env.TOGETHERMOVE_QA_OUTPUT_DIR
  ?`${process.env.TOGETHERMOVE_QA_OUTPUT_DIR.replace(/\/$/,'')}/`
  :fileURLToPath(new URL('../../test-results/browser/',import.meta.url));
const logs=new Map();
test.beforeEach(async({page},info)=>{
  const log={pageErrors:[],consoleErrors:[],consoleWarnings:[],requestsFailed:[]};
  logs.set(info.testId,log);
  page.on('pageerror',error=>log.pageErrors.push(error.message));
  page.on('console',message=>{
    if(message.type()==='error')log.consoleErrors.push(message.text());
    if(message.type()==='warning')log.consoleWarnings.push(message.text());
  });
  page.on('requestfailed',request=>log.requestsFailed.push({url:request.url(),error:request.failure()?.errorText}));
});
test.afterEach(async({page},info)=>{
  const log=logs.get(info.testId);
  await mkdir(evidence,{recursive:true});
  const name=info.title.replace(/[^a-z0-9]+/gi,'-').toLowerCase();
  await writeFile(`${evidence}${name}.console.json`,JSON.stringify(log,null,2));
  await info.attach('browser-log',{body:JSON.stringify(log,null,2),contentType:'application/json'});
  expect(log.pageErrors,'Uncaught browser exceptions').toEqual([]);
  if(!info.title.includes('network errors'))expect(log.consoleErrors,'Browser console errors').toEqual([]);
});

async function mockedSidecar(page){
  const mock={status:'neutral',source:'synthetic',streamId:'synthetic-qa-stream',verified:true,version:'5.0.0',seq:0,
    events:[],requests:[],previewRequests:[],armed:false,drop:false,invalid:false,lastRound:null};
  mock.raise=(gesture,fields={})=>mock.events.push({seq:++mock.seq,gesture,confidence:.99,ageMs:0,...fields});
  await page.route('**/motion/events?*',async route=>{
    const url=new URL(route.request().url());
    const context=Object.fromEntries(url.searchParams);
    mock.requests.push(context);
    mock.lastRound=context.roundId;
    if(mock.drop){await route.abort('failed');return;}
    const events=mock.events.splice(0).map(event=>({roundId:context.roundId,...event}));
    const packet={protocol:1,clientId:context.clientId,roundId:context.roundId,
      revision:Number(context.revision),active:context.active==='1',mode:context.mode,
      runtime:{opencv:mock.version,verified:mock.verified,source:mock.source},
      source:mock.source,streamId:mock.streamId,status:mock.status,expected:'left',heldMs:0,seq:mock.seq,
      events,metrics:{fps:0,armed:mock.armed}};
    if(mock.invalid)packet.protocol=999;
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(packet)});
  });
  // All preview traffic is mocked too: a camera-labelled protocol fixture must
  // never fall through to a real sidecar or produce a real camera image.
  await page.route('**/motion/preview?*',async route=>{
    const context=Object.fromEntries(new URL(route.request().url()).searchParams);
    mock.previewRequests.push(context);
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
      source:mock.source,available:false,clientId:context.clientId,roundId:context.roundId,
      revision:Number(context.revision),active:context.active==='1',mode:context.mode,
      status:mock.source==='synthetic'?'synthetic':context.active==='1'?'waiting':'paused',
    })});
  });
  return mock;
}

async function cameraRound(page,mock,{standing=false}={}){
  await page.goto('/');
  await expect(page).toHaveTitle('Sway & Sprout — Grow together');
  await page.getByRole('button',{name:/02 Catch/}).click();
  if(standing){await page.locator('[data-action="mode:standing"]').click();await expect(page.locator('[data-action="mode:standing"]')).toHaveClass(/selected/);}
  await page.locator('[data-action="input:camera"]').click();
  await expect(page.locator('[data-action="input:camera"]')).toHaveClass(/selected/);
  await page.getByRole('button',{name:/^Start catch/}).click();
  await expect(page.getByRole('heading',{name:'Catch the sunshine'})).toBeVisible();
  await expect(page.locator('#camera-source')).toHaveText(mock.source==='synthetic'?'SYNTHETIC TEST · NO CAMERA':'LOCAL CAMERA · OPENCV 5');
  await expect.poll(()=>mock.requests.some(request=>request.active==='1')).toBe(true);
  await expect(page.locator('#sunshine-count')).toHaveText('0');
}

async function screenshot(page,name){await page.screenshot({path:`${evidence}${name}.png`,fullPage:true});}

test('synthetic semantic raises grow six rays without keyboard input or focus changes',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  const savedBefore=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));
  const before=await page.locator('.garden-flower').evaluate(node=>getComputedStyle(node).transform);
  await expect(page.getByRole('button',{name:'Pause Ⅱ'})).toBeFocused();
  for(let count=1;count<=6;count++){
    mock.raise(count%2?'left-raise':'right-raise');
    await expect(page.locator('#sunshine-count')).toHaveText(String(count));
    await expect(page.locator('.sun-rays .collected')).toHaveCount(count);
    await expect(page.getByRole('button',{name:'Pause Ⅱ'})).toBeFocused();
  }
  await expect(page.locator('#sunshine-next')).toHaveText('Your sunshine is gathered!');
  await expect(page.locator('#motion-status')).toContainText('Synthetic input');
  const activeRevision=Number(mock.requests.filter(request=>request.active==='1').at(-1).revision);
  await expect.poll(()=>mock.requests.at(-1)?.active).toBe('0');
  expect(Number(mock.requests.at(-1).revision),'Completing capture changes control revision').toBeGreaterThan(activeRevision);
  await page.waitForTimeout(550);
  const after=await page.locator('.garden-flower').evaluate(node=>getComputedStyle(node).transform);
  expect(after).not.toBe(before);
  await screenshot(page,'synthetic-six-rays-1920');
  await expect(page.getByRole('heading',{name:'A little more life.'})).toBeVisible({timeout:35000});
  await expect(page.getByText(/0 OF 3 MOMENTS GROWN · SYNTHETIC TEST/)).toBeVisible();
  // A completed result retains its actual source even if another local service
  // is started later. Celebration should release its inactive polling lease.
  await page.waitForTimeout(500);
  const completedRequests=mock.requests.length;
  mock.source='camera';mock.streamId='different-post-completion-stream';
  await page.waitForTimeout(700);
  expect(mock.requests.length,'Completed celebration stops polling').toBe(completedRequests);
  await expect(page.getByText(/0 OF 3 MOMENTS GROWN · SYNTHETIC TEST/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Resume →'})).toHaveCount(0);
  expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
  await page.reload();await expect(page.getByText('Your next little adventure')).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
});

test('pause Back and position change ignore semantic raises while paused',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  await page.keyboard.press('Space');
  await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
  const time=await page.locator('#time').textContent();
  mock.raise('right-raise');await page.waitForTimeout(650);
  await expect(page.locator('#sunshine-count')).toHaveText('1');
  await expect(page.locator('#time')).toHaveText(time);
  await expect.poll(()=>mock.requests.at(-1)?.active).toBe('0');
  await page.keyboard.press('Enter');
  mock.raise('right-raise');await expect(page.locator('#sunshine-count')).toHaveText('2');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
  await page.getByRole('button',{name:'Change position'}).click();
  await expect(page.getByText('MOMENT 2 OF 3 · STANDING · SYNTHETIC TEST · NO CAMERA')).toBeVisible();
  await expect(page.getByRole('button',{name:'Resume →'})).toBeVisible();
  await expect.poll(()=>mock.requests.at(-1)?.mode).toBe('standing');
  mock.raise('left-raise');await page.waitForTimeout(450);
  await expect(page.locator('#sunshine-count')).toHaveText('2');
  await screenshot(page,'synthetic-paused-standing-1920');
});

test('duplicates stale low-confidence wrong-side and previous-round events cannot grow rays',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  const originalRound=mock.lastRound;
  mock.raise('right-raise');await page.waitForTimeout(350);
  mock.raise('left-raise',{confidence:.4});await page.waitForTimeout(350);
  mock.raise('left-raise',{ageMs:1800});await page.waitForTimeout(350);
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  mock.events.push({seq:mock.seq,gesture:'right-raise',confidence:.99,ageMs:0});
  await page.waitForTimeout(350);await expect(page.locator('#sunshine-count')).toHaveText('1');
  await page.getByRole('button',{name:'Back to garden',exact:true}).click();
  await page.getByRole('button',{name:/02 Catch/}).click();
  await page.locator('[data-action="input:camera"]').click();
  await expect(page.locator('[data-action="input:camera"]')).toHaveClass(/selected/);
  await page.getByRole('button',{name:/^Start catch/}).click();
  await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
  expect(mock.lastRound).not.toBe(originalRound);
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  mock.raise('left-raise',{roundId:originalRound});
  await expect(page.locator('#motion-status')).toContainText('connection lost');
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
});

test('low confidence no person and unverified OpenCV are explicit recoverable states',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  mock.status='low-confidence';await expect(page.locator('#motion-status')).toContainText('can’t see both shoulders');
  await screenshot(page,'synthetic-low-confidence-1920');
  mock.status='no-person';await expect(page.locator('#motion-status')).toContainText('Step into view');
  mock.status='camera-error';await expect(page.locator('#motion-status')).toContainText('Camera unavailable');
  mock.verified=false;mock.version='5.0.0';mock.raise('left-raise');
  await expect(page.locator('#motion-status')).toContainText('runtime is not verified');
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  mock.verified=true;mock.status='neutral';mock.raise('left-raise');
  await expect(page.locator('#sunshine-count')).toHaveText('1');
});

test('network errors show fallback preserve progress and recover without reload',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  mock.drop=true;await expect(page.locator('#motion-status')).toContainText('connection lost');
  await expect(page.getByRole('button',{name:'Use manual play'})).toBeVisible();
  await expect(page.locator('#sunshine-count')).toHaveText('1');
  await screenshot(page,'synthetic-network-fallback-1920');
  mock.drop=false;mock.raise('right-raise');await expect(page.locator('#sunshine-count')).toHaveText('2');
});

test('manual fallback from mocked camera transport stops polling and preserves self-report completion',async({page})=>{
  // This is camera-labelled JSON only; both HTTP routes are mocked, with no capture.
  const mock=await mockedSidecar(page);mock.source='camera';await cameraRound(page,mock);
  await page.getByRole('button',{name:'Use manual play'}).click();
  await expect(page.locator('.sunshine-garden')).toHaveCount(0);
  await expect(page.getByText('MOMENT 2 OF 3 · SEATED · MANUAL')).toBeVisible();
  await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
  await page.waitForTimeout(1600);const settled=mock.requests.length;
  await page.waitForTimeout(900);expect(mock.requests.length).toBe(settled);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading',{name:'How did that feel?'})).toBeVisible({timeout:35000});
  await expect(page.getByRole('button',{name:'We joined in ✦'})).toBeVisible();
  await page.keyboard.press('Enter');
  await expect(page.getByText('1 OF 3 MOMENTS GROWN',{exact:true})).toBeVisible();
  await page.reload();await expect(page.getByText('1 of 3 moments grown')).toBeVisible();
});

test('manual fallback from synthetic input does not save simulated participation',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  const savedBefore=await page.evaluate(()=>localStorage.getItem('togethermove.v1'));
  await page.getByRole('button',{name:'Use manual play'}).click();
  await expect(page.locator('.sunshine-garden')).toHaveCount(0);
  await expect.poll(()=>mock.requests.at(-1)?.active).toBe('0');
  await page.getByRole('button',{name:'Resume →'}).click();
  await expect(page.getByRole('heading',{name:'How did that feel?'})).toBeVisible({timeout:35000});
  await page.getByRole('button',{name:'We joined in ✦'}).click();
  await expect(page.getByText('0 OF 3 MOMENTS GROWN',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
  await page.reload();await expect(page.getByText('Your next little adventure')).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('togethermove.v1'))).toBe(savedBefore);
});

test('returning to Garden stops camera polling and starting again resets the round',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  const oldRound=mock.lastRound;
  await page.getByRole('button',{name:'Back to garden',exact:true}).click();
  await expect(page.getByRole('button',{name:'Let’s grow →'})).toBeFocused();
  await page.waitForTimeout(1600);const settled=mock.requests.length;
  await page.waitForTimeout(900);expect(mock.requests.length).toBe(settled);
  await page.getByRole('button',{name:/02 Catch/}).click();
  await expect(page.locator('[data-action="input:manual"]')).toHaveClass(/selected/);
  await page.locator('[data-action="input:camera"]').click();
  await expect(page.locator('[data-action="input:camera"]')).toHaveClass(/selected/);
  await page.getByRole('button',{name:/^Start catch/}).click();
  await expect(page.locator('#camera-source')).toHaveText('SYNTHETIC TEST · NO CAMERA');
  expect(mock.lastRound).not.toBe(oldRound);
  await expect(page.locator('#sunshine-count')).toHaveText('0');
});

test('switching input source or restarting the service resets evidence and pauses the round',async({page})=>{
  const mock=await mockedSidecar(page);await cameraRound(page,mock);
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  const originalRound=mock.lastRound;
  mock.source='camera';mock.streamId='camera-qa-stream';
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
  await expect(page.locator('#motion-status')).toContainText('input service changed');
  await expect.poll(()=>mock.lastRound).not.toBe(originalRound);
  await page.keyboard.press('Enter');
  mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
  const cameraRoundId=mock.lastRound;
  mock.streamId='restarted-camera-qa-stream';
  await expect(page.locator('#sunshine-count')).toHaveText('0');
  await expect(page.getByRole('button',{name:'Resume →'})).toBeFocused();
  await expect.poll(()=>mock.lastRound).not.toBe(cameraRoundId);
});

for(const viewport of [{width:390,height:844},{width:960,height:540}]){
  test(`camera sunshine fits ${viewport.width}x${viewport.height} and reduced motion`,async({page})=>{
    await page.setViewportSize(viewport);await page.emulateMedia({reducedMotion:'reduce'});
    const mock=await mockedSidecar(page);await cameraRound(page,mock,{standing:true});
    mock.raise('left-raise');await expect(page.locator('#sunshine-count')).toHaveText('1');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    expect(await page.locator('.living-sun').evaluate(node=>getComputedStyle(node).animationName)).toBe('none');
    await expect(page.getByRole('button',{name:'Pause Ⅱ'})).toBeFocused();
    if(viewport.width>850){
      const bounds=await page.locator('.sunshine-garden').boundingBox();
      expect(bounds.y+bounds.height).toBeLessThanOrEqual(viewport.height);
      for(const button of await page.locator('.actions button').all()){
        const box=await button.boundingBox();expect(box.y+box.height).toBeLessThanOrEqual(viewport.height);
      }
    }
    await screenshot(page,`synthetic-camera-${viewport.width}x${viewport.height}`);
  });
}
