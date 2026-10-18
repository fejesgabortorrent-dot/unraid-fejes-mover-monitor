// Dependency-free checks for the shipped interface's language catalog and decisions.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../docs/demo/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
assert.ok(!/<table\b/i.test(html), 'The interface must stay card-based');
const catalog = script.slice(0, script.indexOf('const $='));
const decision = script.slice(script.indexOf('function decision('), script.indexOf('function renderHistory('));
const sandbox = {};
vm.runInNewContext(catalog + decision + ';globalThis.catalog=translations;globalThis.decide=decision;', sandbox);
const keys = Object.keys(sandbox.catalog.hu).sort();
for (const lang of ['hu', 'en', 'de']) {
  const t = sandbox.catalog[lang];
  assert.deepEqual(Object.keys(t).sort(), keys, lang+' catalog differs');
  for (const key of keys) assert.ok(t[key].length, lang+': empty '+key);
  assert.equal(t.scenarios.length, 9);
  for (const match of html.matchAll(/data-t="([^"]+)"/g)) assert.equal(typeof t[match[1]], 'string', lang+': '+match[1]);
}
const cases = [
  [{free:633},300,'enough'], [{free:300},300,'enough'],
  [{free:100},300,'ready'], [{free:100,torrent:'busy'},300,'defer'],
  [{free:100,torrent:'unknown'},300,'defer'], [{free:100,backup:'busy'},300,'defer'],
  [{free:100,parity:'busy'},300,'defer'], [{free:100,cooldown:'waiting'},300,'defer'],
  [{free:633,mount:false},300,'defer'], [{free:100},50,'enough'],
];
for (const [state, threshold, expected] of cases) {
  const [result, reason] = sandbox.decide(state, threshold);
  assert.equal(result, expected);
  for (const lang of ['hu','en','de']) {
    assert.equal(typeof sandbox.catalog[lang][result], 'string');
    assert.equal(typeof sandbox.catalog[lang][reason], 'string');
  }
}
console.log('PASS: demo JavaScript syntax, 3 complete catalogs, 9 scenarios and 10 decision checks');
