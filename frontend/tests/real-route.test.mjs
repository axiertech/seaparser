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
    const cards = [...doc.querySelectorAll('.card[data-select]')];
    const paths = [...doc.querySelectorAll('[data-route]')];
    assert.equal(cards.length, 4); assert.equal(paths.length, 4);
    assert.ok(doc.querySelectorAll('svg polyline').length >= 8);
    assert.match(doc.body.textContent, /MET-vind \+ Copernicus-vågor och ström/);
    assert.match(doc.body.textContent, /Utfärdandetid antas/);
    assert.match(doc.body.textContent, /Ingen aktuell prognos/);
    assert.match(doc.body.textContent, /Vind 1[0-9]\.\d{2} m\/s/);
    cards[1].click();
    assert.equal(doc.querySelectorAll('.card.selected').length, 1);
    for (const path of paths) assert.equal(path.style.opacity, path.dataset.route === cards[1].dataset.select ? '1' : '0.12');
    doc.getElementById('all').click();
    assert.equal(doc.querySelectorAll('.selected').length, 0);
    assert.ok(paths.every(path => path.style.opacity === '1'));
  } finally { dom.window.close(); }
});


test('utökad jämförelse visar 16 alternativ, budget, samma vinnare och klickbart exponeringsdiagram', () => {
  const html = readFileSync(new URL('../../artifacts/real-route-budget/index.html', import.meta.url), 'utf8');
  const dom = new JSDOM(html, { runScripts: 'dangerously' });
  try {
    const doc = dom.window.document;
    assert.equal(doc.querySelectorAll('.card').length, 16);
    assert.equal(doc.querySelectorAll('.exposure [data-select]').length, 16);
    assert.match(doc.body.textContent, /Samma alternativ vinner båda kriterierna/);
    assert.match(doc.body.textContent, /4 kandidater × 4 avgångar = högst 16/);
    assert.match(doc.body.textContent, /Trunkerad: ja/);
    assert.match(doc.body.textContent, /Geometrisk ordning är inte väderoptimalitet/);
    const dot = doc.querySelectorAll('.exposure [data-select]')[9];
    dot.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    assert.equal(doc.querySelector('.card.selected').dataset.select, dot.dataset.select);
    assert.equal(doc.querySelector('[data-route][style*="opacity: 1"]').dataset.route, dot.dataset.select);
    assert.ok(!/\b(?:src|href)\s*=\s*["']https?:/i.test(html));
  } finally { dom.window.close(); }
});

test('rörelseramsgranskning visar fysisk fart separat från kartposition och markerar bana', () => {
  const html = readFileSync(new URL('../../artifacts/motion-route-review/index.html', import.meta.url), 'utf8');
  const dom = new JSDOM(html, { runScripts: 'dangerously' });
  try {
    const doc = dom.window.document;
    assert.equal(doc.querySelectorAll('.card').length, 16);
    assert.match(doc.body.textContent, /17 oktober 2026/);
    assert.match(doc.body.textContent, /fysiska öst\/nord-hastigheter i m\/s/);
    assert.match(doc.body.textContent, /positionens ändring/);
    assert.match(doc.body.textContent, /inte kvalificerad navigation/);
    assert.match(doc.body.textContent, /Beräknad med uttryckliga antaganden/);
    const card = doc.querySelectorAll('.card')[5]; card.click();
    assert.equal(doc.querySelector('[data-route][style*="opacity: 1"]').dataset.route, card.dataset.select);
    assert.ok(!/\b(?:src|href)\s*=\s*["']https?:/i.test(html));
  } finally { dom.window.close(); }
});
