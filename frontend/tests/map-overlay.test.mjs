import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import {createMap as localCreateMap} from '../map/map-component.mjs';

for(const source of ['local',...(process.env.SEAPARSER_PUBLIC_MAP_TEST==='1'?['https']:[])]) for(const profile of ['vinga','uddevalla']) test(`${source}/${profile}: all added land, hulls and margins toggle together; base tiles and routes remain`,async()=>{
 const publicRoot='https://seaparser.com/poc/';
 const publicRead=async name=>{const response=await fetch(publicRoot+name+'?overlay-test='+Date.now());assert.equal(response.status,200);assert.ok(response.url.startsWith(publicRoot));return response.text();};
 const createMap=source==='https'?(await import('data:text/javascript;base64,'+Buffer.from(await publicRead('map-component.mjs')).toString('base64'))).createMap:localCreateMap;
 const read=async name=>source==='https'?await publicRead(name):readFileSync(new URL('../../artifacts/poc-site/'+name,import.meta.url),'utf8');
 let scene=JSON.parse(await read('scene.json'));
 if(profile==='uddevalla'){
  const data=JSON.parse(await read('vinga-uddevalla.json')),[w,s,e,n]=data.bbox;
  scene={...scene,profile:'vinga-uddevalla',map_min_zoom:7,land_display:data.coastline_display,obstacles:{type:'FeatureCollection',features:[]},coverage:{type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}]}};
 }
 const original=JSON.stringify(scene);const dom=new JSDOM('<!doctype html><div id="map"></div>',{pretendToBeVisual:true});
 const old={window:globalThis.window,document:globalThis.document};globalThis.window=dom.window;globalThis.document=dom.window.document;
 const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');let view;
 try{
  const element=document.getElementById('map');Object.defineProperty(element,'clientWidth',{value:800});Object.defineProperty(element,'clientHeight',{value:480});
  view=createMap(L,element,scene,()=>{});
  view.background();
  const tileLayers=()=>{let count=0;view.map.eachLayer(layer=>{if(layer instanceof L.TileLayer)count++;});return count;};
  assert.equal(tileLayers(),1,'Baskartans kustlinjer ska finnas kvar');
  const landCount=L.geoJSON(scene.land_display).getLayers().length;
  const obstacleCount=L.geoJSON(scene.obstacles).getLayers().length;
  assert.ok(landCount>0);if(profile==='vinga')assert.ok(obstacleCount>0);
  assert.equal(document.querySelectorAll('.leaflet-overlay-pane path').length,1,'Endast täckningsramen får synas vid första laddning');
  const line={type:'Feature',properties:{id:'route',kind:'accepted',candidate:'route',status:'arrived'},geometry:{type:'LineString',coordinates:[scene.start,scene.target]}};
  const result={obstacles:scene.obstacles,routes:{type:'FeatureCollection',features:[line]}};const raw=JSON.stringify(result);
  view.show(result);
  const toggle=document.querySelector('.calculation-overlay-toggle');
  assert.equal(toggle.textContent,'Visa beräkningsunderlag');assert.equal(toggle.getAttribute('aria-pressed'),'false');
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  assert.equal(document.querySelectorAll('path[stroke="#9a5830"]').length,0,'Inget brunt landlager ska visas');
  assert.equal(document.querySelectorAll('.leaflet-overlay-pane path').length,2,'Endast täckningsram och beräknad rutt får synas');
  assert.equal(document.querySelectorAll('path[stroke="#087156"]').length,1);
  toggle.click();assert.equal(toggle.textContent,'Dölj beräkningsunderlag');assert.equal(toggle.getAttribute('aria-pressed'),'true');
  const paths=[...document.querySelectorAll('path[stroke="#718795"]')];assert.equal(paths.length,landCount+2*obstacleCount,'Alla landkonturer, hinderhöljen och resultatmarginaler ska visas');
  assert.ok(paths.every(p=>p.getAttribute('stroke-width')==='1'&&p.getAttribute('stroke-dasharray')==='4 5'&&(p.getAttribute('fill')==='none'||p.getAttribute('fill-opacity')==='0')));
  view.show(result);assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,paths.length);
  assert.equal(tileLayers(),1);
  toggle.click();assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  view.show(result);assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  assert.equal(document.querySelectorAll('.leaflet-overlay-pane path').length,2);assert.equal(tileLayers(),1);assert.equal(document.querySelectorAll('path[stroke="#087156"]').length,1);
  assert.equal(JSON.stringify(scene),original);assert.equal(JSON.stringify(result),raw);
 }finally{view?.dispose();dom.window.close();for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});
