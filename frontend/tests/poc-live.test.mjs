import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import {mount} from '../map/controller.mjs';
import {createMap} from '../map/map-component.mjs';
const source=readFileSync(new URL('../poc/poc-transport.mjs',import.meta.url),'utf8').replace("'./client.mjs'",JSON.stringify(new URL('../map/client.mjs',import.meta.url).href));
const {createPocTransport}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(check,ms){const end=Date.now()+ms;while(Date.now()<end){if(check())return;await wait(50);}assert.fail('PoC integration timed out');}
async function assertIdle(api){const r=await fetch(api.url+(api.public?'/api/poc/health':'/api/health'));assert.equal(r.status,200);const health=await r.json();assert.deepEqual(health.active_jobs,{local:0,regional:0},'Föregående jobb måste vara avslutat och reapat före nästa test');}
async function server(){
 if(process.env.SEAPARSER_POC_URL)return {url:process.env.SEAPARSER_POC_URL.replace(/\/$/,''),public:true,close:async()=>{}};
 const root=new URL('../../',import.meta.url),local=new URL('.venv/bin/python',root),python=process.env.PYTHON||(existsSync(local)?local.pathname:'python');
 const child=spawn(python,['-B','-m','uvicorn','scripts.local_demo:poc_app','--factory','--host','127.0.0.1','--port','0','--no-access-log'],{cwd:root,stdio:['ignore','pipe','pipe']});
 let log='',url;child.stderr.on('data',x=>{log+=x;url=log.match(/http:\/\/127\.0\.0\.1:\d+/)?.[0];});
 try{await until(()=>url||child.exitCode!==null,15000);assert.ok(url,'PoC API did not bind');}catch(e){child.kill();throw e;}
 return {url,public:false,close:async()=>{if(child.exitCode!==null)return;const done=new Promise(r=>child.once('exit',r));child.kill();await done;}};
}

test('free map clicks → live real-data API → comparison → GPX; coverage/time/limits remain enforced',{timeout:240000},async()=>{
 const api=await server();let view,dom;
 try{
  await assertIdle(api);
  const html=await fetch(api.url+(api.public?'/poc/index.html':'/'));assert.equal(html.status,200);
  const text=await html.text();assert.equal(text,readFileSync(new URL('../../artifacts/poc-site/index.html',import.meta.url),'utf8'));
  dom=new JSDOM(text,{url:api.url+'/poc/'});globalThis.window=dom.window;globalThis.document=dom.window.document;
  Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true});dom.window.SVGSVGElement.prototype.createSVGRect=()=>({});
  const el=document.getElementById('map');for(const [k,v] of [['clientWidth',900],['clientHeight',610],['offsetWidth',900],['offsetHeight',610]])Object.defineProperty(el,k,{value:v});
  el.getBoundingClientRect=()=>({left:0,top:0,right:900,bottom:610,width:900,height:610});
  const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');
  const fetcher=(path,options)=>fetch(api.url+(path.startsWith('/')?(api.public?path:path.replace(/^\/api\/poc\//,'/api/')):(api.public?'/poc/':'/')+path),options);
  const transport=createPocTransport(fetcher);
  view=await mount(document,(node,scene,pick)=>createMap(L,node,scene,pick),transport);assert.ok(view);
  assert.match(document.getElementById('mode-notice').textContent,/Liveberäkning/);
  const scene=await (await fetcher('/api/poc/scene?profile=vinga-poc')).json();
  const start={latitude:scene.start[1]+.0001,longitude:scene.start[0]+.0001},target={latitude:scene.target[1]-.0001,longitude:scene.target[0]+.0001};
  const click=p=>view.map.fire('click',{latlng:L.latLng(p.latitude,p.longitude)});
  click(start);click(target);assert.equal(document.getElementById('start-place').value,'custom');assert.equal(document.getElementById('target-place').value,'custom');
  assert.equal(Number(document.getElementById('start-lat').value),Number(start.latitude.toFixed(10)));
  document.getElementById('departure-choice').value='0';
  const submit=async()=>{document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));await view.whenIdle();};
  await submit();const link=document.querySelector('.route a');assert.ok(link,document.getElementById('status').textContent);
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0,'Alla beräkningspolygoner ska vara dolda');
  assert.ok(document.querySelectorAll('path[stroke="#087156"],path[stroke="#b78023"]').length>0,'Beräknade rutter ska fortfarande visas');
  const overlay=document.querySelector('.calculation-overlay-toggle');overlay.click();
  assert.ok(document.querySelectorAll('path[stroke="#718795"]').length>=24,'Land, hinder och marginaler ska visas med samma kontroll');
  overlay.click();assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  assert.match(document.getElementById('comparison').textContent,/Kortast restid/);
  document.querySelector('.route button').click();assert.ok(document.querySelector('.route.picked'));
  const gpx=await fetcher(new URL(link.href).pathname);assert.equal(gpx.status,200);const xml=new dom.window.DOMParser().parseFromString(await gpx.text(),'application/xml');
  assert.equal(xml.querySelectorAll('parsererror').length,0);assert.ok(xml.querySelectorAll('rtept').length>=2);
  assert.ok(Math.abs(Number(xml.querySelector('rtept').getAttribute('lat'))-start.latitude)<1e-6);
  click({latitude:0,longitude:0});assert.match(document.getElementById('status').textContent,/utanför.*prognosområdet/);assert.equal(document.querySelectorAll('.route a').length,0);
  const option=document.createElement('option');option.value='43200';document.getElementById('departure-choice').append(option);document.getElementById('departure-choice').value='43200';await submit();assert.match(document.getElementById('status').textContent,/Avgången saknar/);
  await assert.rejects(transport.plan({profile:'vinga-poc',start,target,candidate_limit:4,departure_offsets_seconds:[43200]},{}),/Avgången saknar/);
  document.getElementById('departure-choice').value='0';document.getElementById('weather-preset').value='waves';document.getElementById('weather-preset').dispatchEvent(new dom.window.Event('change'));await submit();
  assert.equal(document.querySelectorAll('.route a').length,0);assert.match(document.getElementById('status').textContent,/Ingen GPX/);
 }finally{try{await view?.dispose();await assertIdle(api);}finally{dom?.window.close();await api.close();}}
});

