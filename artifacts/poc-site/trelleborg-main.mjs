// Saved result from the existing engine; no forecast extrapolation in the UI.
import {createMap} from './map-component.mjs';
import {renderCoastalView} from './coastal-view.mjs';

export async function mountSwedishCoast(document,L,fetcher=fetch,mapFactory=createMap){
 const get=id=>document.getElementById(id),empty={type:'FeatureCollection',features:[]};
 try{
  const response=await fetcher('trelleborg-voyage.json');if(!response.ok)throw new Error('Den simulerade kustfärden kunde inte läsas');
  const data=await response.json();if(data.profile!=='trelleborg-stromstad')throw new Error('Fel kustscenario');
  const scenario=data.scenario,[w,s,e,n]=scenario.bbox;
  const view=mapFactory(L,get('map'),{profile:data.profile,map_min_zoom:5,coverage:{type:'FeatureCollection',features:[{type:'Feature',properties:{kind:'source_extract_extent'},geometry:{type:'Polygon',coordinates:[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}}]},obstacles:empty},()=>{});
  view.background();view.endpoints(scenario.start,scenario.target);
  get('planning-title').textContent='Trelleborg–Strömstad';
  document.querySelector('.snapshot').textContent='Frysta prognoser · 19–21 oktober 2026';
  document.querySelector('.map-heading span').textContent='Trelleborg–Strömstad · simulerad kustfärd';
  document.querySelector('.map-note').textContent='Hela accepterade segment kontrolleras mot sparat OSM-vatten med 10 m modellmarginal. Djup och landfullständighet är okända. OSM-bakgrunden är inte officiellt sjökort.';
  get('regional-summary').hidden=false;get('regional-summary').querySelector('h2').textContent='Prognosfönster och färdens omfattning';
  get('regional-samples').replaceChildren();get('show-gaps').closest('label').hidden=true;
  get('show-gaps').closest('label').nextElementSibling.hidden=true;
  get('regional-validity').textContent=`Gemensamt underlag ${scenario.valid_from} – ${scenario.valid_until}. 49 timmar från avgång. Samma MET-körning saknar senare giltigheter; inga prognoser extrapoleras.`;
  const option=(id,value,text)=>{const node=get(id);node.replaceChildren();const o=document.createElement('option');o.value=value;o.textContent=text;node.append(o);node.disabled=true;};
  for(const name of ['start','target']){
   option(name+'-place',name,scenario[name].label);get(name+'-lat').value=scenario[name].latitude;get(name+'-lon').value=scenario[name].longitude;
   get(name+'-lat').readOnly=true;get(name+'-lon').readOnly=true;get('choose-'+name).disabled=true;
  }
  option('departure-choice','saved',scenario.departure);get('departure-choice').previousSibling.textContent='Sparad avgång · UTC';
  option('boat-profile','constant-5kn','Konstantfart 5 kn · uppskattad');
  option('weather-preset','saved',`Vind ≤${data.configuration.max_wind_m_s} m/s · Hs ≤${data.configuration.max_wave_height_m} m`);
  get('wind-limit').value=data.configuration.max_wind_m_s;get('wave-limit').value=data.configuration.max_wave_height_m;
  get('calculate').textContent='Visa sparad simulerad färd';
  const show=()=>{renderCoastalView(document,view,data,{gpx:id=>`gpx/trelleborg-${encodeURIComponent(id)}-estimated.gpx`,evidenceUrl:'trelleborg-voyage.json'});
   get('regional-blocker').textContent='En sparad kandidat och en avgång har simulerats. Fria punkter och nya avgångar är inte aktiverade för detta scenario. Reservdata och källantaganden redovisas per segment. Hög osäkerhet; vädergränser ej verifierade.';
   get('status').textContent=`Sparad modellfärd · avgång ${scenario.departure}. Ankomst ${data.routes[0]?.arrival_time??'målet ej nått'}. Hög osäkerhet; vädergränser ej verifierade.`;
   get('mode-notice').textContent+=' Detta scenario visar en sparad beräkning; egna punkter och nya avgångar är inte aktiverade.';};
  get('plan-form').addEventListener('submit',event=>{event.preventDefault();show();});
  get('background').disabled=true;get('background').textContent='OSM-kartbakgrund visas';show();return view;
 }catch(error){get('status').textContent=error.message;return null;}
}
