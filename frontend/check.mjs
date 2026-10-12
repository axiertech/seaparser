// Validate local review assets; no dependencies, server, browser or network.
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const html = readFileSync(new URL('./scenario-demo.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('./scenario-demo.css', import.meta.url), 'utf8');
assert.ok(html.startsWith('<!doctype html>') && html.includes('lang="sv"'));
assert.ok(html.includes("default-src 'none'") && html.includes('Content-Security-Policy'));
assert.ok(!/<script\b|<iframe\b|\b(?:src|href)\s*=\s*["']https?:/i.test(html));
assert.ok(!/@import\b|url\s*\(|<\/style/i.test(css));
assert.deepEqual([...html.matchAll(/\$([A-Z_]+)/g)].map(x => x[1]).sort(), ['NAV', 'SCENARIOS', 'STYLE']);
console.log('Lokala HTML/CSS-resurser och frånvaro av externa beroenden godkända');

const mapHtml = readFileSync(new URL('./map/index.html', import.meta.url), 'utf8');
assert.ok(mapHtml.includes('connect-src \'self\''));
assert.ok(!/\b(?:src|href)\s*=\s*["']https?:/i.test(mapHtml));
for (const file of ['map/main.mjs', 'map/controller.mjs', 'map/client.mjs', 'map/map-component.mjs', 'build.mjs']) {
  const source = readFileSync(new URL('./'+file, import.meta.url), 'utf8');
  assert.ok(!source.includes('navigator.geolocation'));
}
