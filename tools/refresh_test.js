// Execute the actual page scripts with controlled DOM and deferred fetches.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function script(name) {
  const marker = name === 'FejesMover.page' ? 'window.fejesMoverTimer' : 'window.fejesMoverDashTimer';
  const matches = [...fs.readFileSync(path.join(__dirname, '../src', name), 'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)];
  // Source contains precompiled language branches plus a PHP-backed title
  // script. Execute the actual Hungarian polling branch, not that title.
  const found = matches.filter(match => match[1].includes(marker)).at(-1);
  assert.ok(found, 'Polling script missing: '+name);
  return found[1];
}
function environment() {
  const elements = {};
  let tick, resolveFetch, responsePart;
  const context = {
    window: {}, document: {hidden: false, getElementById: id => elements[id]},
    location: {href: '/Tools/FejesMover'}, AbortController,
    setInterval: fn => {tick = fn; return 1;}, clearInterval() {},
    setTimeout: () => 1, clearTimeout() {},
    fetch: () => new Promise(resolve => {resolveFetch = resolve;}),
    DOMParser: class {parseFromString() {return {getElementById: () => responsePart};}}
  };
  return {elements, context, tick: () => tick(), respond(part) {
    responsePart = part;
    resolveFetch({ok: true, text: async () => ''});
  }};
}
async function main() {
  const e = environment();
  e.elements['fm-toggle'] = {};
  e.elements['fm-error'] = {};
  e.elements['fm-monitor'] = {replaceWith() {e.elements['fm-toggle'] = {textContent: 'Automatikus frissítés: BE (5 mp)'};}};
  vm.runInNewContext(script('FejesMover.page'), e.context);
  const pending = e.tick();
  e.elements['fm-toggle'].onclick();
  assert.match(e.elements['fm-toggle'].textContent, /SZÜNET/);
  e.respond({});
  await pending;
  assert.match(e.elements['fm-toggle'].textContent, /SZÜNET/);
  e.context.fetch = () => {throw Error('Paused polling must not fetch');};
  await e.tick();
  e.elements['fm-toggle'].onclick();
  assert.match(e.elements['fm-toggle'].textContent, /BE/);
  console.log('PASS: in-flight refresh preserves pause label and polling state; resume works');

  const d = environment();
  for (const id of ['fmd-status','fmd-percent','fmd-ring','fmd-free','fmd-updated']) d.elements[id] = {style: {}};
  d.elements['fmd-mode']={replaceChildren(banner){this.banner=banner;}};
  vm.runInNewContext(script('FejesMover.Dashboard.page'), d.context);
  for (const [available, used, free, expected] of [['1','0','100','0%'], ['0','0','—','—'], ['1','100','0,0','100%'], ['0','0','—','—']]) {
    const poll = d.tick();
    const banner={mode:available==='1'?'observer':'demo',pool:used==='100'?'fast':'cache'};
    d.respond({querySelector:()=>banner,dataset: {mode:banner.mode,pool:banner.pool,running: '0', uncertain: '0', available, used, free}});
    await poll;
    assert.equal(d.elements['fmd-percent'].textContent, expected);
    assert.equal(d.elements['fmd-free'].textContent, free);
    assert.equal(d.elements['fmd-mode'].banner,banner);
    assert.equal(d.elements['fmd-status'].textContent,banner.mode==='demo'?'DEMO':'● Várakozik');
    assert.match(d.elements['fmd-ring'].style.background, new RegExp(available === '1' ? used+'%' : '0%'));
  }
  console.log('PASS: dashboard refresh handles empty, missing, full and lost cache readings');
}
main().catch(error => {console.error(error); process.exitCode = 1;});