test('published regional clicks → asynchronous real-data job → comparison → estimated GPX',{
 skip:!process.env.SEAPARSER_COASTAL_PUBLIC_TEST,timeout:300000
},async()=>{
 const api=await server();assert.equal(api.public,true,'Regional public verification requires the activated deployment');let view,dom;
 try{
  await assertIdle(api);
  const response=await fetch(api.url+'/poc/index.html?example=vinga-uddevalla');assert.equal(response.status,200);
  const html=await response.text();assert.equal(html,readFileSync(new URL('../../artifacts/poc-site/index.html',import.meta.url),'utf8'));
  dom=new JSDOM(html,{url:api.url+'/poc/'});globalThis.window=dom.window;globalThis.document=dom.window.document;
  dom.window.SVGSVGElement.prototype.createSVGRect=()=>({});const element=document.getElementById('map');
  for(const [k,v] of [['clientWidth',1000],['clientHeight',610]])Object.defineProperty(element,k,{value:v});
  const require=createRequire(import.meta.url);delete require.cache[require.resolve('leaflet')];const L=require('leaflet');
  const source=readFileSync(new URL('../poc/uddevalla-main.mjs',import.meta.url),'utf8')
   .replace("'./map-component.mjs'",JSON.stringify(new URL('../map/map-component.mjs',import.meta.url).href))
   .replace("'./client.mjs'",JSON.stringify(new URL('../map/client.mjs',import.meta.url).href))
   .replace("'./coastal-view.mjs'",JSON.stringify(new URL('../poc/coastal-view.mjs',import.meta.url).href));
  const {mountRegional}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  const fetcher=(path,options)=>fetch(api.url+(path.startsWith('/')?path:'/poc/'+path),options);
  view=await mountRegional(document,L,fetcher);assert.ok(view);
  const coastal=JSON.parse(readFileSync(new URL('../../fixtures/coastal-voyage.json',import.meta.url),'utf8'));
  const a=coastal.routes[0].path[20],b=coastal.routes[0].path.at(-20);
  view.map.fire('click',{latlng:L.latLng(a[1],a[0])});view.map.fire('click',{latlng:L.latLng(b[1],b[0])});
  assert.equal(document.getElementById('start-place').value,'custom');assert.equal(document.getElementById('target-place').value,'custom');
  document.getElementById('departure-choice').value='0';
  document.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));
  assert.equal(document.getElementById('calculate').disabled,true);
  await view.whenIdle();
  assert.match(document.getElementById('status').textContent,/Beräkning klar för dina val/);
  assert.ok(document.querySelectorAll('#results .route').length>=1);
  assert.match(document.getElementById('results').textContent,/kortast restid.*HÖG OSÄKERHET/);
  assert.equal(document.querySelectorAll('path[stroke="#718795"]').length,0);
  const link=document.querySelector('#results a');assert.match(link.getAttribute('href'),/^\/api\/poc\/coastal\/plans\/[a-f0-9]{32}\/routes\//);
  const exported=await fetch(link.href);assert.equal(exported.status,200);const xml=new dom.window.DOMParser().parseFromString(await exported.text(),'application/xml');
  assert.equal(xml.querySelectorAll('parsererror').length,0);assert.ok(xml.querySelectorAll('rtept').length>=2);
  assert.ok(Math.abs(Number(xml.querySelector('rtept').getAttribute('lat'))-a[1])<1e-8);
  assert.match(xml.querySelector('metadata desc').textContent,/Vädergränser EJ verifierade/);
  document.querySelector('#results button').click();assert.ok(document.querySelector('.route.picked'));
  view.map.fire('click',{latlng:L.latLng(0,0)});assert.equal(document.querySelectorAll('#results a').length,0);
 }finally{try{await view?.dispose();await assertIdle(api);}finally{dom?.window.close();await api.close();}}
});
