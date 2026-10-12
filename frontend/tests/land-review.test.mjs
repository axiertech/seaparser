import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

test('land review separates overlays and loads tiles only after manual opt-in',async()=>{
 const dom=new JSDOM('<button id="background">Bakgrund</button>');
 let tiles=0;const files=[],styles=[];
 const old={L:globalThis.L,fetch:globalThis.fetch,document:globalThis.document};
 globalThis.document=dom.window.document;
 globalThis.fetch=async url=>{files.push(url);return {ok:true,json:async()=>({type:'FeatureCollection',features:[]})};};
 const map={setView(){return this;},attributionControl:{addAttribution(text){assert.match(text,/OpenStreetMap/);}}};
 globalThis.L={map:()=>map,geoJSON:(data,options)=>{styles.push(options.style.color);return {addTo(){}};},
 tileLayer:(url,options)=>{tiles++;assert.equal(url,'https://tile.openstreetmap.org/{z}/{x}/{y}.png');assert.equal(options.maxNativeZoom,19);return {addTo(){}};}};
 try {
  const source=readFileSync(new URL('../map/land-review.mjs',import.meta.url),'utf8');
  await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  assert.deepEqual(files,['land.geojson','routing.geojson']);assert.deepEqual(styles,['orange','red']);assert.equal(tiles,0);
  const button=dom.window.document.querySelector('button');button.click();button.click();assert.equal(tiles,1);assert.equal(button.disabled,true);
 } finally {Object.assign(globalThis,old);dom.window.close();}
});
