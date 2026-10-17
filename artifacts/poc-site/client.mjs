// Same-origin HTTP transport, bounded polling. No forecast/tile fetch in the engine.
async function json(response) {
  if (!response.ok) {
    const body=await response.json().catch(()=>null);
    const detail=typeof body?.detail==='string'?body.detail:Array.isArray(body?.detail)?body.detail.map(e=>e.msg?.replace(/^Value error, /,'')).filter(Boolean).join(' '):'';
    throw new Error(detail || `API svarade ${response.status}`);
  }
  return response.json();
}
export async function loadScene(fetcher = fetch, profile = 'vinga') {
  if (!['synthetic', 'vinga', 'vinga-native', 'vinga-poc'].includes(profile)) throw new Error('Okänd region');
  return json(await fetcher('/api/scene?profile=' + profile));
}
export async function plan(payload, { fetcher = fetch, pause = ms => new Promise(resolve => setTimeout(resolve, ms)), signal } = {}) {
  const created = await json(await fetcher('/api/plans', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal }));
  if (!/^[a-f0-9]{32}$/.test(created.id)) throw new Error('Ogiltigt jobb-id');
  for (let index = 0; index < 120; index++) {
    if (signal?.aborted) throw new Error('Avbrutet');
    const state = await json(await fetcher(`/api/plans/${created.id}`, { signal }));
    if (state.status === 'completed') return { id: created.id, result: state.result };
    if (state.status === 'failed') throw new Error(state.reason || 'Beräkningen misslyckades');
    await pause(250);
  }
  throw new Error('Svarstiden överskreds');
}
export function gpxUrl(job, route) { return `/api/plans/${encodeURIComponent(job)}/routes/${encodeURIComponent(route)}/gpx`; }
