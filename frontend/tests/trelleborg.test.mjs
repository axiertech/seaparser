import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../poc/trelleborg-main.mjs',import.meta.url),'utf8').replace("'./map-component.mjs'",JSON.stringify(new URL('../map/map-component.mjs',import.meta.url).href)).replace("'./coastal-view.mjs'",JSON.stringify(new URL('../poc/coastal-view.mjs',import.meta.url).href));
const {mountSwedishCoast}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const saved=JSON.parse(readFileSync(new URL('../../fixtures/trelleborg-voyage.json',import.meta.url),'utf8'));

test('same PoC displays completed Trelleborg voyage, full date, sources, GPX and frozen scope',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../poc/index.html',import.meta.url),'utf8'));
 let shown,endpoints,scene;const document=dom.window.document;
 const view=await mountSwedishCoast(document,null,async()=>new Response(JSON.stringify(saved)),(_L,_element,model)=>{scene=model;return {background(){},endpoints(a,b){endpoints=[a,b];},show(value){shown=value;}};});
 assert.ok(view);assert.equal(scene.profile,'trelleborg-stromstad');assert.equal(endpoints[0].longitude,13.15);assert.equal(endpoints[1].latitude,58.93);
 assert.equal(shown.routes.features.length,1);assert.equal(shown.routes.features[0].geometry.coordinates.length,2700);
 const results=document.getElementById('results');assert.match(results.textContent,/438.70 km.*44 h 47 min.*2026-10-21 05:46:48/);
 assert.match(results.textContent,/Vädergränser EJ verifierade/);assert.match(document.getElementById('comparison').textContent,/Jämförelse/); // one route has no comparative optimum
 assert.match(document.getElementById('mode-notice').textContent,/egna punkter.*inte aktiverade/);
 assert.match(results.querySelector('a').href,/trelleborg-water-0-estimated.gpx/);
 assert.match(results.querySelector('pre').textContent,/source_time/);
 assert.equal(document.getElementById('departure-choice').disabled,true);
 assert.equal(document.getElementById('start-lat').readOnly,true);
 dom.window.close();
});
