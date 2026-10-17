// Form/results orchestration. Calculations stay on the application side.
import { loadScene, plan, gpxUrl } from './client.mjs';
const labels = { weather_limit: 'Konstaterat överskridande', weather_unverified: 'Otillräckligt bevis', data_unavailable: 'Otillräckliga data', blocked: 'Hinder blockerar', infeasible: 'Ingen tillåten färd i båtmodellen', limit_reached: 'Beräkningsgräns nådd' };
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
  let selected = 'start'; let generation = 0; let abort;
  try {
    const profile = document.documentElement.dataset.profile || 'vinga';
    const scene = await transport.loadScene(undefined, profile);
    const regional = profile === 'vinga' || profile === 'vinga-native';
    if (scene.departure && byId('search-budget')) {
      const base = Date.parse(scene.departure);
      for (const option of byId('search-budget').options) {
        const [count, offsets] = option.value.split(':');
        option.textContent = `${count} kandidater · ${offsets.split(',').map(o => new Date(base + Number(o) * 1000).toISOString().slice(11, 16)).join(', ')} UTC`;
      }
    }
    if (byId('search-budget-label')) byId('search-budget-label').hidden = !regional;
    const scenarioLabel = byId('scenario-label'); if (scenarioLabel) scenarioLabel.hidden = regional;
    if (byId('assumptions')) byId('assumptions').textContent = scene.weather_provenance ? 'Historiska verkliga data. Metadata kvalificering: antagen.\n' + Object.values(scene.weather_provenance.assumptions).join('\n\n') : 'Syntetiskt referensfall för tester.';
    if (scene.weather_limits) { if (byId('wind-limit')) byId('wind-limit').value = scene.weather_limits.max_wind_m_s; if (byId('wave-limit')) byId('wave-limit').value = scene.weather_limits.max_wave_height_m; }
    if (scene.default_margin_m !== undefined) byId('margin').value = scene.default_margin_m;
    setPoint('start', { longitude: scene.start[0], latitude: scene.start[1] });
    setPoint('target', { longitude: scene.target[0], latitude: scene.target[1] });
    const view = mapFactory(byId('map'), scene, point => {
      setPoint(selected, point); invalidate();
      status.textContent = `${selected === 'start' ? 'Start' : 'Mål'} valt. Beräkna igen för aktuell rutt.`;
      selected = selected === 'start' ? 'target' : 'start';
    });
    function previewObstacles() {
      const margin = Number(byId('margin').value);
      if (!Number.isFinite(margin) || margin < 0 || margin > 10) return scene.obstacles;
      return { ...scene.obstacles, features: scene.obstacles.features.map(feature => ({ ...feature, properties: { ...feature.properties, margin_m: margin } })) };
    }
    function invalidate() {
      generation++; abort?.abort(); results.replaceChildren(); if (byId('comparison')) byId('comparison').textContent = ''; byId('provenance').textContent = '';
      view.show({ routes: { features: [] }, obstacles: previewObstacles() });
      view.endpoints(getPoint('start'), getPoint('target')); byId('calculate').disabled = false;
    }
    view.endpoints(getPoint('start'), getPoint('target'));
    view.show({ routes: { features: [] }, obstacles: previewObstacles() });
    const background = byId('background');
    if (background && scene.profile !== 'synthetic') background.addEventListener('click', () => { view.background(); background.disabled = true; }, { once: true });
    for (const name of ['start', 'target']) byId(`choose-${name}`).addEventListener('click', () => { selected = name; status.textContent = `Klicka för att välja ${name === 'start' ? 'start' : 'mål'}.`; });
    byId('plan-form').addEventListener('input', invalidate);
    byId('plan-form').addEventListener('submit', async event => {
      event.preventDefault(); invalidate(); const current = generation; abort = new AbortController();
      byId('calculate').disabled = true; status.textContent = 'Beräknar i separat process…';
      try {
        const [candidateChoice, departureChoice] = (byId('search-budget')?.value || '2:0,600').split(':');
        const departureOffsets = regional ? departureChoice.split(',').map(Number) : [0, 600];
        const response = await transport.plan({ profile, start: getPoint('start'), target: getPoint('target'), margin_m: Number(byId('margin').value), scenario: regional ? 'baseline' : byId('scenario').value, ...(regional ? { candidate_limit: Number(candidateChoice), max_wind_m_s: Number(byId('wind-limit').value), max_wave_height_m: Number(byId('wave-limit').value) } : {}), departure_offsets_seconds: departureOffsets }, { signal: abort.signal });
        if (current !== generation) return;
        const result = response.result; view.show(result);
        const summary = result.geometry_search;
        const comparison = result.alternative_comparison;
        if (comparison && byId('comparison')) {
          const describe = id => { const r = result.alternatives.find(r => r.id === id); return r ? `${r.candidate} vid ${r.departure_time.slice(11, 16)} UTC` : 'inget genomfört alternativ'; };
          byId('comparison').textContent = `Kortast restid över undersökta avgångar: ${describe(comparison.fastest_id)}. Lägst komfortexponering: ${describe(comparison.comfortable_id)}. ${comparison.same_winner === true ? 'Samma alternativ vinner båda kriterierna.' : comparison.same_winner === false ? 'Olika alternativ vinner kriterierna.' : 'Ingen vinnare kan utses.'} Komfortvalet tillåter högst ${comparison.max_comfort_extra_seconds} s extra restid. Ingen global optimalitet.`;
        }
        status.textContent = summary.candidates.length ? `${result.alternatives.length} undersökta rutt-/avgångsalternativ. ${summary.truncated ? 'Begränsad sökning: ' + summary.limit_reason : 'Grafen uttömd; ingen global optimalitet.'}` : 'Ingen genererad kandidat; det bevisar inte att andra möjliga rutter saknas.';
        byId('provenance').textContent = JSON.stringify({ projection: result.projection, search: summary, input_sha256: result.input_sha256, dataset: result.planning?.manifest.dataset_id, version: result.planning?.manifest.dataset_version, land: result.land, depth: result.depth_status, navigational_safety: result.navigational_safety, boat: result.planning?.manifest.boat.model, assumptions: result.weather_provenance?.assumptions, qualification: result.result_qualification, limits: result.selected_weather_limits, notice: result.notice }, null, 2);
        for (const route of result.alternatives) {
          const card = document.createElement('article'); card.className = `route ${category(route)}`;
          const heading = document.createElement('h3'); heading.textContent = `${route.candidate} · avgång ${route.departure_time}`; card.append(heading);
          const detail = document.createElement('p');
          detail.textContent = `${category(route) === 'verified' ? 'Verifierade modellgränser' : category(route) === 'assumed' ? 'Beräknad med antaganden; modellgränser uppfyllda' : labels[route.status] || 'Inte verifierad'}. Restid: ${route.travel_seconds === null ? '—' : route.travel_seconds.toFixed(2) + ' s'}. Ankomst: ${route.arrival_time || '—'}. Komfortexponering (ej validerad): ${route.comfort_exposure === null ? '—' : route.comfort_exposure.toFixed(2)}. ${route.fastest ? 'Snabbast vid denna avgång. ' : ''}${route.comfortable ? 'Bekvämast vid denna avgång. ' : ''}${route.reason || ''}`;
          card.append(detail);
          const show = document.createElement('button'); show.type = 'button'; show.textContent = 'Visa på kartan';
          show.addEventListener('click', () => { view.show(result, route.id); for (const child of results.children) child.classList.remove('picked'); card.classList.add('picked'); }); card.append(show);
          if (['verified', 'assumed'].includes(category(route))) { const link = document.createElement('a'); link.href = gpxUrl(response.id, route.id); link.textContent = 'Hämta planerad GPX'; link.download = 'seaparser-plan.gpx'; card.append(link); }
          results.append(card);
        }
      } catch (error) { if (current === generation) status.textContent = error.message; }
      finally { if (current === generation) byId('calculate').disabled = false; }
    });
    status.textContent = `${scene.notice} Klicka för start, därefter mål, och beräkna.`;
    return view;
  } catch (error) { status.textContent = `Kan inte starta: ${error.message}. API:t måste köras lokalt.`; }
}
