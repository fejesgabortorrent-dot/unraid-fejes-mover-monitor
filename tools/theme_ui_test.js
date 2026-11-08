const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const text=fs.readFileSync(__dirname+'/../src/FejesMoverRuntime.php','utf8');
const source=[...text.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
function env(initial,blocked=false,hostColor="rgb(240, 240, 240)",host={}){let stored=initial,observer;const props={},attrs={},select={value:'auto'},events={},win={};
const context={getComputedStyle:()=>({color:hostColor,getPropertyValue:key=>host[key]||''}),window:{addEventListener:(k,f)=>win[k]=f},document:{body:{},documentElement:{style:{setProperty:(k,v)=>props[k]=v},setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k]},querySelectorAll:()=>[select],addEventListener:(k,f)=>events[k]=f},localStorage:{getItem(){if(blocked)throw Error();return stored},setItem(k,v){if(blocked)throw Error();stored=v}},MutationObserver:class{constructor(f){observer=f}observe(){}}};
vm.runInNewContext(source,context);return{attrs,props,select,stored:()=>stored,change(value){events.change({target:{value,matches:()=>true}})},refresh(){select.value='auto';observer()},cross(value){stored=value;win.storage({key:'fejesMoverTheme'})}};}
let e=env(null);assert.equal(e.attrs['data-fejes-theme'],'auto');
for(const name of ['white','black','gray','azure']){e.change(name);assert.equal(e.attrs['data-fejes-theme'],name);assert.equal(e.stored(),name);e.refresh();assert.equal(e.select.value,name);assert.equal(env(e.stored()).attrs['data-fejes-theme'],name);}
e.change('auto');assert.equal(e.attrs['data-fejes-theme'],'auto');e.cross('gray');assert.equal(e.select.value,'gray');e.cross('invalid');assert.equal(e.attrs['data-fejes-theme'],'auto');
assert.equal(env('light').attrs['data-fejes-theme'],'white');assert.equal(env('dark').attrs['data-fejes-theme'],'black');
e=env(null,true);e.change('black');e.refresh();assert.equal(e.select.value,'black');assert.equal(e.attrs['data-fejes-theme'],'black');
console.log('Unraid palettes, automatic theme, legacy preference migration, refresh, cross-tab and blocked storage passed.');

// Follow Unraid keeps host surfaces but repairs unreadable foreground colors.
for(const host of [
 {'--background-color':'#1d1b1b','--mild-background-color':'#121510','--text-color':'#606e7f'},
 {'--background-color':'#f2f2f2','--mild-background-color':'#ffffff','--text-color':'#cccccc'}
]){const auto=env(null,false,'',host);assert.ok(['#f0f3f7','#202a36'].includes(auto.props['--fejes-auto-fg']));assert.equal(auto.attrs['data-fejes-theme'],'auto');}
const rgb=h=>h.match(/[0-9a-f]{2}/gi).map(x=>parseInt(x,16)/255),lum=c=>c.map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0),ratio=(a,b)=>(Math.max(lum(rgb(a)),lum(rgb(b)))+.05)/(Math.min(lum(rgb(a)),lum(rgb(b)))+.05);
for(const name of ['white','black','gray','azure']){
 const rule=text.match(new RegExp('html\\[data-fejes-theme="'+name+'"\\]\\{([^}]+)\\}'))[1],tokens=Object.fromEntries([...rule.matchAll(/(--fejes-[\w-]+):(#[0-9a-f]{6})/g)].map(m=>[m[1],m[2]]));
 for(const surface of ['--fejes-bg','--fejes-panel','--fejes-control']){assert.ok(ratio(tokens['--fejes-fg'],tokens[surface])>=7,name+' text contrast');assert.ok(ratio(tokens['--fejes-muted'],tokens[surface])>=4.5,name+' secondary text contrast');}
}
console.log('Shared palettes retain at least 7:1 main text and 4.5:1 secondary text contrast; automatic foreground repair passed.');
