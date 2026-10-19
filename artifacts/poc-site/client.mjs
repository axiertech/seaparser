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
async function runPlan(path,payload,{fetcher=fetch,pause=ms=>new Promise(resolve=>setTimeout(resolve,ms)),signal,onStatus=()=>{},interval=250}={}) {
  const created=await json(await fetcher(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(25000)}));
  if(!/^[a-f0-9]{32}$/.test(created.id))throw new Error('Ogiltigt jobb-id');
  const seconds=created.poll_timeout_seconds??30;
  let terminal=false;
  try {
    if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<=0||seconds>3600)throw new Error('Ogiltig beräkningstidsbudget');
    onStatus({id:created.id,status:'queued',elapsed_seconds:0,server_timeout_seconds:created.server_timeout_seconds,poll_timeout_seconds:seconds});
    const deadline=Date.now()+seconds*1000;
    for(let index=0;index<Math.ceil(seconds*1000/interval)&&Date.now()<deadline;index++){
      if(signal?.aborted)throw new Error('Avbrutet');
      const state=await json(await fetcher(`${path}/${created.id}`,{signal}));onStatus(state);
      if(state.status==='completed'){terminal=true;return {id:created.id,result:state.result};}
      if(state.status==='failed'){terminal=true;throw new Error(state.reason||'Beräkningen misslyckades');}
      await pause(interval);
    }
    throw new Error('Svarstiden överskreds');
  } finally {
    if(!terminal){
      try {const stopped=await json(await fetcher(`${path}/${created.id}`,{method:'DELETE',signal:AbortSignal.timeout(10000),keepalive:true}));if(stopped.active!==false)throw new Error('Saknat kvitto på avslutat jobb');}
      catch(cause){const error=new Error('Kunde inte verifiera att det avbrutna jobbet städats; starta inte nästa beräkning.',{cause});error.cleanupFailed=true;throw error;}
    }
  }
}

export function plan(payload,options){return runPlan('/api/plans',payload,options);}
export function planCoastal(payload,{fetcher=fetch,...options}={}){
  const bounded=async(path,request={})=>{
    const timeout=AbortSignal.timeout(25000),signal=request.signal?AbortSignal.any([request.signal,timeout]):timeout;
    const response=await fetcher(path,{...request,signal});
    if(response.status===404)throw new Error(request.method==='POST'?'Det regionala API:t är ännu inte aktiverat. Ingen beräkning eller ny GPX har skapats.':'Jobbet saknas eller har gått ut. Beräkna på nytt.');
    return response;
  };
  return runPlan('/api/poc/coastal/plans',payload,{interval:1000,...options,fetcher:bounded});
}
export function gpxUrl(job, route) { return `/api/plans/${encodeURIComponent(job)}/routes/${encodeURIComponent(route)}/gpx`; }
