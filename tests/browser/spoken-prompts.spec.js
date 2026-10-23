import {test,expect} from '@playwright/test';

test('spoken prompts are opt-in, stop with the round and preserve saved progress',async({page})=>{
  const seed={completed:['wake'],sessions:2};
  await page.addInitScript(value=>{
    localStorage.setItem('togethermove.v1',JSON.stringify(value));
    window.promptClips=[];
    window.Audio=class{
      constructor(src){this.src=src;this.currentTime=0;this.pauses=0;window.promptClips.push(this);}
      play(){return Promise.resolve();}
      pause(){this.pauses++;}
    };
  },seed);
  await page.goto('/');await page.getByRole('button',{name:'Let’s grow'}).click();
  await expect(page.getByRole('button',{name:'Spoken prompts: Off'})).toHaveAttribute('aria-pressed','false');
  expect(await page.evaluate(()=>window.promptClips.length)).toBe(0);
  await page.getByRole('button',{name:'Spoken prompts: Off'}).click();
  await expect(page.getByRole('button',{name:'Spoken prompts: On'})).toBeFocused();
  await page.getByRole('button',{name:/Start wake/}).click();
  expect(await page.evaluate(()=>window.promptClips.map(clip=>clip.src))).toEqual(['./audio/prompts/wake-seated-0.mp3']);
  await page.getByRole('button',{name:'Pause',exact:false}).click();
  expect(await page.evaluate(()=>window.promptClips[0].pauses)).toBe(1);
  await page.getByRole('button',{name:/Resume/}).click();
  expect(await page.evaluate(()=>window.promptClips.length)).toBe(2);
  await page.getByRole('button',{name:'Change position'}).click();
  expect(await page.evaluate(()=>window.promptClips[1].pauses)).toBe(1);
  await page.getByRole('button',{name:/Resume/}).click();
  expect(await page.evaluate(()=>window.promptClips.at(-1).src)).toBe('./audio/prompts/wake-standing-0.mp3');
  await page.getByRole('button',{name:'Back to garden'}).click();
  expect(await page.evaluate(()=>window.promptClips.at(-1).pauses)).toBe(1);
  expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('togethermove.v1')))).toEqual(seed);
  await page.reload();await page.getByRole('button',{name:'Let’s grow'}).click();
  await expect(page.getByRole('button',{name:'Spoken prompts: Off'})).toBeVisible();
});

test('camera selection suppresses manual spoken cues and blocked audio keeps play usable',async({page})=>{
  // Test the app's camera-mode boundary without activating a sidecar or camera.
  await page.route('**/motion/**',route=>route.abort());
  await page.addInitScript(()=>{
    window.promptClips=[];
    window.Audio=class{
      constructor(src){this.src=src;window.promptClips.push(this);}
      play(){return Promise.reject(Object.assign(new Error('blocked'),{name:'NotAllowedError'}));}
      pause(){}
    };
  });
  await page.goto('/');await page.getByRole('button',{name:/02 Catch/}).click();
  await page.getByRole('button',{name:'Spoken prompts: Off'}).click();
  await page.getByRole('button',{name:/Camera sunshine/}).click();
  await page.getByRole('button',{name:/Start catch/}).click();
  expect(await page.evaluate(()=>window.promptClips.length)).toBe(0);
  await page.getByRole('button',{name:'Use manual play'}).click();
  await page.getByRole('button',{name:/Resume/}).click();
  await expect(page.getByRole('status').filter({hasText:'Sound was blocked'})).toBeVisible();
  await expect(page.getByRole('button',{name:/Pause/})).toBeVisible();
  await expect(page.locator('#cue')).toHaveText('Stay comfortably seated with your back supported.');
});

test('spoken prompt controls and Start fit the 1080p TV setup',async({page})=>{
  for(const challenge of [/01 Wake/,/02 Catch/,/03 Make/]){
    await page.goto('/');await page.getByRole('button',{name:challenge}).click();
    const layout=await page.evaluate(()=>({height:document.documentElement.scrollHeight,viewport:innerHeight}));
    expect(layout.height).toBeLessThanOrEqual(layout.viewport);
    await expect(page.getByRole('button',{name:'Spoken prompts: Off'})).toBeInViewport();
    await expect(page.getByRole('button',{name:/Start /})).toBeInViewport();
  }
});

