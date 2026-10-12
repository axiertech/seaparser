import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { spawn, spawnSync } from 'node:child_process';
import { JSDOM } from 'jsdom';
import { mount, category } from '../map/controller.mjs';
import { createMap } from '../map/map-component.mjs';
import { plan, loadScene } from '../map/client.mjs';

const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate, timeout = 10000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { if (predicate()) return; await wait(20); }
  assert.fail('Tidsgräns i integrationskontrollen');
}
const root = new URL('../../', import.meta.url);
async function server(profile = 'synthetic') {
  if (process.env.SEAPARSER_DEMO_URL) return { url: process.env.SEAPARSER_DEMO_URL.replace(/\/$/, ''), async close() {} };
  const local = new URL('.venv/bin/python', root);
  const python = existsSync(local) ? local.pathname : 'python';
  if (profile === 'vinga') {
    const generated = spawnSync(python, ['-B', '-m', 'scripts.land_preview', '--bundle', '--output', 'frontend/land-dist'], { cwd: root, encoding: 'utf8' });
    assert.equal(generated.status, 0, 'Regional bundleexport misslyckades');
  }
  const app = profile === 'vinga' ? ['scripts.local_demo:regional_app', '--factory'] : ['api.main:app'];
  const child = spawn(python, ['-B', '-m', 'uvicorn', ...app, '--host', '127.0.0.1', '--port', '0', '--no-access-log'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; let url;
  child.stderr.on('data', data => { log += data.toString(); url = log.match(/http:\/\/127\.0\.0\.1:\d+/)?.[0]; });
  try { await until(() => url || child.exitCode !== null); assert.ok(url, 'Lokalt API startade inte'); }
  catch (error) { child.kill(); throw error; }
  return { url, async close() { const done = new Promise(resolve => child.once('exit', resolve)); child.kill('SIGTERM'); await done; } };
}

for (const profile of process.env.SEAPARSER_DEMO_URL && process.env.SEAPARSER_DEMO_PROFILE !== 'vinga' ? ['synthetic'] : ['synthetic','vinga']) test(`${profile}: kartklick → verklig API-process → Leaflet-rutter → GPX`, async () => {
  const api = await server(profile);
  let view;
  try {
    const fetcher = (path, options) => fetch(api.url + path, options);
    let html = readFileSync(new URL('../map/index.html', import.meta.url), 'utf8');
    if (profile === 'vinga') {
      const page = await fetch(api.url + '/vinga.html'); assert.equal(page.status, 200); html = await page.text();
      for (const name of ['land.geojson', 'routing.geojson', 'controller.mjs', 'map-component.mjs', 'client.mjs', 'vendor/leaflet.js']) {
        const asset = await fetch(api.url + '/' + name); assert.equal(asset.status, 200);
        assert.equal(Buffer.compare(Buffer.from(await asset.arrayBuffer()), readFileSync(new URL('../land-dist/' + name, import.meta.url))), 0);
      }
      assert.match(html, /Djup och landfullständighet okända/);
    }
    if (process.env.SEAPARSER_DEMO_URL) {
      const pagePath = process.env.SEAPARSER_DEMO_PROFILE === 'vinga' && profile === 'synthetic' ? '/synthetic.html' : '/';
      const response = await fetch(api.url + pagePath); assert.equal(response.status, 200);
      html = await response.text();
      assert.equal(Buffer.compare(Buffer.from(html), readFileSync(new URL(profile === 'vinga' ? '../land-dist/vinga.html' : '../dist/index.html', import.meta.url))), 0, 'Publik index.html avviker från verifierad build');
      for (const name of ['map.css', 'main.mjs', 'map-component.mjs', 'controller.mjs', 'client.mjs', 'vendor/leaflet.js', 'vendor/leaflet.css']) {
        const asset = await fetch(api.url + '/' + name); assert.equal(asset.status, 200);
        if (name.endsWith('.mjs')) assert.match(asset.headers.get('content-type') || '', /javascript/);
        assert.equal(Buffer.compare(Buffer.from(await asset.arrayBuffer()), readFileSync(new URL((profile === 'vinga' ? '../land-dist/' : '../dist/') + name, import.meta.url))), 0, 'Publik resurs avviker: ' + name);
      }
    }
    const dom = new JSDOM(html, { url: api.url, pretendToBeVisual: true });
    globalThis.window = dom.window; globalThis.document = dom.window.document;
    Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true });
    dom.window.SVGSVGElement.prototype.createSVGRect = () => ({});
    const element = document.getElementById('map');
    for (const [name, value] of [['clientWidth', 800], ['clientHeight', 480], ['offsetWidth', 800], ['offsetHeight', 480]]) Object.defineProperty(element, name, { value });
    element.getBoundingClientRect = () => ({ x: 0, y: 0, left: 0, top: 0, right: 800, bottom: 480, width: 800, height: 480 });
    const require = createRequire(import.meta.url); delete require.cache[require.resolve('leaflet')];
    const L = require('leaflet');
    const transport = { loadScene: () => loadScene(fetcher,profile), plan: (payload, options) => plan(payload, { ...options, fetcher, pause: () => wait(profile === 'vinga' ? 250 : 10) }) };
    view = await mount(document, (node, scene, pick) => createMap(L, node, scene, pick), transport);
    assert.ok(view);
    const scene = await loadScene(fetcher,profile);
    assert.ok([...document.querySelectorAll('path[stroke="#9a5830"]')].some(path => Number(path.getAttribute('stroke-width')) > 3), 'Vald routingmarginal saknas på kartan');
    if (profile === 'vinga') {
      assert.equal(document.getElementById('margin').value, '10');
      assert.ok(document.querySelector('#background'));
      assert.equal(document.querySelectorAll('.leaflet-tile').length, 0, 'Bakgrund måste vara opt-in');
    }
    view.map.fire('click', { latlng: L.latLng(scene.start[1], scene.start[0]) });
    view.map.fire('click', { latlng: L.latLng(scene.target[1], scene.target[0]) });
    assert.equal(Number(document.getElementById('start-lat').value), Number(scene.start[1].toFixed(10)));
    assert.equal(Number(document.getElementById('target-lon').value), Number(scene.target[0].toFixed(10)));
    document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }));
    await until(() => !document.getElementById('calculate').disabled, profile === 'vinga' ? 25000 : 15000);
    assert.ok(document.querySelector('a[download]'), document.getElementById('status').textContent + ' ' + [...document.querySelectorAll('.route')].map(card => card.textContent).join(' | '));
    assert.ok(document.querySelectorAll('.leaflet-overlay-pane path').length > 3, 'Verklig Leaflet-geometri saknas');
    assert.ok(document.querySelectorAll('.route').length > 1);
    const choose = document.querySelector('.route button'); choose.click();
    assert.ok(document.querySelector('.route.picked'));
    const link = document.querySelector('a[download]');
    const response = await fetch(link.href); assert.equal(response.status, 200);
    const xml = new dom.window.DOMParser().parseFromString(await response.text(), 'application/xml');
    assert.equal(xml.querySelectorAll('parsererror').length, 0);
    assert.ok(xml.querySelectorAll('rtept').length >= 3);
    assert.equal(xml.querySelectorAll('trk').length, 0);
    assert.ok(Number(xml.querySelector('rtept').getAttribute('lat')) > 57);
    if (profile === 'vinga') {
      assert.match(xml.querySelector('metadata desc').textContent, /Ej navigationssäkert/);
      assert.match(document.getElementById('provenance').textContent, /seaparser-estimated-vinga-weather/);
      assert.match(document.getElementById('provenance').textContent, /"depth": "unknown"/);
      document.getElementById('scenario').value = 'weather-limit';
      document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }));
      await until(() => document.querySelector('.route.exceeded'), 25000);
      assert.equal(document.querySelectorAll('a[download]').length, 0);
      document.getElementById('scenario').value = 'missing-waves';
      document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }));
      await until(() => document.querySelector('.route.unknown'), 25000);
      assert.equal(document.querySelectorAll('a[download]').length, 0);
      assert.match(document.getElementById('results').textContent, /Otillräckliga data/);
    }
    // Changing any input must remove stale results and the old export link.
    document.getElementById('margin').value = '3';
    document.getElementById('margin').dispatchEvent(new dom.window.Event('input', { bubbles: true }));
    assert.equal(document.querySelectorAll('a[download]').length, 0);
    view.dispose(); view = null; dom.window.close();
  } finally { view?.dispose(); await api.close(); }
});

