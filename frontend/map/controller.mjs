// Form/results orchestration. Calculations stay on the application side.
import { loadScene, plan, gpxUrl } from './client.mjs';
const labels = { weather_limit: 'Konstaterat överskridande', weather_unverified: 'Otillräckligt bevis', data_unavailable: 'Otillräckliga data', blocked: 'Hinder blockerar', infeasible: 'Ingen tillåten färd i båtmodellen', limit_reached: 'Beräkningsgräns nådd' };
function withinCoverage(point, coverage) {
  const ring=coverage?.features?.[0]?.geometry?.coordinates?.[0];
  if(!ring || !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude))return false;
  const x=point.longitude,y=point.latitude;let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
    const [a,b]=ring[i],[c,d]=ring[j];
    if(Math.abs((x-a)*(d-b)-(y-b)*(c-a))<1e-14 && x>=Math.min(a,c)-1e-12 && x<=Math.max(a,c)+1e-12 && y>=Math.min(b,d)-1e-12 && y<=Math.max(b,d)+1e-12)return true;
    if((b>y)!==(d>y) && x<(c-a)*(y-b)/(d-b)+a)inside=!inside;
  }
  return inside;
}
export function category(route) {
  if (route.qualification === 'conditional_on_assumptions' && route.status === 'arrived' && route.weather_segment_status === 'verified' && route.arrival_weather_status === 'passed_at_arrival') return 'assumed';
  if (route.status === 'arrived' && route.weather_segment_status === 'verified' && route.arrival_weather_status === 'passed_at_arrival') return 'verified';
  return route.status === 'weather_limit' ? 'exceeded' : 'unknown';
}
export async function mount(document, mapFactory, transport = { loadScene, plan }) {
  const byId = id => document.getElementById(id);
  const status = byId('status'); const results = byId('results');
  const setPoint = (name, point) => { byId(`${name}-lat`).value = point.latitude.toFixed(10); byId(`${name}-lon`).value = point.longitude.toFixed(10); };
  const getPoint = name => ({ latitude: Number(byId(`${name}-lat`).value), longitude: Number(byId(`${name}-lon`).value) });
  let selected = 'start'; let generation = 0; let abort; let lastResult;
  try {
    const profile = document.documentElement.dataset.profile || 'vinga';
    const scene = await transport.loadScene(undefined, profile);
    const regional = profile === 'vinga' || profile === 'vinga-native' || profile === 'vinga-poc';
    if (scene.departure && byId('search-budget')) {
      const base = Date.parse(scene.departure);
      for (const option of byId('search-budget').options) {
        const [count, offsets] = option.value.split(':');
        option.textContent = `${count} kandidater · ${offsets.split(',').map(o => new Date(base + Number(o) * 1000).toISOString().slice(11, 16)).join(', ')} UTC`;
      }
    }
    if (byId('search-budget-label')) byId('search-budget-label').hidden = !regional || profile==='vinga-poc';
    const scenarioLabel = byId('scenario-label'); if (scenarioLabel) scenarioLabel.hidden = regional;
    if (byId('assumptions')) {
      const provenance=scene.weather_provenance;
      const dates=(provenance?.verified?.marine_metadata||[]).map(m=>`${m.product==='waves'?'Vågor':'Ström'}: giltigt ${m.valid_from} – ${m.valid_until}. Hämtat ${m.retrieved_at}. Enheter: ${m.units.join(', ')}.`);
      byId('assumptions').textContent = provenance ? `Historiska verkliga data. Metadata kvalificering: antagen.\nPlaneringsdatum: ${scene.planning_time}. Antaget utfärdande: ${provenance.assumed_issued_at}. Källutfärdande: ej verifierat.\nMET modellreferens: ${provenance.verified?.wind_model_reference_time||'saknas'} (inte bevis på utfärdande).\n${dates.join('\n')}\nMET frysta giltigheter: ${(scene.wind_sample_validities||[]).join(', ')||'se källspårbarhet'}.\n\n` + Object.values(provenance.assumptions).join('\n\n') : 'Syntetiskt referensfall för tester.';
    }
    if (scene.weather_limits) { if (byId('wind-limit')) byId('wind-limit').value = scene.weather_limits.max_wind_m_s; if (byId('wave-limit')) byId('wave-limit').value = scene.weather_limits.max_wave_height_m; }
    if (scene.default_margin_m !== undefined) byId('margin').value = scene.default_margin_m;
    if(profile==='vinga-poc'&&!scene.static_catalog)byId('calculate').textContent='Beräkna ruttalternativ';
    if (scene.static_catalog) {
      byId('calculate').textContent = 'Visa ruttalternativ';
      for (const name of ['start','target']) for (const axis of ['lat','lon']) byId(`${name}-${axis}`).readOnly = true;
    }
    for (const name of ['start','target']) if (byId(`${name}-place`) && scene.places) {
      const select=byId(`${name}-place`);
      for (const p of scene.places) { const option=document.createElement('option'); option.value=p.id; option.textContent=p.label; select.append(option); }
      select.value=scene.places[name==='start'?0:1].id;
      select.addEventListener('change',()=>{const place=scene.places.find(p=>p.id===select.value);if(place){setPoint(name,place); invalidate();}});
    }
    if (byId('boat-profile')) for (const boat of scene.boat_profiles || []) {const o=document.createElement('option');o.value=boat.id;o.textContent=boat.label;byId('boat-profile').append(o);}
    if (byId('departure-choice')) {
      for (const d of scene.departure_options || []) {const o=document.createElement('option');o.value=String(d.offset_seconds);o.textContent=d.time.slice(11,16)+' UTC';byId('departure-choice').append(o);}
      if(profile==='vinga-poc'&&!scene.static_catalog)byId('departure-choice').value='0';
    }
    if (byId('weather-preset')) {
      for (const p of scene.weather_presets || []) {const o=document.createElement('option');o.value=p.id;o.textContent=p.label;byId('weather-preset').append(o);}
      byId('weather-preset').addEventListener('change',()=>{const p=scene.weather_presets.find(p=>p.id===byId('weather-preset').value);byId('wind-limit').value=p.max_wind_m_s;byId('wave-limit').value=p.max_wave_height_m;invalidate();});
    }
    if (byId('mode-notice')) byId('mode-notice').textContent=scene.static_catalog ? 'Begränsat PoC: välj tre markerade punkter och fyra avgångar. Rutterna är förberäknade från verkliga frysta data. Fria ruttpunkter ingår ännu inte i det publicerade urvalet.' : 'Liveberäkning: klicka fritt för start och mål inom det markerade prognosområdet (900 m). Historiska frysta prognoser; land och vädergränser kontrolleras.';
    setPoint('start', { longitude: scene.start[0], latitude: scene.start[1] });
    setPoint('target', { longitude: scene.target[0], latitude: scene.target[1] });
    function syncPlace(name,point) {
      const select=byId(`${name}-place`);if(!select||!scene.places)return;
      const place=scene.places.find(p=>Math.abs(p.latitude-point.latitude)<1e-8&&Math.abs(p.longitude-point.longitude)<1e-8);
      if(place){select.value=place.id;return;}
      if(![...select.options].some(o=>o.value==='custom')){const option=document.createElement('option');option.value='custom';option.textContent='Egen kartpunkt';option.disabled=true;select.append(option);}
      select.value='custom';
    }
    const view = mapFactory(byId('map'), scene, point => {
      if(profile==='vinga-poc'&&!scene.static_catalog&&!withinCoverage(point,scene.coverage)){
        invalidate();status.textContent='Punkten ligger utanför det markerade prognosområdet. Välj en punkt innanför täckningsgränsen (900 m).';return;
      }
      if(profile==='vinga-poc'&&!scene.static_catalog)byId('calculate').textContent='Beräkna ruttalternativ';
    if (scene.static_catalog) {
        const place=scene.places.find(p=>Math.hypot((p.latitude-point.latitude)*111000,(p.longitude-point.longitude)*60000)<40);
        if (!place) {status.textContent='Välj en av de markerade punkterna i detta begränsade PoC.';return;}
        point=place;byId(`${selected}-place`).value=place.id;
      }
      setPoint(selected, point); syncPlace(selected,point); invalidate();
      status.textContent = `${selected === 'start' ? 'Start' : 'Mål'} valt. Beräkna igen för aktuell rutt.`;
      selected = selected === 'start' ? 'target' : 'start';
    });
    function previewObstacles() {
      const margin = Number(byId('margin').value);
      if (!Number.isFinite(margin) || margin < 0 || margin > 10) return scene.obstacles;
      return { ...scene.obstacles, features: scene.obstacles.features.map(feature => ({ ...feature, properties: { ...feature.properties, margin_m: margin } })) };
    }
    function invalidate() {
      generation++; abort?.abort(); lastResult=null; if(byId('show-all'))byId('show-all').disabled=true; results.replaceChildren(); if (byId('comparison')) byId('comparison').textContent = ''; byId('provenance').textContent = '';
      view.show({ routes: { features: [] }, obstacles: previewObstacles() });
      view.endpoints(getPoint('start'), getPoint('target')); byId('calculate').disabled = false;
    }
    view.endpoints(getPoint('start'), getPoint('target'));
    view.show({ routes: { features: [] }, obstacles: previewObstacles() });
    byId('show-all')?.addEventListener('click',()=>{if(lastResult){view.show(lastResult);for(const child of results.children)child.classList.remove('picked');}});
    const background = byId('background');
    if (background && scene.profile !== 'synthetic') background.addEventListener('click', () => { view.background(); background.disabled = true; }, { once: true });
    for (const name of ['start', 'target']) byId(`choose-${name}`).addEventListener('click', () => { selected = name; status.textContent = `Klicka för att välja ${name === 'start' ? 'start' : 'mål'}.`; });
    byId('plan-form').addEventListener('input', invalidate);
    byId('plan-form').addEventListener('submit', async event => {
      event.preventDefault(); invalidate(); const current = generation; abort = new AbortController();
      byId('calculate').disabled = true; status.textContent = scene.static_catalog ? 'Hämtar undersökta ruttalternativ…' : 'Beräknar rutter…';
      try {
        if(profile==='vinga-poc'&&!scene.static_catalog){
          if(!withinCoverage(getPoint('start'),scene.coverage)||!withinCoverage(getPoint('target'),scene.coverage))throw new Error('Start eller mål ligger utanför det markerade prognosområdet.');
          if(!['all',...scene.departure_options.map(d=>String(d.offset_seconds))].includes(byId('departure-choice').value))throw new Error('Avgången saknar tillgängliga prognosdata. Välj en av de angivna tiderna.');
        }
        const [candidateChoice, departureChoice] = (byId('search-budget')?.value || '2:0,600').split(':');
        const departureOffsets = byId('departure-choice') ? (byId('departure-choice').value==='all' ? scene.departure_options.map(d=>d.offset_seconds) : [Number(byId('departure-choice').value)]) : regional ? departureChoice.split(',').map(Number) : [0, 600];
        const response = await transport.plan({ profile, start: getPoint('start'), target: getPoint('target'), margin_m: Number(byId('margin').value), scenario: regional ? 'baseline' : byId('scenario').value, ...(regional ? { candidate_limit: profile==='vinga-poc' ? 4 : Number(candidateChoice), ...(profile==='vinga-poc'?{boat_profile:byId('boat-profile').value}:{}), max_wind_m_s: Number(byId('wind-limit').value), max_wave_height_m: Number(byId('wave-limit').value) } : {}), departure_offsets_seconds: departureOffsets }, { signal: abort.signal });
        if (current !== generation) return;
        const result = response.result; lastResult=result; if(byId('show-all'))byId('show-all').disabled=false; view.show(result,profile==='vinga-poc'?result.alternative_comparison.fastest_id:null);
        const summary = result.geometry_search;
        const comparison = result.alternative_comparison;
        if (comparison && byId('comparison')) {
          const describe = id => { const r = result.alternatives.find(r => r.id === id); return r ? `${profile==='vinga-poc'?'Alternativ '+(Number(r.candidate.split('-').at(-1))+1):r.candidate} vid ${r.departure_time.slice(11, 16)} UTC` : 'inget genomfört alternativ'; };
          byId('comparison').textContent = `Kortast restid över undersökta avgångar: ${describe(comparison.fastest_id)}. Lägst komfortexponering: ${describe(comparison.comfortable_id)}. ${comparison.same_winner === true ? 'Samma alternativ vinner båda kriterierna.' : comparison.same_winner === false ? 'Olika alternativ vinner kriterierna.' : 'Ingen vinnare kan utses.'} Komfortvalet tillåter högst ${comparison.max_comfort_extra_seconds} s extra restid. Ingen global optimalitet.`;
        }
        status.textContent = summary.candidates.length ? `${result.alternatives.length} undersökta rutt-/avgångsalternativ. ${summary.truncated ? 'Begränsad sökning: ' + summary.limit_reason : 'Grafen uttömd; ingen global optimalitet.'}` : 'Ingen genererad kandidat; det bevisar inte att andra möjliga rutter saknas.';
        if(profile==='vinga-poc') status.textContent = summary.status==='endpoint_blocked' ? 'Start eller mål ligger på land eller inom vald hindermarginal. Flytta punkten till vatten. Ingen GPX-export tillåts.' : !summary.candidates.length ? 'Ingen rutt hittades inom den begränsade sökningen. Prova andra vattenpunkter. Ingen GPX-export tillåts.' : result.alternatives.some(r=>r.status==='arrived') ? `${result.alternatives.length} undersökta alternativ. Välj ett ruttkort för karta och GPX. Endast det angivna urvalet har jämförts.` : 'Inget av de undersökta alternativen klarar valda gränser. Ingen GPX-export tillåts.';
        byId('provenance').textContent = JSON.stringify({ projection: result.projection, search: summary, input_sha256: result.input_sha256, dataset: result.planning?.manifest.dataset_id, version: result.planning?.manifest.dataset_version, land: result.land, depth: result.depth_status, navigational_safety: result.navigational_safety, boat: result.planning?.manifest.boat.model, assumptions: result.weather_provenance?.assumptions, qualification: result.result_qualification, limits: result.selected_weather_limits, notice: result.notice }, null, 2);
        const preferred=r=>r.id===result.alternative_comparison?.fastest_id?0:r.id===result.alternative_comparison?.comfortable_id?1:2;
        const displayRoutes=profile==='vinga-poc'?[...result.alternatives].sort((a,b)=>preferred(a)-preferred(b)):result.alternatives;
        for (const route of displayRoutes) {
          const card = document.createElement('article'); card.className = `route ${category(route)}`;
          if(profile==='vinga-poc' && route.id===result.alternative_comparison.fastest_id)card.classList.add('picked');
          const heading = document.createElement('h3'); heading.textContent = profile==='vinga-poc' ? `Alternativ ${Number(route.candidate.split('-').at(-1))+1} · ${route.departure_time.slice(11,16)} UTC` : `${route.candidate} · avgång ${route.departure_time}`; card.append(heading);
          if(profile==='vinga-poc')for(const [id,label] of [[result.alternative_comparison.fastest_id,'Snabbast funna'],[result.alternative_comparison.comfortable_id,'Bekvämast funna']])if(route.id===id){const tag=document.createElement('span');tag.className='route-tag';tag.textContent=label;card.append(tag);}
          const detail = document.createElement('p');
          detail.textContent = `${category(route) === 'verified' ? 'Verifierade modellgränser' : category(route) === 'assumed' ? 'Beräknad med antaganden; modellgränser uppfyllda' : labels[route.status] || 'Inte verifierad'}. Restid: ${route.travel_seconds === null ? '—' : route.travel_seconds.toFixed(2) + ' s'}. Ankomst: ${route.arrival_time || '—'}. Komfortexponering (ej validerad): ${route.comfort_exposure === null ? '—' : route.comfort_exposure.toFixed(2)}. ${route.fastest ? 'Snabbast vid denna avgång. ' : ''}${route.comfortable ? 'Bekvämast vid denna avgång. ' : ''}${route.reason || ''}`;
          if (profile==='vinga-poc') detail.textContent = `${category(route)==='assumed'?'Beräknad med angivna antaganden':labels[route.status]||'Inte verifierad'}. Restid: ${route.travel_seconds==null?'—':(route.travel_seconds/60).toFixed(1)+' min'}. Ankomst ${route.arrival_time?.slice(11,19)||'—'} UTC. ${route.fastest?'Snabbast vid avgången. ':''}${route.comfortable?'Bekvämast vid avgången. ':''}${route.reason||''}`;
          if (route.distance_m != null) detail.textContent += ` Sträcka${route.status==='arrived'?'':' till avbrott'}: ${(route.distance_m/1852).toFixed(2)} M (${Math.round(route.distance_m)} m).`;
          card.append(detail);
          if(route.weather_summary){const p=document.createElement('p');const fmt=(v,u)=>v?.min==null?'saknas':`${v.min.toFixed(1)}–${v.max.toFixed(1)} ${u}${v.missing_samples?' · dataluckor':''}`;p.textContent=`Längs modellrutten · Vind ${fmt(route.weather_summary.wind_m_s,'m/s')} · Vågor ${fmt(route.weather_summary.wave_height_m,'m')} · Ström ${fmt(route.weather_summary.current_m_s,'m/s')}`;card.append(p);}
          const show = document.createElement('button'); show.type = 'button'; show.textContent = 'Visa på kartan';
          show.addEventListener('click', () => { view.show(result, route.id); for (const child of results.children) child.classList.remove('picked'); card.classList.add('picked'); }); card.append(show);
          if (['verified', 'assumed'].includes(category(route))) { const link = document.createElement('a'); link.href = transport.gpxUrl ? transport.gpxUrl(response.id,route.id) : gpxUrl(response.id, route.id); link.textContent = 'Hämta planerad GPX'; link.download = 'seaparser-plan.gpx'; card.append(link); }
          results.append(card);
        }
      } catch (error) { if (current === generation) status.textContent = error.message; }
      finally { if (current === generation) byId('calculate').disabled = false; }
    });
    status.textContent = `${scene.notice} Klicka för start, därefter mål, och beräkna.`;
    return view;
  } catch (error) { status.textContent = `Kan inte starta: ${error.message}. Kontrollera sidans dataresurser och API-anslutning.`; }
}
