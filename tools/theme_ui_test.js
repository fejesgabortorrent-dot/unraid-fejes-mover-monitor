const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(__dirname+'/../src/FejesMoverRuntime.php','utf8');
const source=[...text.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
function env(initial,blocked=false){let stored=initial,observer;const attrs={},select={value:'auto'},events={},win={};
const context={window:{addEventListener:(k,f)=>win[k]=f},document:{body:{},documentElement:{setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k]},querySelectorAll:()=>[select],addEventListener:(k,f)=>events[k]=f},localStorage:{getItem(){if(blocked)throw Error();return stored},setItem(k,v){if(blocked)throw Error();stored=v}},MutationObserver:class{constructor(f){observer=f}observe(){}}};
vm.runInNewContext(source,context);return{attrs,select,stored:()=>stored,change(value){events.change({target:{value,matches:()=>true}})},refresh(){select.value='auto';observer()},cross(value){stored=value;win.storage({key:'fejesMoverTheme'})}};}
let e=env(null);assert.equal(e.attrs['data-fejes-theme'],undefined);e.change('light');assert.equal(e.attrs['data-fejes-theme'],'light');assert.equal(e.stored(),'light');e.refresh();assert.equal(e.select.value,'light');
assert.equal(env(e.stored()).attrs['data-fejes-theme'],'light');e.change('dark');assert.equal(e.attrs['data-fejes-theme'],'dark');e.change('auto');assert.equal(e.attrs['data-fejes-theme'],undefined);
e.cross('dark');assert.equal(e.select.value,'dark');e.cross('invalid');assert.equal(e.attrs['data-fejes-theme'],undefined);
e=env('invalid');assert.equal(e.select.value,'auto');e=env(null,true);e.change('dark');e.refresh();assert.equal(e.select.value,'dark');assert.equal(e.attrs['data-fejes-theme'],'dark');
console.log('Theme defaults, persistence, banner refresh, cross-tab changes and blocked storage passed.');