test('endast fullständigt verifierad ankomst är grön; hårt väderfel rött', () => {
  const safe = { status: 'arrived', weather_segment_status: 'verified', arrival_weather_status: 'passed_at_arrival' };
  assert.equal(category(safe), 'verified');
  assert.equal(category({ ...safe, arrival_weather_status: 'not_checked' }), 'unknown');
  assert.equal(category({ ...safe, weather_segment_status: 'unverified' }), 'unknown');
  assert.equal(category({ status: 'weather_limit' }), 'exceeded');
});

test('misslyckad API-beräkning ger uttryckligt fel', async () => {
  const id = 'a'.repeat(32); let calls = 0;
  const fetcher = async () => ({ ok: true, json: async () => ++calls === 1 ? { id } : { status: 'failed', reason: 'Tidsgräns' } });
  await assert.rejects(plan({}, { fetcher, pause: async () => {} }), /Tidsgräns/);
});

test('publik build har endast uttryckliga frontendfiler och lokala resurser', () => {
  const expected = ['client.mjs', 'controller.mjs', 'index.html', 'main.mjs', 'map-component.mjs', 'map.css', 'vendor'];
  assert.deepEqual(readdirSync(new URL('../dist/', import.meta.url)).sort(), expected);
  const html = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');
  assert.ok(!/(?:src|href)="https?:/i.test(html));
  assert.ok(!html.includes('geolocation'));
  assert.ok(existsSync(new URL('../dist/vendor/leaflet-LICENSE.txt', import.meta.url)));
});
