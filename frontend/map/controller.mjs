// Form/results orchestration. Calculations stay on the application side.
import { loadScene, plan, gpxUrl } from './client.mjs';
const labels = { weather_limit: 'Konstaterat överskridande', weather_unverified: 'Otillräckligt bevis', data_unavailable: 'Otillräckliga data', blocked: 'Hinder blockerar', infeasible: 'Ingen tillåten färd i båtmodellen', limit_reached: 'Beräkningsgräns nådd' };
export function category(route) {
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
    const scene = await transport.loadScene();
    setPoint('start', { longitude: scene.start[0], latitude: scene.start[1] });
    setPoint('target', { longitude: scene.target[0], latitude: scene.target[1] });
    const view = mapFactory(byId('map'), scene, point => {
      setPoint(selected, point); invalidate();
      status.textContent = `${selected === 'start' ? 'Start' : 'Mål'} valt. Beräkna igen för aktuell rutt.`;
      selected = selected === 'start' ? 'target' : 'start';
    });
    function invalidate() {
      generation++; abort?.abort(); results.replaceChildren(); byId('provenance').textContent = '';
      view.show({ routes: { features: [] }, obstacles: scene.obstacles });
      view.endpoints(getPoint('start'), getPoint('target')); byId('calculate').disabled = false;
    }
    view.endpoints(getPoint('start'), getPoint('target'));
    for (const name of ['start', 'target']) byId(`choose-${name}`).addEventListener('click', () => { selected = name; status.textContent = `Klicka för att välja ${name === 'start' ? 'start' : 'mål'}.`; });
    byId('plan-form').addEventListener('input', invalidate);
    byId('plan-form').addEventListener('submit', async event => {
      event.preventDefault(); invalidate(); const current = generation; abort = new AbortController();
      byId('calculate').disabled = true; status.textContent = 'Beräknar i separat process…';
      try {
        const response = await transport.plan({ start: getPoint('start'), target: getPoint('target'), margin_m: Number(byId('margin').value), scenario: byId('scenario').value, departure_offsets_seconds: [0, 600] }, { signal: abort.signal });
        if (current !== generation) return;
        const result = response.result; view.show(result);
        const summary = result.geometry_search;
        status.textContent = summary.candidates.length ? `${result.alternatives.length} undersökta rutt-/avgångsalternativ. ${summary.truncated ? 'Begränsad sökning: ' + summary.limit_reason : 'Grafen uttömd; ingen global optimalitet.'}` : 'Ingen genererad kandidat; det bevisar inte att andra möjliga rutter saknas.';
        byId('provenance').textContent = JSON.stringify({ projection: result.projection, search: summary, input_sha256: result.input_sha256, dataset: result.planning?.manifest.dataset_id, version: result.planning?.manifest.dataset_version, boat: result.planning?.manifest.boat.model, notice: result.notice }, null, 2);
        for (const route of result.alternatives) {
          const card = document.createElement('article'); card.className = `route ${category(route)}`;
          const heading = document.createElement('h3'); heading.textContent = `${route.candidate} · avgång ${route.departure_time}`; card.append(heading);
          const detail = document.createElement('p');
          detail.textContent = `${category(route) === 'verified' ? 'Verifierade modellgränser' : labels[route.status] || 'Inte verifierad'}. Restid: ${route.travel_seconds === null ? '—' : route.travel_seconds.toFixed(2) + ' s'}. Ankomst: ${route.arrival_time || '—'}. Syntetisk komfort: ${route.comfort_exposure === null ? '—' : route.comfort_exposure.toFixed(2)}. ${route.fastest ? 'Snabbast vid denna avgång. ' : ''}${route.comfortable ? 'Bekvämast vid denna avgång. ' : ''}${route.reason || ''}`;
          card.append(detail);
          const show = document.createElement('button'); show.type = 'button'; show.textContent = 'Visa på kartan';
          show.addEventListener('click', () => { view.show(result, route.id); for (const child of results.children) child.classList.remove('picked'); card.classList.add('picked'); }); card.append(show);
          if (category(route) === 'verified') { const link = document.createElement('a'); link.href = gpxUrl(response.id, route.id); link.textContent = 'Hämta planerad GPX'; link.download = 'seaparser-plan.gpx'; card.append(link); }
          results.append(card);
        }
      } catch (error) { if (current === generation) status.textContent = error.message; }
      finally { if (current === generation) byId('calculate').disabled = false; }
    });
    status.textContent = `${scene.notice} Klicka för start, därefter mål, och beräkna.`;
    return view;
  } catch (error) { status.textContent = `Kan inte starta: ${error.message}. API:t måste köras lokalt.`; }
}