test('actual bundled Polly clips decode and play locally after opting in',async({page},testInfo)=>{
  const remoteRequests=[];
  page.on('request',request=>{if(!new URL(request.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/))remoteRequests.push(request.url());});
  await page.addInitScript(()=>{
    const NativeAudio=window.Audio;window.actualPromptClips=[];
    window.Audio=function(src){const audio=new NativeAudio(src);window.actualPromptClips.push(audio);return audio;};
  });
  await page.goto('/');
  const decoded=await page.evaluate(async()=>{
    const context=new AudioContext(),clips=[];
    try{
      for(const challenge of ['wake','sun','rain'])for(const mode of ['seated','standing'])for(let phase=0;phase<3;phase++){
        const path=`./audio/prompts/${challenge}-${mode}-${phase}.mp3`,response=await fetch(path);
        if(!response.ok)throw Error(`Missing bundled clip: ${path}`);
        const buffer=await context.decodeAudioData(await response.arrayBuffer());
        clips.push({path,duration:buffer.duration,sampleRate:buffer.sampleRate,channels:buffer.numberOfChannels});
      }
    }finally{await context.close();}
    return clips;
  });
  expect(decoded).toHaveLength(18);expect(decoded.every(clip=>clip.duration>0&&clip.duration<10)).toBe(true);
  await page.getByRole('button',{name:'Let’s grow'}).click();
  await page.getByRole('button',{name:'Spoken prompts: Off'}).click();
  await page.getByRole('button',{name:/Start wake/}).click();
  await page.waitForFunction(()=>window.actualPromptClips[0]?.currentTime>.1&&!window.actualPromptClips[0]?.paused);
  const playback=await page.evaluate(()=>{const audio=window.actualPromptClips[0];return {src:audio.getAttribute('src'),currentTime:audio.currentTime,duration:audio.duration,paused:audio.paused,readyState:audio.readyState,error:audio.error?.code??null};});
  expect(playback.error).toBe(null);expect(playback.readyState).toBeGreaterThanOrEqual(3);
  await page.getByRole('button',{name:/Pause/}).click();
  expect(await page.evaluate(()=>window.actualPromptClips[0].paused)).toBe(true);
  expect(await page.evaluate(()=>window.actualPromptClips[0].currentTime)).toBe(0);
  expect(remoteRequests).toEqual([]);
  await testInfo.attach('polly-local-runtime.json',{body:JSON.stringify({decoded,playback,externalRequests:remoteRequests},null,2),contentType:'application/json'});
});

for(const viewport of [{width:960,height:540},{width:1280,height:720},{width:1920,height:1080}]){
  test(`manual controls fit ${viewport.width}x${viewport.height} through remote focus, pause and position changes`,async({page},testInfo)=>{
    await page.setViewportSize(viewport);
    await page.addInitScript(()=>{window.Audio=class{play(){return Promise.resolve();}pause(){}};});
    const measurements=[];
    async function fits(label,play=false){
      const metrics=await page.evaluate(({label,play})=>{
        const selectors=['header','h1','footer','[data-action="spoken-prompts"]','#spoken-prompts-status',...play?['#cue','#time','.actions','.pause-note']:['.choices','.safety','[data-action="start"]']];
        return {label,width:innerWidth,height:innerHeight,scrollY,scrollHeight:document.documentElement.scrollHeight,rects:selectors.flatMap(selector=>{const node=document.querySelector(selector);if(!node)return [];const rect=node.getBoundingClientRect();return [{selector,x:rect.x,y:rect.y,right:rect.right,bottom:rect.bottom,width:rect.width,height:rect.height}];})};
      },{label,play});
      measurements.push(metrics);expect(metrics.scrollY,label).toBe(0);expect(metrics.scrollHeight,label).toBeLessThanOrEqual(viewport.height);
      for(const rect of metrics.rects){expect(rect.y,`${label} ${rect.selector} top`).toBeGreaterThanOrEqual(-.5);expect(rect.bottom,`${label} ${rect.selector} bottom`).toBeLessThanOrEqual(viewport.height+.5);expect(rect.right,`${label} ${rect.selector} right`).toBeLessThanOrEqual(viewport.width+.5);}
    }
    for(const challenge of [/01 Wake/,/02 Catch/,/03 Make/]){
      await page.goto('/');await page.getByRole('button',{name:challenge}).click();await fits('setup');
      await page.getByRole('button',{name:'Spoken prompts: Off'}).click();await fits('setup toggle focus');
      await page.getByRole('button',{name:/Start /}).click();await fits('playing',true);
      await page.keyboard.press('Space');await fits('paused',true);
      await page.getByRole('button',{name:'Change position'}).click();await fits('position switch',true);
      await page.getByRole('button',{name:/Resume/}).click();await fits('standing',true);
      await page.getByRole('button',{name:'Spoken prompts: On'}).click();await fits('play toggle focus',true);
    }
    await testInfo.attach('manual-layout.json',{body:JSON.stringify(measurements,null,2),contentType:'application/json'});
  });
}
