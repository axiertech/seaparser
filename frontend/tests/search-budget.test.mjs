import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { mount } from '../map/controller.mjs';

test('utvecklingsval skickar fyra kandidater/fyra avgångar och visar gemensam vinnare', async () => {
  const dom = new JSDOM(readFileSync(new URL('../map/index.html', import.meta.url), 'utf8'));
  try {
    const doc = dom.window.document;
    const result = JSON.parse(readFileSync(new URL('../../artifacts/real-route-budget/result.json', import.meta.url)));
    const points = result.alternatives[0].waypoints;
    let submitted;
    await mount(doc, () => ({ show() {}, endpoints() {} }), {
      loadScene: async () => ({ profile: 'vinga', start: points[0], target: points.at(-1), obstacles: result.obstacles, default_margin_m: 10, notice: result.notice }),
      plan: async payload => { submitted = payload; return { id: 'a'.repeat(32), result }; },
    });
    doc.getElementById('search-budget').value = '4:0,600,3600,10800';
    doc.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit', { cancelable: true }));
    await new Promise(resolve => setImmediate(resolve));
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
