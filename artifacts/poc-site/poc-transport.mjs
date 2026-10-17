// Same UI uses live jobs when the PoC API exists, otherwise an explicit frozen catalog.
import { loadScene, plan, gpxUrl } from './client.mjs';
export function createPocTransport(fetcher = fetch) {
  let scene, catalog, mode = 'catalog';
  const pocPath=path=>path.replace(/^\/api\//,'/api/poc/');
  const liveFetch=(path,options)=>fetcher(pocPath(path),options);
  const read = async path => {const r=await fetcher(path);if(!r.ok)throw new Error(`Kunde inte läsa PoC-underlaget (${r.status})`);return r.json();};
  return {
    async loadScene() {
      try {
        const live=await loadScene((path,options)=>liveFetch(path,{...options,signal:AbortSignal.timeout(15000)}),'vinga-poc');
        if(live.profile==='vinga-poc' && live.boat_profiles && live.weather_provenance?.motion_frame){scene=live;mode='live';return scene;}
      } catch { /* The static catalog is clearly identified, never a simulated API result. */ }
      scene=await read('scene.json');catalog=await read('catalog.json');return {...scene,static_catalog:true};
    },
    async plan(payload, options) {
      if(mode==='live')return plan(payload,{...options,fetcher:liveFetch});
      if(payload.profile!=='vinga-poc'||!['baseline',undefined].includes(payload.scenario))throw new Error('Detta PoC använder endast den frysta verkliga dataprofilen.');
      const match=p=>scene.places.find(x=>Math.abs(x.latitude-p.latitude)<1e-8 && Math.abs(x.longitude-p.longitude)<1e-8);
      const a=match(payload.start), b=match(payload.target);
      if(!a||!b||a.id===b.id)throw new Error('Välj två olika markerade punkter i det publicerade urvalet.');
      if(payload.boat_profile!=='constant-5kn'||payload.margin_m!==10||payload.candidate_limit!==4)throw new Error('Detta val ingår inte i det förberäknade PoC-underlaget.');
      const preset=scene.weather_presets.find(p=>p.max_wind_m_s===payload.max_wind_m_s && p.max_wave_height_m===payload.max_wave_height_m);
      const offsets=payload.departure_offsets_seconds;
      if(!preset||!offsets.length||new Set(offsets).size!==offsets.length||offsets.some(o=>!scene.departure_options.some(d=>d.offset_seconds===o)))throw new Error('Valda gränser eller tider finns inte i det verifierade urvalet.');
      const key=`${a.id}${b.id}-${preset.id}`;
      const entry=catalog.cases[key];if(!entry)throw new Error('Saknat beräkningsunderlag. Inga värden fylls i.');
      const data=await read(entry.file);const allowed=new Set(scene.departure_options.filter(d=>offsets.includes(d.offset_seconds)).map(d=>d.time));
      const alternatives=data.alternatives.filter(r=>allowed.has(r.departure_time));const ids=new Set(alternatives.map(r=>r.id));
      const comparisonKey=offsets.length===scene.departure_options.length?'all':offsets.length===1?String(offsets[0]):null;
      if(comparisonKey===null)throw new Error('Välj en avgång eller alla fyra.');
      return {id:key,result:{...data,alternatives,routes:{...data.routes,features:data.routes.features.filter(f=>ids.has(f.properties.id))},alternative_comparison:data.comparisons[comparisonKey],search_budget:{...data.search_budget,departure_offsets_seconds:offsets,evaluation_limit:offsets.length*4}}};
    },
    gpxUrl(job, route) {return mode==='live'?pocPath(gpxUrl(job,route)):`gpx/${encodeURIComponent(job)}-${encodeURIComponent(route)}.gpx`;}
  };
}
