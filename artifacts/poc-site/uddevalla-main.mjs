// Regional source preflight in the same PoC. Never substitutes for route planning.
import {createMap} from './map-component.mjs';

export function missingCell(product,point) {
  const find=(axis,value)=>{if(!Number.isFinite(value)||value<axis[0]||value>axis.at(-1))return -1;let i=0;while(i<axis.length-2&&axis[i+1]<=value)i++;return i;};
  const i=find(product.longitude,point.longitude),j=find(product.latitude,point.latitude);
  if(i<0||j<0)return 'outside';
  return [0,1].some(y=>[0,1].some(x=>!product.node_valid_all_times[j+y][i+x]))?'missing':'present';
}

export async function mountRegional(document,L,fetcher=fetch,mapFactory=createMap) {
  const get=id=>document.getElementById(id),status=get('status');
  try {
    const response=await fetcher('vinga-uddevalla.json');if(!response.ok)throw new Error('Det regionala frysta underlaget kunde inte läsas');
    const data=await response.json();if(data.schema!==1||data.route_status!=='blocked_at_data_preflight'||data.routing_performed||data.gpx_available)throw new Error('Avvikande regional förkontroll');
    get('regional-summary').hidden=false;get('planning-title').textContent='Vinga–Uddevalla';
    document.querySelector('.snapshot').textContent='Frysta prognoser · 18–19 oktober 2026';
    get('mode-notice').textContent='Verkliga regionala prognosdata. Ruttberäkning stoppas före sökning när nödvändigt stöd saknas. Kartpunkter kan väljas fritt för kontroll av datatäckning.';
    document.querySelector('.map-heading span').textContent='Vinga–Uddevalla · uttagsområde och dataluckor';
    document.querySelector('.map-note').textContent='Ramen visar uttaget, inte godkänd routing. Fryst OSM-kustunderlag visas med Visa beräkningsunderlag och är förenklat enbart för visning. Baskartans kustlinjer påverkas inte. OSM-kartbakgrund är inget officiellt sjökort; djup och landfullständighet är okända.';
    document.querySelector('.legend').textContent='Gråblå streckade konturer: valbart beräkningsunderlag · rött/orange: saknade marina interpolationshörn nära Uddevalla. Inga linjer visas som beräknade rutter.';
    const [w,s,e,n]=data.bbox,ring=[[w,s],[e,s],[e,n],[w,n],[w,s]],empty={type:'FeatureCollection',features:[]};
    const scene={profile:'vinga-uddevalla',map_min_zoom:7,coverage:{type:'FeatureCollection',features:[{type:'Feature',properties:{kind:'source_extract_extent'},geometry:{type:'Polygon',coordinates:[ring]}}]},obstacles:empty,land_display:data.coastline_display};
    let selected='start',view;
    const setPoint=(name,p)=>{get(name+'-lat').value=p.latitude;get(name+'-lon').value=p.longitude;};
    const point=name=>({latitude:Number(get(name+'-lat').value),longitude:Number(get(name+'-lon').value)});
    const mark=()=>view.endpoints(point('start'),point('target'));
    function check() {
      const points=[point('start'),point('target')];
      const issues=[];
      for(let k=0;k<points.length;k++)for(const product of ['waves','current']){
        const support=missingCell(data.products[product],points[k]);
        if(support!=='present')issues.push(`${k===0?'Start':'Mål'}: ${product==='waves'?'vågor':'ström'} ${support==='outside'?'utanför källans native-grid':'saknar nödvändiga interpolationshörn under perioden'}`);
      }
      status.textContent=issues.length?issues.join('. ')+'. Ingen ruttberäkning eller GPX.':'Marina gridhörn finns under perioden. Regional vind-, land-, segment- och källkvalificering är inte genomförd för dessa egna punkter. Ingen rutt eller GPX skapas.';
      get('comparison').textContent='Ingen kvalificerbar ruttjämförelse för detta regionala underlag. Färdsimuleringen har inte startats; restid och komfort är inte beräknade.';
      get('results').replaceChildren();mark();
    }
    for(const name of ['start','target']){
      const select=get(name+'-place');select.replaceChildren();
      for(const [id,p] of Object.entries(data.probes)){const option=document.createElement('option');option.value=id;option.textContent=p.position.label;select.append(option);}
      const custom=document.createElement('option');custom.value='custom';custom.textContent='Egen kartpunkt';custom.disabled=true;select.append(custom);select.value=name;
      select.addEventListener('change',()=>{const p=data.probes[select.value];if(p){setPoint(name,p.position);check();}});
      get('choose-'+name).addEventListener('click',()=>{selected=name;status.textContent='Klicka för att välja '+(name==='start'?'start':'mål')+'.';});
      setPoint(name,data.probes[name].position);
    }
    view=mapFactory(L,get('map'),scene,p=>{setPoint(selected,p);get(selected+'-place').value='custom';check();selected=selected==='start'?'target':'start';});
    view.background();get('background').disabled=true;
    const boat=document.createElement('option');boat.value='constant-5kn';boat.textContent='Konstantfart 5 kn · uppskattad båtmodell';get('boat-profile').replaceChildren(boat);
    const weather=document.createElement('option');weather.textContent='Vind ≤18 m/s · vågor ≤3 m · behålls vid framtida beräkning';get('weather-preset').replaceChildren(weather);
    const departure=get('departure-choice');departure.previousSibling.textContent='Provtid · UTC (inte beräknad avgång)';departure.replaceChildren();
    for(let i=0;i<data.valid_times.length;i++){const option=document.createElement('option');option.value=String(i);option.textContent=new Date(data.valid_times[i]).toISOString().slice(0,16).replace('T',' ')+' UTC';departure.append(option);}
    get('calculate').textContent='Kontrollera datastöd';get('show-all').disabled=true;
    get('plan-form').addEventListener('submit',event=>{event.preventDefault();check();});
    function samples(){
      const i=Number(departure.value),host=get('regional-samples');host.replaceChildren();
      for(const [name,probe] of Object.entries(data.probes)){
        const card=document.createElement('article');card.className='route unknown';const title=document.createElement('h3');title.textContent=name==='start'?'Vinga · fryst provpunkt':'Uddevalla / Byfjorden · fryst provpunkt';card.append(title);
        const wind=probe.wind[i],wave=probe.waves.samples[i],current=probe.current.samples[i];
        const p=document.createElement('p');p.textContent=`Vind ${wind.speed_m_s.toFixed(2)} m/s (verkliga MET-värden). Vågor: ${wave.value?wave.value[0].toFixed(2)+' m Hs · '+wave.value[1].toFixed(2)+' s Tm02':'värde kan inte interpoleras; '+wave.missing_corners+'/4 hörn saknas'}. Ström: ${current.value?Math.hypot(...current.value).toFixed(2)+' m/s':'värde kan inte interpoleras; '+current.missing_corners+'/4 hörn saknas'}.`;card.append(p);host.append(card);
      }
    }
    departure.addEventListener('change',samples);samples();
    const ended=Date.now()>Date.parse(data.valid_times.at(-1));
    get('regional-validity').textContent=`${ended?'Historiskt underlag':'Fryst prognosuttag; inte en löpande uppdaterad prognos'}. Gemensamma giltigheter: ${data.valid_times[0]} – ${data.valid_times.at(-1)} (${data.valid_times.length} timsteg, 30 timmar). Modellreferens MET: ${data.reference_time}; utfärdande och körförenlighet ej verifierade.`;
    get('regional-distance').textContent=`Fågelvägsavstånd ${(data.straight_line_distance_m/1000).toFixed(1)} km. Detta är inte en beräknad eller verifierat farbar rutt. Restid och komfort: ej beräknade. GPX: ej tillgänglig.`;
    get('regional-blocker').textContent='Målet saknar ett av fyra egna gridhörn för både vågor och ström vid samtliga 31 timsteg. Samma problem finns i omgivande Uddevalla-celler. Närmaste gridvärde eller noll får inte ersätta luckan; större sökbudget löser inte detta datastödshinder.';
    get('assumptions').textContent=data.assumptions.join('\n\n');get('provenance').textContent=JSON.stringify({source_sha256:data.source_sha256,land:data.land_inventory,blockers:data.blockers},null,2);
    const explanation=document.querySelector('.explanation');for(const p of explanation.querySelectorAll(':scope > p'))p.hidden=true;
    const gaps=L.layerGroup();
    for(const [product,grid] of Object.entries(data.products)){
      const features=[];
      for(let j=0;j<grid.latitude.length-1;j++)for(let i=0;i<grid.longitude.length-1;i++){
        const x=grid.longitude[i],y=grid.latitude[j];if(x<11.76||x>12.02||y<58.27||y>58.40)continue;
        if([0,1].every(dy=>[0,1].every(dx=>grid.node_valid_all_times[j+dy][i+dx])))continue;
        const x2=grid.longitude[i+1],y2=grid.latitude[j+1];features.push({type:'Feature',properties:{product},geometry:{type:'Polygon',coordinates:[[[x,y],[x2,y],[x2,y2],[x,y2],[x,y]]]}});
      }
      L.geoJSON({type:'FeatureCollection',features},{style:{color:product==='waves'?'#ac2536':'#d47b12',weight:1,fillOpacity:.12}}).addTo(gaps);
    }
    gaps.addTo(view.map);get('show-gaps').addEventListener('change',()=>{if(get('show-gaps').checked)gaps.addTo(view.map);else view.map.removeLayer(gaps);});
    check();return view;
  }catch(error){status.textContent='Regionalt underlag kunde inte visas: '+error.message;}
}
