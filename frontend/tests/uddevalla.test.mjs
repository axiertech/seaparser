import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../poc/uddevalla-main.mjs',import.meta.url),'utf8').replace("'./map-component.mjs'",JSON.stringify(new URL('../map/map-component.mjs',import.meta.url).href));
const {mountRegional,missingCell}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const data=JSON.parse(readFileSync(new URL('../../fixtures/vinga-uddevalla-preflight.json',import.meta.url),'utf8'));

test('regional native masks reject missing corners and outside points; zero is not a gap',()=>{
 const product={longitude:[11,12],latitude:[57,58],node_valid_all_times:[[true,true],[true,false]]};
 assert.equal(missingCell(product,{longitude:11.1,latitude:57.1}),'missing');
 assert.equal(missingCell(product,{longitude:13,latitude:57.1}),'outside');
 product.node_valid_all_times[1][1]=true;assert.equal(missingCell(product,{longitude:11.1,latitude:57.1}),'present');
});

test('same PoC displays real regional samples, actual Leaflet coverage/clicks and refuses fabricated GPX',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../poc/index.html',import.meta.url),'utf8'),{pretendToBeVisual:true});
 const old={window:globalThis.window,document:globalThis.document,HTMLElement:globalThis.HTMLElement};
 globalThis.window=dom.window;globalThis.document=dom.window.document;globalThis.HTMLElement=dom.window.HTMLElement;
 const document=dom.window.document;Object.defineProperty(document.getElementById('map'),'clientWidth',{value:1000});Object.defineProperty(document.getElementById('map'),'clientHeight',{value:610});
 const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');let view;
 try{
  const requests=[];view=await mountRegional(document,L,async path=>{requests.push(path);return new Response(JSON.stringify(data));});
  assert.ok(view,document.getElementById('status').textContent);assert.equal(view.map.getMinZoom(),7);
  assert.deepEqual(requests,['vinga-uddevalla.json']);assert.equal(document.getElementById('regional-summary').hidden,false);
  assert.match(document.getElementById('regional-samples').textContent,/Vind.*m\/s.*Vågor.*m Hs.*Ström/);
  assert.match(document.getElementById('regional-samples').textContent,/1\/4 hörn saknas/);
  assert.match(document.getElementById('status').textContent,/Mål.*vågor.*ström.*Ingen ruttberäkning eller GPX/);
  assert.equal(document.querySelectorAll('#results a').length,0);assert.match(document.getElementById('regional-distance').textContent,/inte en beräknad.*Restid.*ej beräknade/);
  document.getElementById('departure-choice').value='30';document.getElementById('departure-choice').dispatchEvent(new dom.window.Event('change'));
  assert.match(document.getElementById('regional-samples').textContent,/1\/4 hörn saknas/);
  view.map.fire('click',{latlng:L.latLng(0,0)});assert.match(document.getElementById('status').textContent,/utanför källans native-grid/);
  assert.equal(document.querySelectorAll('#results a').length,0);assert.equal(requests.length,1);
  assert.ok(document.querySelector('#example-choice option[value="vinga"]'));
 }finally{view?.dispose();dom.window.close();for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});
