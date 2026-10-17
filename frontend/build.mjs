// Explicit public allowlist. No repository/config/log files enter the webroot.
import { mkdirSync, copyFileSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const out = new URL('./dist/', import.meta.url);
mkdirSync(out, { recursive: true });
for (const name of ['index.html', 'map.css', 'main.mjs', 'map-component.mjs', 'controller.mjs', 'client.mjs']) copyFileSync(new URL(`./map/${name}`, import.meta.url), new URL(name, out));
mkdirSync(new URL('vendor/images/', out), { recursive: true });
for (const name of ['leaflet.js', 'leaflet.css']) copyFileSync(new URL(`./node_modules/leaflet/dist/${name}`, import.meta.url), new URL(`vendor/${name}`, out));
copyFileSync(new URL('./node_modules/leaflet/LICENSE', import.meta.url), new URL('vendor/leaflet-LICENSE.txt', out));
for (const name of readdirSync(new URL('./node_modules/leaflet/dist/images/', import.meta.url))) copyFileSync(new URL(`./node_modules/leaflet/dist/images/${name}`, import.meta.url), new URL(`vendor/images/${name}`, out));
console.log('Publika kartfiler genererade i frontend/dist; inget publicerat.');

const native = readFileSync(new URL('./map/index.html', import.meta.url), 'utf8').replace('data-profile="vinga"', 'data-profile="vinga-native"').replace('2026-10-13', '2026-10-17');
writeFileSync(new URL('native.html', out), native);
