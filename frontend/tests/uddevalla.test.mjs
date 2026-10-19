import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
const source=readFileSync(new URL('../poc/uddevalla-main.mjs',import.meta.url),'utf8').replace("'./map-component.mjs'",JSON.stringify(new URL('../map/map-component.mjs',import.meta.url).href)).replace("'./client.mjs'",JSON.stringify(new URL('../map/client.mjs',import.meta.url).href)).replace("'./coastal-view.mjs'",JSON.stringify(new URL('../poc/coastal-view.mjs',import.meta.url).href));
const {mountRegional,missingCell}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const data=JSON.parse(readFileSync(new URL('../../fixtures/vinga-uddevalla-preflight.json',import.meta.url),'utf8'));

test('regional disposal awaits an in-flight response without touching the closed DOM',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../poc/index.html',import.meta.url),'utf8'));
 let release,polled=false;const delayed=new Promise(r=>release=r),id='b'.repeat(32);
 const layer={addTo(){return this;}},L={layerGroup:()=>layer,geoJSON:()=>layer};
 const view=await mountRegional(dom.window.document,L,async(path,options)=>{
  if(path==='vinga-uddevalla.json')return new Response(JSON.stringify(data));
  if(options?.method==='POST')return new Response(JSON.stringify({id,poll_timeout_seconds:255}));
  polled=true;await delayed;return new Response(JSON.stringify({status:'completed',result:{}}));
 },()=>({map:{},background(){},show(){},endpoints(){},dispose(){}}));
 dom.window.document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
 for(let i=0;i<20&&!polled;i++)await new Promise(r=>setImmediate(r));assert.equal(polled,true);
 // An invalid second submission must also retain the first job's cleanup chain.
 dom.window.document.getElementById('start-lat').value='0';
 dom.window.document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
 let finished=false;const stopped=view.dispose().then(()=>finished=true);
 dom.window.close();await new Promise(r=>setImmediate(r));assert.equal(finished,false);
 release();await stopped;await view.whenIdle();assert.equal(finished,true);
});

test('regional native masks reject missing corners and outside points; zero is not a gap',()=>{
 const product={longitude:[11,12],latitude:[57,58],node_valid_all_times:[[true,true],[true,false]]};
 assert.equal(missingCell(product,{longitude:11.1,latitude:57.1}),'missing');
 assert.equal(missingCell(product,{longitude:13,latitude:57.1}),'outside');
 product.node_valid_all_times[1][1]=true;assert.equal(missingCell(product,{longitude:11.1,latitude:57.1}),'present');
});

test('same PoC displays source gaps and free regional points without fabricating a computed GPX',async()=>{
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
  assert.match(document.getElementById('status').textContent,/Mål.*vågor.*ström.*landmedvetna reservdata.*Hög osäkerhet/);
  assert.equal(document.querySelectorAll('#results a').length,0);assert.match(document.getElementById('regional-distance').textContent,/inte en beräknad.*Restid.*ej beräknade/);
  document.getElementById('departure-choice').value='30';document.getElementById('departure-choice').dispatchEvent(new dom.window.Event('change'));
  assert.match(document.getElementById('regional-samples').textContent,/1\/4 hörn saknas/);
  view.map.fire('click',{latlng:L.latLng(0,0)});assert.match(document.getElementById('status').textContent,/utanför källans native-grid/);
  assert.equal(document.querySelectorAll('#results a').length,0);assert.equal(requests.length,1);
  assert.ok(document.querySelector('#example-choice option[value="vinga"]'));
 }finally{await view?.dispose();dom.window.close();for(const [key,value] of Object.entries(old)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});

test('free regional clicks post selected points, show long-job status, compare routes and clear stale GPX',async()=>{
 const dom=new JSDOM(readFileSync(new URL('../poc/index.html',import.meta.url),'utf8'),{pretendToBeVisual:true,url:'https://seaparser.com/poc/'});
 const old={window:globalThis.window,document:globalThis.document};globalThis.window=dom.window;globalThis.document=dom.window.document;
 dom.window.SVGSVGElement.prototype.createSVGRect=()=>({});const document=dom.window.document,element=document.getElementById('map');
 for(const [k,v] of [['clientWidth',1000],['clientHeight',610]])Object.defineProperty(element,k,{value:v});
 const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');let view,body,release;
 const completed=new Promise(r=>release=r),id='a'.repeat(32);
 const voyage=JSON.parse(readFileSync(new URL('../../fixtures/coastal-voyage.json',import.meta.url),'utf8'));
 voyage.comparison={fastest_candidate:'water-0',comfortable_candidate:'water-0',max_comfort_extra_seconds:300};
 try{
  const fetcher=async(path,options)=>{
   if(path==='vinga-uddevalla.json')return new Response(JSON.stringify(data));
   if(options?.method==='POST'){body=JSON.parse(options.body);return new Response(JSON.stringify({id,poll_timeout_seconds:255,server_timeout_seconds:240}));}
   assert.equal(path,`/api/poc/coastal/plans/${id}`);
   await completed;return new Response(JSON.stringify({status:'completed',result:voyage}));
  };
  view=await mountRegional(document,L,fetcher);assert.ok(view);
  const a=data.probes.start.position,b=data.probes.target.position;
  view.map.fire('click',{latlng:L.latLng(a.latitude,a.longitude)});view.map.fire('click',{latlng:L.latLng(b.latitude,b.longitude)});
  document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  for(let i=0;i<100&&(!body||!document.getElementById('status').textContent.includes('Köad'));i++)await wait(10);
  assert.deepEqual(body.start,{latitude:a.latitude,longitude:a.longitude});assert.deepEqual(body.target,{latitude:b.latitude,longitude:b.longitude});
  assert.equal(body.candidate_limit,2);assert.equal(body.max_wave_height_m,3);
  assert.equal(document.getElementById('calculate').disabled,true);assert.match(document.getElementById('status').textContent,/Köad.*60 s.*240 s/);
  release();for(let i=0;i<100&&document.getElementById('calculate').disabled;i++)await wait(10);
  assert.match(document.getElementById('status').textContent,/Beräkning klar för dina val/);
  assert.match(document.getElementById('results').textContent,/kortast restid.*komfortval.*HÖG OSÄKERHET/);
  assert.equal(document.querySelector('#results a').getAttribute('href'),`/api/poc/coastal/plans/${id}/routes/water-0/gpx`);
  document.querySelector('#results button').click();assert.ok(document.querySelector('.route.picked'));
  view.map.fire('click',{latlng:L.latLng(0,0)});assert.equal(document.querySelectorAll('#results a').length,0);
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
 }finally{release();for(let i=0;i<100&&document.getElementById('calculate').disabled;i++)await new Promise(r=>setTimeout(r,10));await view?.dispose();dom.window.close();for(const [k,v] of Object.entries(old)){if(v===undefined)delete globalThis[k];else globalThis[k]=v;}}
});
