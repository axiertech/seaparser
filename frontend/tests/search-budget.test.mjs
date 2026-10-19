import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { mount } from '../map/controller.mjs';

test('disposing a pending controller prevents late writes to a closed DOM',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../map/index.html',import.meta.url),'utf8'));
 const result=JSON.parse(readFileSync(new URL('../../artifacts/real-route-budget/result.json',import.meta.url),'utf8'));
 let release,started=false;const delayed=new Promise(r=>release=r);
 const view=await mount(dom.window.document,()=>({show(){},endpoints(){},dispose(){}}),{
  loadScene:async()=>({profile:'synthetic',start:[11,58],target:[11,58.001],obstacles:result.obstacles,notice:'test'}),
  plan:async()=>{started=true;await delayed;return {id:'a'.repeat(32),result};}
 });
 dom.window.document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
 await new Promise(r=>setImmediate(r));assert.equal(started,true);
 const stopped=view.dispose();dom.window.close();release();await stopped;await view.whenIdle();
});

for (const [profile, artifact] of [['vinga', 'real-route-budget'], ['vinga-native', 'supported-native-routes']]) test(`${profile}: utvecklingsval och rätt avgångstider visar gemensam vinnare`, async () => {
  const dom = new JSDOM(readFileSync(new URL('../map/index.html', import.meta.url), 'utf8'));
  try {
    const doc = dom.window.document; doc.documentElement.dataset.profile = profile;
    const result = JSON.parse(readFileSync(new URL(`../../artifacts/${artifact}/result.json`, import.meta.url)));
    const points = result.alternatives[0].waypoints;
    let submitted;
    await mount(doc, () => ({ show() {}, endpoints() {} }), {
      loadScene: async () => ({ profile, departure: result.weather_at_start.time, start: points[0], target: points.at(-1), obstacles: result.obstacles, default_margin_m: 10, notice: result.notice }),
      plan: async payload => { submitted = payload; return { id: 'a'.repeat(32), result }; },
    });
    doc.getElementById('search-budget').value = '4:0,600,3600,10800';
    doc.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit', { cancelable: true }));
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(submitted.profile, profile);
    assert.match(doc.getElementById('search-budget').options[0].textContent, profile === 'vinga-native' ? /01:00, 01:10/ : /12:00, 12:10/);
    assert.equal(doc.getElementById('scenario-label').hidden, true);
    assert.equal(submitted.candidate_limit, 4);
    assert.deepEqual(submitted.departure_offsets_seconds, [0, 600, 3600, 10800]);
    assert.equal(doc.querySelectorAll('.route').length, 16);
    assert.match(doc.getElementById('comparison').textContent, /Samma alternativ vinner båda kriterierna/);
    assert.match(doc.querySelector('.route').textContent, /Komfortexponering \(ej validerad\)/);
    doc.getElementById('search-budget').dispatchEvent(new dom.window.Event('input', { bubbles: true }));
    assert.equal(doc.querySelectorAll('.route').length, 0);
    assert.equal(doc.getElementById('comparison').textContent, '');
  } finally { dom.window.close(); }
});
