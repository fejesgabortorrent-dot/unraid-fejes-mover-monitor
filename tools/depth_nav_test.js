const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../src/FejesMoverRuntime.php','utf8');
const scripts=[...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const depth=scripts.find(s=>s.includes("key='fejesMoverDepth'"));
const nav=scripts.find(s=>s.includes("key='fejesMoverNavigation'"));
function appearance(initial,blocked=false){let saved=initial,observer;const attrs={},select={value:'raised'},events={},win={};
 const context={window:{addEventListener:(k,f)=>win[k]=f},document:{body:{},documentElement:{setAttribute:(k,v)=>attrs[k]=v},querySelectorAll:()=>[select],addEventListener:(k,f)=>events[k]=f},localStorage:{getItem(){if(blocked)throw Error();return saved},setItem(k,v){if(blocked)throw Error();saved=v}},MutationObserver:class{constructor(f){observer=f}observe(){}}};
 vm.runInNewContext(depth,context);return{attrs,select,change(value){events.change({target:{value,matches:()=>true}})},refresh(){select.value='raised';observer()},cross(value){saved=value;win.storage({key:'fejesMoverDepth'})}};
}
let a=appearance(null);assert.equal(a.attrs['data-fejes-depth'],'raised');a.change('flat');a.refresh();assert.equal(a.select.value,'flat');a.cross('raised');assert.equal(a.select.value,'raised');a.cross('invalid');assert.equal(a.select.value,'raised');a=appearance(null,true);a.change('flat');a.refresh();assert.equal(a.select.value,'flat');
const store={};function page(path,blocked=false){let click,destination;const back={},forward={},link={attrs:{href:path},getAttribute(k){return this.attrs[k]},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]}};
 const context={window:{},location:{pathname:path,assign:p=>destination=p},sessionStorage:{getItem:k=>{if(blocked)throw Error();return store[k]||null},setItem:(k,v)=>{if(blocked)throw Error();store[k]=v}},document:{body:{},querySelector:()=>null,querySelectorAll:s=>s==='[data-fejes-back]'?[back]:s==='[data-fejes-forward]'?[forward]:s==='.fmc-nav a'?[link]:[],addEventListener:(k,f)=>click=f},MutationObserver:class{constructor(f){}observe(){}}};
 vm.runInNewContext(nav,context);return{back,forward,link,go(direction){click({target:{closest:s=>s===`[data-fejes-${direction}]`?{}:null}});return destination}};
}
let p=page('/Tools/FejesMover');assert.equal(p.back.disabled,true);assert.equal(p.forward.disabled,true);assert.equal(p.link.attrs['aria-current'],'page');p=page('/Tools/FejesMoverSelective');assert.equal(p.back.disabled,false);assert.equal(p.go('back'),'/Tools/FejesMover');p=page('/Tools/FejesMover');assert.equal(p.forward.disabled,false);assert.equal(p.go('forward'),'/Tools/FejesMoverSelective');p=page('/Tools/FejesMoverSelective');p.go('back');page('/Tools/FejesMover');p=page('/Tools/FejesMoverSettings');assert.equal(p.forward.disabled,true);assert.equal(p.go('back'),'/Tools/FejesMover');
store.fejesMoverNavigation=JSON.stringify({items:['https://evil.invalid/'],index:0});p=page('/Tools/FejesMover');assert.equal(p.back.disabled,true);assert.equal(p.go('back'),undefined);p=page('/Tools/FejesMover',true);assert.equal(p.back.disabled,true);
assert.match(source,/prefers-reduced-motion:reduce/);assert.match(source,/data-fejes-label/);
console.log('Depth persistence, unavailable storage, scoped history, branching and invalid history protection passed.');
