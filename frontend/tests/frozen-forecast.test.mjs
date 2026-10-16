import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const page = readFileSync(new URL('../../artifacts/vinga-frozen-review/index.html', import.meta.url), 'utf8');
function review(html = page) {
  const errors = [], console = new VirtualConsole();
  console.on('jsdomError', e => errors.push(e));
  const dom = new JSDOM(html, { runScripts:'dangerously', virtualConsole:console });
  assert.deepEqual(errors, []);
  const d = dom.window.document;
  const change = (id,value,event='change') => { d.getElementById(id).value = value; d.getElementById(id).dispatchEvent(new dom.window.Event(event)); assert.deepEqual(errors, []); };
  return { dom, d, change };
}

test('standalone artifact embeds current presentation assets', () => {
  for (const name of ['js','css']) assert.ok(page.includes(readFileSync(new URL(`../presentation/frozen-forecast.${name}`, import.meta.url),'utf8')));
  assert.ok(!/\bfetch\s*\(|XMLHttpRequest|navigator\.geolocation/.test(page));
});

test('real wind grid, time slider, selected point and all raw quantities are interactive', () => {
  const {dom,d,change} = review();
  assert.equal(d.querySelectorAll('#grid circle').length,56);
  assert.match(d.getElementById('values').textContent,/12.970281/);
  assert.match(d.getElementById('values').textContent,/159/);
  assert.equal(d.querySelectorAll('#series-table tr').length,5);
  change('timeline','4','input');
  assert.equal(d.getElementById('time').value,'4');
  assert.match(d.getElementById('plot-title').textContent,/2026-10-13 16:00:00 UTC/);
  change('node','55');
  assert.match(d.getElementById('values').textContent,/15.915022/);
  assert.match(d.getElementById('coordinates').textContent,/-199442.2, -588322/);
  change('field','direction');
  assert.match(d.getElementById('plot-title').textContent,/FRÅN/);
  assert.match(d.getElementById('legend').textContent,/142 – 160 °/);
  assert.match(d.getElementById('mask').textContent,/Markandel/);
  assert.equal(d.querySelectorAll('#grid path').length,0); // No invented vector arrows.
  const first = d.querySelector('#grid circle');
  first.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  assert.equal(d.getElementById('node').value,'0');
  dom.window.close();
});

test('waves and current retain different native grids and separate mask/source identities', () => {
  const {dom,d,change} = review();
  d.querySelector('[data-product="waves"]').click();
  assert.equal(d.querySelectorAll('#grid circle').length,4);
  assert.match(d.getElementById('coordinates').textContent,/11.597147941589355/);
  assert.match(d.getElementById('values').textContent,/1.2349779605865479/);
  assert.match(d.getElementById('mask').textContent,/1 – hav/);
  assert.match(d.getElementById('hashes').textContent,/wave-mask.nc/);
  change('field','VTM02');
  assert.match(d.getElementById('series-table').textContent,/2.9598515033721924 s/);
  d.querySelector('[data-product="current"]').click();
  assert.match(d.getElementById('coordinates').textContent,/11.597127914428711/);
  assert.match(d.getElementById('values').textContent,/-0.2828807234764099/);
  assert.match(d.getElementById('mask').textContent,/okänd/);
  assert.doesNotMatch(d.getElementById('hashes').textContent,/wave-mask/);
  assert.match(d.getElementById('source-times').textContent,/Okänd – inte verifierad/);
  assert.match(d.getElementById('extent').textContent,/57.64155197143555/);
  dom.window.close();
});

test('explicit gaps, land, unknown masks and zero values are distinguishable', () => {
  const raw = JSON.parse(page.match(/<script id="review-data" type="application\/json">(.*?)<\/script>/s)[1]);
  const wave = raw.products[1];
  wave.fields.VHM0.values[0] = [[null,0],[2,3]];
  wave.mask = [[0,1],[null,1]];
  const altered = page.replace(/(<script id="review-data" type="application\/json">).*?(<\/script>)/s, (_,a,b)=>a+JSON.stringify(raw)+b);
  const {dom,d,change} = review(altered);
  d.querySelector('[data-product="waves"]').click();
  assert.match(d.getElementById('legend').textContent,/1 saknade prov av 4/);
  assert.match(d.getElementById('legend').textContent,/2 punkter utan havsmask, varav 1 okända/);
  assert.match(d.getElementById('values').textContent,/Saknat prov/);
  assert.match(d.getElementById('mask').textContent,/0 – land/);
  assert.match(d.getElementById('series-table').textContent,/Saknat prov/);
  change('node','1');
  assert.match(d.getElementById('series-table').textContent,/0 m/);
  change('node','2');
  assert.match(d.getElementById('mask').textContent,/okänd/);
  dom.window.close();
});

test('whole segment envelope and raw support follow times and stay on wind grid', () => {
  const {dom,d,change} = review();
  assert.equal(d.getElementById('segment-review').hidden,false);
  assert.match(d.getElementById('segment-summary').textContent,/9 platser vid 4 sparade tider, sammanlagt 36 prov/);
  assert.equal(d.querySelectorAll('[data-segment-envelope]').length,0);
  const toggle=d.getElementById('segment-toggle'); toggle.checked=true;
  toggle.dispatchEvent(new dom.window.Event('change'));
  assert.equal(d.querySelectorAll('[data-segment-envelope]').length,1);
  assert.equal(d.querySelectorAll('[data-segment-support]').length,9);
  assert.match(d.getElementById('segment-status').textContent,/9 punkter/);
  change('node','16'); // row 2, column 2 in source node order.
  assert.match(d.getElementById('segment-node').textContent,/Vald punkt ingår i/);
  change('timeline','4','input');
  assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
  assert.match(d.getElementById('segment-status').textContent,/0 punkter/);
  assert.match(d.getElementById('segment-node').textContent,/ingår inte/);
  change('time','2');
  assert.equal(d.querySelectorAll('[data-segment-support]').length,9);
  d.querySelector('[data-product="waves"]').click();
  assert.equal(d.getElementById('segment-review').hidden,true);
  assert.equal(d.querySelectorAll('[data-segment-envelope]').length,0);
  assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
  d.querySelector('[data-product="current"]').click();
  assert.equal(d.getElementById('segment-review').hidden,true);
  assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
  assert.match(d.getElementById('semantics').textContent,/Källan beskriver inte tidsmedlet/);
  d.querySelector('[data-product="wind"]').click();
  assert.equal(d.querySelectorAll('[data-segment-support]').length,9);
  toggle.checked=false; toggle.dispatchEvent(new dom.window.Event('change'));
  assert.equal(d.querySelectorAll('[data-segment-envelope]').length,0);
  dom.window.close();
});

test('mixed source identity or a qualification flag cannot enable segment overlay', () => {
  for (const mutate of [raw => { raw.segment_review.source_hashes['native-wind-land.txt']='0'.repeat(64); },
                         raw => { raw.segment_review.physical_source_support_qualified=true; }]) {
    const raw=JSON.parse(page.match(/<script id="review-data" type="application\/json">(.*?)<\/script>/s)[1]);
    mutate(raw);
    const altered=page.replace(/(<script id="review-data" type="application\/json">).*?(<\/script>)/s,(_,a,b)=>a+JSON.stringify(raw)+b);
    const {dom,d}=review(altered);
    assert.equal(d.getElementById('segment-review').hidden,true);
    d.getElementById('segment-toggle').checked=true;
    d.getElementById('segment-toggle').dispatchEvent(new dom.window.Event('change'));
    assert.equal(d.querySelectorAll('[data-segment-envelope]').length,0);
    assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
    dom.window.close();
  }
});

test('real negative artifact shows full space/time failure without clipped support', () => {
  const outside=readFileSync(new URL('../../artifacts/vinga-outside-review/index.html',import.meta.url),'utf8');
  const {dom,d,change}=review(outside);
  assert.equal(d.getElementById('segment-review').hidden,false);
  assert.match(d.getElementById('segment-summary').textContent,/grader latitud\/longitud/);
  assert.match(d.getElementById('segment-outcome').textContent,/sparade koordinatgränser/);
  assert.match(d.getElementById('segment-outcome').textContent,/tidsintervall lämnar/);
  const toggle=d.getElementById('segment-toggle'); toggle.checked=true;
  toggle.dispatchEvent(new dom.window.Event('change'));
  const envelope=d.querySelector('[data-segment-envelope]'), coverage=d.querySelector('[data-source-coverage]');
  assert.ok(envelope && coverage);
  assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
  assert.equal(d.querySelectorAll('#grid circle[role="button"]').length,56);
  // The entire un-clipped enclosure fits inside plotting coordinates after axis expansion.
  assert.ok(Number(envelope.getAttribute('x'))>=80-1e-9);
  assert.ok(Number(envelope.getAttribute('x'))+Number(envelope.getAttribute('width'))<=665+1e-9);
  assert.ok(Number(envelope.getAttribute('y'))>=50-1e-9);
  assert.ok(Number(envelope.getAttribute('y'))+Number(envelope.getAttribute('height'))<=350+1e-9);
  assert.ok(Number(coverage.getAttribute('width'))<585 || Number(coverage.getAttribute('height'))<300);
  change('time','2');
  assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
  assert.match(d.getElementById('segment-node').textContent,/ofullständigt/);
  assert.match(d.getElementById('extent').textContent,/-205442.2 till -199442.2/);
  d.querySelector('[data-product="current"]').click();
  assert.equal(d.getElementById('segment-review').hidden,true);
  assert.equal(d.querySelectorAll('[data-segment-envelope]').length,0);
  dom.window.close();
});

test('budget and missing-corner failures stay visible but never mark partial nodes', () => {
  for (const reason of ['source_cell_budget_exceeded','missing_or_nonfinite_raw_node']) {
    const raw=JSON.parse(page.match(/<script id="review-data" type="application\/json">(.*?)<\/script>/s)[1]);
    raw.segment_review.raw_inventory_complete=false;
    raw.segment_review.inventory_failures=[reason];
    // Retain all raw nodes deliberately: partial evidence must not be green-lit.
    const altered=page.replace(/(<script id="review-data" type="application\/json">).*?(<\/script>)/s,(_,a,b)=>a+JSON.stringify(raw)+b);
    const {dom,d}=review(altered);
    assert.equal(d.getElementById('segment-review').hidden,false);
    assert.match(d.getElementById('segment-summary').textContent,/Fullständigt sparat stöd saknas/);
    d.getElementById('segment-toggle').checked=true;
    d.getElementById('segment-toggle').dispatchEvent(new dom.window.Event('change'));
    assert.equal(d.querySelectorAll('[data-segment-envelope]').length,1);
    assert.equal(d.querySelectorAll('[data-segment-support]').length,0);
    assert.match(d.getElementById('segment-status').textContent,/Inget fullständigt stöd/);
    dom.window.close();
  }
});
