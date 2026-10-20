import {test,expect} from '@playwright/test';
test('full garden, pause, persistence and replay',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 await expect(page.getByRole('button',{name:'Let’s grow'})).toBeFocused();
 await page.screenshot({path:'artifacts/home-1920.png'});await page.keyboard.press('Enter');
 await expect(page.getByRole('heading',{name:'Move your way.'})).toBeVisible();
 await page.keyboard.press('Enter');await page.keyboard.press('Space');
 await expect(page.getByRole('button',{name:'Resume'})).toBeVisible();const t=await page.locator('#time').textContent();await page.waitForTimeout(1100);expect(await page.locator('#time').textContent()).toBe(t);
 await page.screenshot({path:'artifacts/paused-1920.png'});await page.keyboard.press('Space');
 for(let i=0;i<3;i++){
  await expect(page.getByRole('heading',{name:'How did that feel?'})).toBeVisible({timeout:40000});
  await page.keyboard.press('Enter');
  if(i<2){await page.keyboard.press('Enter');await page.keyboard.press('Enter');}
 }
 await expect(page.getByRole('heading',{name:'Look what you grew.'})).toBeVisible();await page.waitForTimeout(800);await page.screenshot({path:'artifacts/celebration-1920.png'});
 await page.reload();await expect(page.getByText('3 of 3 moments grown')).toBeVisible();
 await page.getByRole('button',{name:'How to play'}).click();await expect(page.getByRole('heading',{name:'A garden for everyone.'})).toBeVisible();await page.keyboard.press('Escape');
 expect(errors).toEqual([]);
});
test('D-pad reaches challenges and mobile layout fits',async({page})=>{await page.goto('/');await page.keyboard.press('ArrowDown');await expect(page.getByRole('button',{name:/01 Wake/})).toBeFocused();await page.keyboard.press('ArrowRight');await expect(page.getByRole('button',{name:/02 Catch/})).toBeFocused();await page.keyboard.press('Enter');await expect(page.getByRole('button',{name:/Start catch/})).toBeVisible();await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Garden',exact:true}).click();await page.screenshot({path:'artifacts/home-mobile.png',fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);});
test('remote-only pause, back and reduced-motion',async({page})=>{await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');await page.keyboard.press('Enter');await page.keyboard.press('Enter');await expect(page.getByRole('heading',{name:'Wake the garden'})).toBeVisible();expect(await page.locator('.motion-art > span').evaluate(el=>getComputedStyle(el).animationName)).toBe('none');await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Resume'})).toBeFocused();const t=await page.locator('#time').textContent();await page.waitForTimeout(1200);expect(await page.locator('#time').textContent()).toBe(t);await page.keyboard.press('Enter');await expect(page.getByRole('button',{name:'Pause'})).toBeVisible();await page.keyboard.press('ArrowRight');await expect(page.getByRole('button',{name:'Change position'})).toBeFocused();await page.keyboard.press('Enter');await expect(page.getByText(/MOMENT 1 OF 3 · STANDING/)).toBeVisible();await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowRight');await expect(page.getByRole('button',{name:'Back to garden'})).toBeFocused();await page.keyboard.press('Enter');await expect(page.getByRole('button',{name:'Let’s grow'})).toBeFocused();});
