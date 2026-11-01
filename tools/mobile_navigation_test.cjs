const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.FEJES_BROWSER_EXECUTABLE?{executablePath:process.env.FEJES_BROWSER_EXECUTABLE}:{})});
 let checks=0;
 try{
  const page=await browser.newPage();
  for(const width of [320,375,430,700,1024]){
   await page.setViewportSize({width,height:900});
   for(const name of fs.readdirSync(process.argv[2]).filter(n=>n.endsWith('.html'))){
    await page.goto(pathToFileURL(path.resolve(process.argv[2],name)).href);
    const result=await page.locator('.fmc-nav').evaluate(nav=>{
     const box=nav.getBoundingClientRect();
     return {width:box.width,scroll:nav.scrollWidth,client:nav.clientWidth,
      position:getComputedStyle(nav).position,
      controls:[...nav.querySelectorAll('a,button')].map(el=>{const r=el.getBoundingClientRect();return {
       href:el.getAttribute('href'),type:el.getAttribute('type'),height:r.height,
       left:r.left,right:r.right,top:r.top,bottom:r.bottom,
       inside:r.left>=box.left-1&&r.right<=box.right+1&&r.top>=box.top-1&&r.bottom<=box.bottom+1};})};
    });
    assert.equal(result.controls.length,7,name);
    if(width<=700){
     assert.equal(result.position,'static');
     assert.ok(result.scroll<=result.client+1,`${width} ${name}: horizontal overflow`);
     for(const c of result.controls){assert.ok(c.inside,`${width} ${name}: hidden control`);assert.ok(c.height>=44);}
     for(let i=0;i<result.controls.length;i++)for(let j=i+1;j<result.controls.length;j++){
      const a=result.controls[i],b=result.controls[j];
      assert.ok(a.right<=b.left+1||b.right<=a.left+1||a.bottom<=b.top+1||b.bottom<=a.top+1,'Overlapping controls');
     }
    }
    for(const c of result.controls.filter(c=>!c.href))assert.equal(c.type,'button');
    assert.deepEqual(result.controls.filter(c=>c.href).map(c=>c.href),['/Dashboard','/Tools/FejesMover','/Tools/FejesMoverSelective','/Tools/FejesMoverSettings','/Tools/FejesMoverSetup']);
    checks++;
   }
  }
  if(process.env.FEJES_MOBILE_SCREENSHOT){
   await page.setViewportSize({width:375,height:900});
   await page.goto(pathToFileURL(path.resolve(process.argv[2],'hu-FejesMoverSelective.page.html')).href);
   await page.screenshot({path:process.env.FEJES_MOBILE_SCREENSHOT});
  }
  console.log(`${checks} localized page/viewport navigation checks passed.`);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
