const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(__dirname+'/../src/FejesMoverRuntime.php','utf8');
const source=[...text.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
function env(initial,blocked=false,hostColor="rgb(240, 240, 240)"){let stored=initial,observer;const attrs={},select={value:'auto'},events={},win={};
const context={getComputedStyle:()=>({color:hostColor}),window:{addEventListener:(k,f)=>win[k]=f},document:{body:{},documentElement:{setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k]},querySelectorAll:()=>[select],addEventListener:(k,f)=>events[k]=f},localStorage:{getItem(){if(blocked)throw Error();return stored},setItem(k,v){if(blocked)throw Error();stored=v}},MutationObserver:class{constructor(f){observer=f}observe(){}}};
vm.runInNewContext(source,context);return{attrs,select,stored:()=>stored,change(value){events.change({target:{value,matches:()=>true}})},refresh(){select.value='auto';observer()},cross(value){stored=value;win.storage({key:'fejesMoverTheme'})}};}
let e=env(null);assert.equal(e.attrs['data-fejes-theme'],'auto');
for(const name of ['white','black','gray','azure']){e.change(name);assert.equal(e.attrs['data-fejes-theme'],name);assert.equal(e.stored(),name);e.refresh();assert.equal(e.select.value,name);assert.equal(env(e.stored()).attrs['data-fejes-theme'],name);}
e.change('auto');assert.equal(e.attrs['data-fejes-theme'],'auto');e.cross('gray');assert.equal(e.select.value,'gray');e.cross('invalid');assert.equal(e.attrs['data-fejes-theme'],'auto');
assert.equal(env('light').attrs['data-fejes-theme'],'white');assert.equal(env('dark').attrs['data-fejes-theme'],'black');
e=env(null,true);e.change('black');e.refresh();assert.equal(e.select.value,'black');assert.equal(e.attrs['data-fejes-theme'],'black');
console.log('Unraid palettes, automatic theme, legacy preference migration, refresh, cross-tab and blocked storage passed.');
