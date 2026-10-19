import { createMap } from './map-component.mjs';
import { mount } from './controller.mjs';
import { createPocTransport } from './poc-transport.mjs';
const example=document.getElementById('example-choice');let view;
const regional=new URL(location.href).searchParams.get('example')==='vinga-uddevalla';
example.value=regional?'vinga-uddevalla':'vinga';
example.addEventListener('change',async()=>{example.disabled=true;try{await view?.dispose();const url=new URL(location.href);if(example.value==='vinga')url.searchParams.delete('example');else url.searchParams.set('example',example.value);location.assign(url);}catch(error){document.getElementById('status').textContent=error.message;example.disabled=false;}});
window.addEventListener('pagehide',()=>{view?.dispose().catch(error=>console.error(error.message));});
if(regional){const {mountRegional}=await import('./uddevalla-main.mjs');view=await mountRegional(document,window.L);if(view){const {attachCoastalView}=await import('./coastal-view.mjs');attachCoastalView(document,view).show();}}
else {
view=await mount(document,(element,scene,pick)=>{
  const view=createMap(window.L,element,scene,pick);
  if(window.L.control.scale) window.L.control.scale({imperial:false}).addTo(view.map);
  for(const p of scene.places||[]){
    const text=document.createElement('span');text.textContent=p.label;
    window.L.circleMarker([p.latitude,p.longitude],{radius:10,color:'#075b64',fillColor:'#fffefa',fillOpacity:.9,weight:2}).bindTooltip(text).addTo(view.map);
  }
  return view;
},createPocTransport());
if(view)document.getElementById('plan-form').dispatchEvent(new Event('submit',{cancelable:true}));
}
