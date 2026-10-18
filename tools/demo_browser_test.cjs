const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080}});
    const errors=[];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../docs/demo/index.html')).href);
    for (const [lang, heading] of [['hu','A cache-ed, kézben tartva.'],['en','Your cache, under control.'],['de','Dein Cache, unter Kontrolle.']]) {
      await page.selectOption('#language',lang);
      assert.equal(await page.locator('h1').textContent(),heading);
      await page.selectOption('#scenario','1');
      await page.click('#run');
      await page.click('#tab-history');
      assert.equal(await page.locator('.history-entry').count(),lang==='hu'?1:lang==='en'?2:3);
      await page.click('#tab-overview');
      await page.selectOption('#scenario','2');
      assert.equal(await page.locator('.statusrow.blocked').count(),1);
    }
    await page.reload();
    assert.equal(await page.locator('#language').inputValue(),'de');
    await page.selectOption('#language','hu');
    await page.selectOption('#scenario','1');
    await page.locator('#threshold-number').fill('50');
    await page.locator('#threshold-number').dispatchEvent('change');
    assert.equal(await page.locator('#decision').textContent(),'Nincs szükség mozgatásra');
    await page.locator('#threshold-number').fill('300');
    await page.locator('#threshold-number').dispatchEvent('change');
    assert.equal(await page.locator('#decision').textContent(),'Indítható lenne');
    await page.selectOption('#scenario','0');
    await page.click('#tab-dashboard');
    assert.equal(await page.locator('#dash-usage').textContent(),'32%');
    await page.click('#dash-open');
    assert.equal(await page.locator('#tab-overview').getAttribute('aria-selected'),'true');
    fs.mkdirSync('demo-screenshots',{recursive:true});
    await page.screenshot({path:'demo-screenshots/desktop-hu.png',fullPage:true});
    await page.click('#theme');
    assert.ok(await page.locator('body').evaluate(el=>el.classList.contains('light')));
    await page.screenshot({path:'demo-screenshots/desktop-light.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'demo-screenshots/mobile-hu.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: 3 languages, persistence, scenario decisions, history, threshold, themes and mobile overflow');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
