import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { JSDOM } from 'jsdom';
import { mount } from '../map/controller.mjs';
const source=readFileSync(new URL('../poc/poc-transport.mjs',import.meta.url),'utf8').replace("'./client.mjs'",JSON.stringify(new URL('../map/client.mjs',import.meta.url).href));
const {createPocTransport}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
// Tests import the source transport; production copies it beside the shared client.

const site=new URL('../../artifacts/poc-site/',import.meta.url);
const fetcher=async path=>path.startsWith('/api/')?new Response('{}',{status:422}):new Response(readFileSync(new URL(path,site)),{status:200});
const pause=()=>new Promise(resolve=>setImmediate(resolve));

test('published PoC: endpoints, departure, boat, limits, comparison, map selection and actual GPX',async()=>{
  const dom=new JSDOM(readFileSync(new URL('index.html',site),'utf8'));const d=dom.window.document;
  const calls=[];const view={show:(r,id)=>calls.push({r,id}),endpoints(){},background(){}};
  try{
    assert.equal(d.querySelector('h1').textContent,'SeaParser, ruttplanering för OffShore');
    const logo=d.querySelector('.brand img');assert.equal(logo.alt,'SeaParser');
    assert.equal(logo.getAttribute('src'),'assets/logos/seaparser-logo.svg');
    assert.equal(logo.width/logo.height,206/78);
    for(const link of d.querySelectorAll('link[rel="icon"]'))assert.ok(existsSync(new URL(link.getAttribute('href'),site)));
    assert.equal(d.querySelectorAll('link[rel="icon"]').length,2);
    await mount(d,()=>view,createPocTransport(fetcher));
    assert.equal(d.getElementById('start-place').options.length,3);
    assert.equal(d.getElementById('boat-profile').value,'constant-5kn');
    assert.match(d.getElementById('mode-notice').textContent,/förberäknade/);
    assert.equal(d.getElementById('assumptions').closest('details').open,false);
    const submit=async()=>{d.getElementById('plan-form').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));for(let i=0;i<10&&d.getElementById('calculate').disabled;i++)await pause();};
    await submit();assert.equal(d.querySelectorAll('.route').length,16);
    assert.match(d.querySelector('.route').textContent,/Sträcka.*M.*Vind.*m\/s.*Vågor.*m.*Ström/);
    assert.match(d.getElementById('comparison').textContent,/Samma alternativ vinner/);
    d.querySelector('.route button').click();assert.ok(calls.at(-1).id);
    const link=d.querySelector('.route a');assert.match(link.getAttribute('href'),/^gpx\//);
    assert.match(readFileSync(new URL(link.getAttribute('href'),site),'utf8'),/rtept/);
    d.getElementById('departure-choice').value='600';await submit();assert.equal(d.querySelectorAll('.route').length,4);
    d.getElementById('target-place').value='c';d.getElementById('target-place').dispatchEvent(new dom.window.Event('change'));await submit();
    assert.equal(d.querySelectorAll('.route').length,4);assert.ok(calls.at(-1).r.alternatives[0].distance_m>0);
    d.getElementById('weather-preset').value='waves';d.getElementById('weather-preset').dispatchEvent(new dom.window.Event('change'));await submit();
    assert.match(d.getElementById('status').textContent,/Ingen GPX/);assert.equal(d.querySelectorAll('.route a').length,0);
  } finally{dom.window.close();}
});

test('catalog never substitutes endpoints, missing data, boat profile or arbitrary limits',async()=>{
 const t=createPocTransport(fetcher),s=await t.loadScene();const [a,b]=s.places;
 const req={profile:'vinga-poc',start:a,target:b,boat_profile:'constant-5kn',margin_m:10,candidate_limit:4,max_wind_m_s:18,max_wave_height_m:3,departure_offsets_seconds:[0]};
 for(const change of [{profile:'synthetic'},{scenario:'unverified'},{start:{latitude:0,longitude:0}},{target:a},{boat_profile:'unknown'},{max_wave_height_m:5},{departure_offsets_seconds:[123]}])await assert.rejects(t.plan({...req,...change}));
 assert.ok((await t.plan(req)).result.alternatives.length);
});
