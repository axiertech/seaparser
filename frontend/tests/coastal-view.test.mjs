import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import {attachCoastalView} from '../poc/coastal-view.mjs';
const source=readFileSync(new URL('../poc/uddevalla-main.mjs',import.meta.url),'utf8').replace("'./map-component.mjs'",JSON.stringify(new URL('../map/map-component.mjs',import.meta.url).href));
const {mountRegional}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const raw=JSON.parse(readFileSync(new URL('../../fixtures/vinga-uddevalla-preflight.json',import.meta.url),'utf8'));
const voyage=JSON.parse(readFileSync(new URL('../../fixtures/coastal-voyage.json',import.meta.url),'utf8'));
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(check){for(let i=0;i<200;i++){if(check())return;await wait(10);}assert.fail('Coastal presentation did not finish');}

test('same PoC shows actual uncertain route, comparison, sources and GPX; changed points/time remove it',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../poc/index.html',import.meta.url),'utf8'),{pretendToBeVisual:true});
 const old={window:globalThis.window,document:globalThis.document};globalThis.window=dom.window;globalThis.document=dom.window.document;
 dom.window.SVGSVGElement.prototype.createSVGRect=()=>({});
 const document=dom.window.document,element=document.getElementById('map');
 for(const [key,value] of [['clientWidth',1000],['clientHeight',610]])Object.defineProperty(element,key,{value});
 const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');let view;
 try{
  view=await mountRegional(document,L,async()=>new Response(JSON.stringify(raw)));assert.ok(view);
  attachCoastalView(document,view,async()=>new Response(JSON.stringify(voyage)));
  const show=document.getElementById('show-coastal-voyage');show.click();await until(()=>!show.disabled);
  assert.match(document.getElementById('comparison').textContent,/1 faktiskt simulerat.*hög osäkerhet/);
  assert.match(document.getElementById('results').textContent,/88\.96 km.*9 h 34 min/);
  assert.match(document.getElementById('results').textContent,/Vädergränser EJ verifierade/);
  assert.equal(document.querySelectorAll('path[stroke="#b78023"][stroke-dasharray="8 5"]').length,1);
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  assert.match(document.querySelector('#results a').getAttribute('href'),/coastal-water-0-estimated\.gpx/);
  assert.match(document.querySelector('#results pre').textContent,/source_longitude.*[\s\S]*source_time/);
  document.querySelector('.calculation-overlay-toggle').click();assert.ok(document.querySelectorAll('path[stroke="#718795"]').length>0);
  assert.equal(document.querySelectorAll('path[stroke="#b78023"]').length,1);
  view.map.fire('click',{latlng:L.latLng(0,0)});assert.equal(document.querySelectorAll('#results a').length,0);
  assert.equal(document.querySelectorAll('path[stroke="#b78023"]').length,0);
  show.click();await until(()=>!show.disabled);assert.ok(document.querySelector('#results a'));
  document.getElementById('departure-choice').value='1';document.getElementById('departure-choice').dispatchEvent(new dom.window.Event('change'));
  assert.equal(document.querySelectorAll('#results a').length,0);assert.equal(document.querySelectorAll('path[stroke="#b78023"]').length,0);
 }finally{view?.dispose();dom.window.close();for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});
