// Presentation of an explicitly selected, actually simulated coastal snapshot.
export function attachCoastalView(document,view,fetcher=fetch) {
 const get=id=>document.getElementById(id),empty={type:'FeatureCollection',features:[]};
 const button=document.createElement('button');button.type='button';button.id='show-coastal-voyage';button.className='primary';
 button.textContent='Visa simulerad färd · 18 okt 09:00 UTC';get('regional-summary').prepend(button);
 const originals=new Map(['mode-notice','regional-distance','regional-blocker','assumptions','provenance'].map(id=>[get(id),get(id).textContent]));
 get('regional-summary').querySelector('h2').textContent='Verkliga prognosprov utan reservdata';
 get('departure-choice').previousSibling.textContent='Avgång / provtid · UTC';
 get('weather-preset').options[0].textContent='Vind ≤18 m/s · vågor ≤3 m · valda modellgränser';
 const legend=document.querySelector('.legend'),oldLegend=legend.textContent;
 let revision=0,shown=false;
 function reset(){revision++;if(!shown)return;shown=false;view.show({obstacles:empty,routes:empty});get('results').replaceChildren();
  for(const [node,text] of originals)node.textContent=text;legend.textContent=oldLegend;
 }
 document.addEventListener('seaparser:regional-change',reset);
 for(const id of ['start-lat','start-lon','target-lat','target-lon'])get(id).addEventListener('input',()=>{
  reset();get('comparison').textContent='Egna punkter: ingen sparad färd gäller. Kontrollera datastöd.';get('status').textContent='Valen har ändrats. Ingen regional färdsimulering eller GPX för dessa egna punkter.';
 });
 button.addEventListener('click',async()=>{
  for(const name of ['start','target']){get(name+'-place').value=name;get(name+'-place').dispatchEvent(new document.defaultView.Event('change'));}
  get('departure-choice').value='0';get('departure-choice').dispatchEvent(new document.defaultView.Event('change'));
  const expected=revision;button.disabled=true;
  try{
   const response=await fetcher('coastal-voyage.json');if(!response.ok)throw new Error('Den simulerade färden kunde inte läsas');
   const data=await response.json();if(revision!==expected)return;
   if(data.profile!=='vinga-uddevalla'||data.result_qualification!=='estimated_high_uncertainty'||data.weather_limits_verified!==false||!data.routes.length)throw new Error('Saknad uttrycklig uppskattningsstatus');
   const evidence=data.reserve_evidence,route=data.routes[0];
   if(route.status!=='arrived'||route.arrival_weather_status!=='passed_at_arrival'||route.weather_limits_verified!==false)throw new Error('Färden har inte nått godkänd modellankomst');
   shown=true;get('mode-notice').textContent='Sparad, faktiskt simulerad färd med verklig vind, vågor och ström samt uttryckliga landmedvetna reservdata. HÖG OSÄKERHET. Vädergränser är inte verifierat klarade. Egna punkter kräver ny beräkning och får inte denna färd.';
   get('regional-blocker').textContent='De strikta proven nedan saknar fortsatt egna gridhörn. Den visade färden använder i stället uttryckliga reservpolicyer för vågor/ström med kontrollerad vattenförbindelse, källposition/tid och avstånd. Hög osäkerhet; gränser ej verifierade.';
   legend.textContent='Orange streckad linje: uppskattad modellfärd · hög osäkerhet längs hela rutten. Vädergränser ej verifierade. Beräkningsunderlag växlas separat.';
   const features=data.routes.map(r=>({type:'Feature',properties:{id:r.id,candidate:r.id,kind:'accepted',qualification:'estimated_high_uncertainty',status:'HÖG OSÄKERHET · vädergränser ej verifierade'},geometry:{type:'LineString',coordinates:r.path}}));
   view.show({obstacles:empty,routes:{type:'FeatureCollection',features}});
   get('comparison').textContent=`${data.routes.length} faktiskt simulerat alternativ. ${data.routes.length===1?'Jämförelse mellan olika vägval återstår.':''} Uppskattningar med hög osäkerhet; inga verifierat klarade vädergränser.`;
   const host=get('results');host.replaceChildren();
   for(const r of data.routes){
    const card=document.createElement('article');card.className='route unknown';
    const title=document.createElement('h3');title.textContent='Vinga–Uddevalla · HÖG OSÄKERHET';card.append(title);
    const p=document.createElement('p');p.textContent=`${(r.distance_m/1000).toFixed(2)} km · ${Math.floor(r.travel_seconds/3600)} h ${Math.round(r.travel_seconds%3600/60)} min · ankomst ${new Date(r.arrival_time).toISOString().slice(11,19)} UTC. Komfortexponering ${r.comfort_exposure.toFixed(2)} (syntetiskt, ej validerat mått).`;card.append(p);
    const weather=document.createElement('p');weather.textContent=['wind_m_s','wave_height_m','current_m_s'].map((key,i)=>{const v=r.weather_summary[key];return `${['Vind','Hs','Ström'][i]} ${v.min.toFixed(3)}–${v.max.toFixed(3)} ${i===1?'m':'m/s'} (${v.sample_count} mittpunkter, ${v.missing_samples} saknade)`;}).join(' · ');card.append(weather);
    const notice=document.createElement('p');notice.textContent='Vädergränser EJ verifierade. Hela landsegment, 10 m modellmarginal och valda gränskontroller behållna; käll-/modellantaganden och reservdata innebär hög osäkerhet.';card.append(notice);
    const link=document.createElement('a');link.href=`gpx/coastal-${encodeURIComponent(r.id)}-estimated.gpx`;link.textContent='GPX · UPPSKATTNING / HÖG OSÄKERHET';link.download='';card.append(link);host.append(card);
   }
   const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Reservkällor och berörda färdsegment';details.append(summary);
   const select=document.createElement('select');select.setAttribute('aria-label','Färdsegment för källspårbarhet');
   evidence.segments.forEach((s,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=`Segment ${i+1} · ben ${s.leg+1} · ${s.samples[0].time}`;select.append(option);});
   const pre=document.createElement('pre');
   const explain=()=>{const segment=evidence.segments[Number(select.value)];pre.textContent=JSON.stringify({...segment,samples:segment.samples.map(s=>({...s,estimates:s.estimate_refs.map(i=>{const r=evidence.records[i];return {...evidence.sources[r.source],...evidence.connections[r.connection],distance_m:r.distance_m,direct_distance_m:r.direct_distance_m,time_offset_seconds:r.time_offset_seconds};})}))},null,2);};
   select.addEventListener('change',explain);details.append(select,pre);explain();host.append(details);
   const download=document.createElement('a');download.href='coastal-voyage.json';download.textContent='Alla segment, källpositioner/tider, vattenförbindelser, avstånd och tidsavvikelser · JSON';download.download='';details.append(download);
   get('regional-distance').textContent=`Simulerad färd ${(route.distance_m/1000).toFixed(2)} km. ${route.segment_count} accepterade modellsegment. Hög osäkerhet; inte verifierad navigerbarhet.`;
   get('assumptions').textContent=JSON.stringify({source_assumptions:data.provenance.source_assumptions,model_assumptions:data.provenance.model_assumptions,reserve_policies:data.provenance.reserve_policies},null,2);
   get('provenance').textContent=JSON.stringify({input_sha256:data.input_sha256,source_metadata:data.provenance.source_metadata,water:data.provenance.water,configuration:data.configuration},null,2);
   get('status').textContent='Visar sparad modellfärd för Vinga–Uddevalla, avgång 18 oktober 09:00 UTC. HÖG OSÄKERHET; vädergränser ej verifierade. Ändrade punkter eller tid tar bort färden och GPX.';
  }catch(error){reset();get('status').textContent=error.message;}finally{button.disabled=false;}
 });
 return {reset,show:()=>button.click()};
}
