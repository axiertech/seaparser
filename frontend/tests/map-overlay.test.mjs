import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import {createMap} from '../map/map-component.mjs';

test('calculation overlay is hidden, toggles thin outlines, and preserves coastline/routes/geometry',()=>{
 const scene=JSON.parse(readFileSync(new URL('../../artifacts/poc-site/scene.json',import.meta.url)));
 const original=JSON.stringify(scene);const dom=new JSDOM('<!doctype html><div id="map"></div>',{pretendToBeVisual:true});
 const old={window:globalThis.window,document:globalThis.document};globalThis.window=dom.window;globalThis.document=dom.window.document;
 const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');let view;
 try{
  const element=document.getElementById('map');Object.defineProperty(element,'clientWidth',{value:800});Object.defineProperty(element,'clientHeight',{value:480});
  view=createMap(L,element,scene,()=>{});
  const line={type:'Feature',properties:{id:'route',kind:'accepted',candidate:'route',status:'arrived'},geometry:{type:'LineString',coordinates:[scene.start,scene.target]}};
  const result={obstacles:scene.obstacles,routes:{type:'FeatureCollection',features:[line]}};const raw=JSON.stringify(result);
  view.show(result);
  const toggle=document.querySelector('.calculation-overlay-toggle');
  assert.equal(toggle.textContent,'Visa beräkningsunderlag');assert.equal(toggle.getAttribute('aria-pressed'),'false');
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  const coasts=document.querySelectorAll('path[stroke="#9a5830"]').length;assert.ok(coasts>0);
  assert.equal(document.querySelectorAll('path[stroke="#087156"]').length,1);
  toggle.click();assert.equal(toggle.textContent,'Dölj beräkningsunderlag');assert.equal(toggle.getAttribute('aria-pressed'),'true');
  const paths=[...document.querySelectorAll('path[stroke="#718795"]')];assert.ok(paths.length>=24);
  assert.ok(paths.every(p=>p.getAttribute('stroke-width')==='1'&&p.getAttribute('stroke-dasharray')==='4 5'&&p.getAttribute('fill-opacity')==='0'));
  view.show(result);assert.ok(document.querySelectorAll('path[stroke="#718795"]').length>=24);
  toggle.click();assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  view.show(result);assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  assert.equal(document.querySelectorAll('path[stroke="#9a5830"]').length,coasts);assert.equal(document.querySelectorAll('path[stroke="#087156"]').length,1);
  assert.equal(JSON.stringify(scene),original);assert.equal(JSON.stringify(result),raw);
 }finally{view?.dispose();dom.window.close();for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});
