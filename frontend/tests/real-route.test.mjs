import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

test('verkliga ruttkort markerar rätt bana och behåller tydliga antaganden', () => {
  const html = readFileSync(new URL('../../artifacts/real-route-review/index.html', import.meta.url), 'utf8');
  assert.ok(!/\b(?:src|href)\s*=\s*["']https?:/i.test(html));
  const dom = new JSDOM(html, { runScripts: 'dangerously' });
  try {
    const doc = dom.window.document;
    const cards = [...doc.querySelectorAll('[data-select]')];
    const paths = [...doc.querySelectorAll('[data-route]')];
    assert.equal(cards.length, 4); assert.equal(paths.length, 4);
    assert.ok(doc.querySelectorAll('svg polyline').length >= 8);
    assert.match(doc.body.textContent, /MET-vind \+ Copernicus-vågor och ström/);
    assert.match(doc.body.textContent, /Utfärdandetid antas/);
    assert.match(doc.body.textContent, /Ingen aktuell prognos/);
    assert.match(doc.body.textContent, /Vind 1[0-9]\.\d{2} m\/s/);
    cards[1].click();
    assert.equal(doc.querySelectorAll('.selected').length, 1);
    for (const path of paths) assert.equal(path.style.opacity, path.dataset.route === cards[1].dataset.select ? '1' : '0.12');
    doc.getElementById('all').click();
    assert.equal(doc.querySelectorAll('.selected').length, 0);
    assert.ok(paths.every(path => path.style.opacity === '1'));
  } finally { dom.window.close(); }
});
