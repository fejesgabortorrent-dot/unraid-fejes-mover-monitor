const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../src/FejesMoverRuntime.php','utf8');
const nav=[...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes("key='fejesMoverNavigation'"));
let scrolled,assigned=false,observer;const nodes=[];
function element(tag){return {tag,children:[],listeners:{},append(...items){this.children.push(...items)},addEventListener(k,f){this.listeners[k]=f}}}
const main=element('main');main.querySelector=()=>main.children.find(x=>x.className==='fmc-page-tail')||null;
const context={window:{scrollTo:value=>scrolled=value},location:{pathname:'/Tools/FejesMoverSettings',assign(){assigned=true}},sessionStorage:{getItem(){return null},setItem(){}},document:{body:{},createElement:element,querySelector:()=>main,querySelectorAll:()=>[],addEventListener(){}},MutationObserver:class{constructor(f){observer=f}observe(){}}};
vm.runInNewContext(nav,context);observer();assert.equal(main.children.length,1);
const top=main.children[0].children.find(x=>x.tag==='button');assert.ok(top);assert.equal(top.type,'button');assert.equal(top.href,undefined);assert.equal(top.target,undefined);
let prevented=false;top.listeners.click({preventDefault(){prevented=true}});assert.ok(prevented);assert.equal(scrolled.top,0);assert.equal(assigned,false);
const strip=main.children[0].children.find(x=>x.className==='fmc-support-strip');assert.ok(strip);const links=strip.children.filter(x=>x.tag==='a');assert.equal(links.length,4);assert.deepEqual(links.map(x=>x.href),['https://paypal.me/FejesG/2EUR','https://paypal.me/FejesG/5EUR','https://paypal.me/FejesG/10EUR','https://paypal.me/FejesG']);for(const link of links){assert.equal(link.target,'_blank');assert.equal(link.rel,'noopener noreferrer');}
console.log('Back to top scrolls in place, is not a submit/link, creates no duplicate footer; only support opens a new tab.');
