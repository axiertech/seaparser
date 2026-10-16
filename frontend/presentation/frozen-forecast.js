'use strict';
(() => {
  const data = JSON.parse(document.getElementById('review-data').textContent);
  if (data.schema !== 1 || data.historical !== true || data.routing_qualified !== false) throw new Error('Historical raw samples required');
  const $ = id => document.getElementById(id);
  let product = data.products[0], fieldKey, timeIndex = 0, nodeIndex = 0;
  const format = value => value === null || value === undefined ? 'Saknat prov' : String(value);
  const date = value => value ? new Date(value).toISOString().replace('T', ' ').replace('.000Z', ' UTC') : 'Okänd – inte verifierad';
  const text = (id, value) => { $(id).textContent = value; };
  const element = (tag, value) => { const e = document.createElement(tag); if (value !== undefined) e.textContent = value; return e; };
  const svgElement = (tag, attrs, value) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) e.setAttribute(k, v); if (value !== undefined) e.textContent = value; return e; };
  const pair = (parent, label, value) => parent.append(element('dt', label), element('dd', value));
  const segment = data.segment_review, wind = data.products.find(p => p.id === 'wind');
  const mathematicalFrame = segment?.segment?.coordinate_frame === 'met-source-sphere-angular-linear-v1' &&
    segment.method === 'met-spherical-lcc-rational-box-v1' ||
    segment?.segment?.coordinate_frame === 'met-source-sphere-aeqd-affine-v1' &&
    segment.method === 'met-source-sphere-aeqd-disk-lcc-v1' &&
    segment.source_local_geometry?.local_to_source_sphere_enclosure_verified === true &&
    segment.source_local_geometry.wgs84_route_binding_verified === false;
  const segmentAvailable = mathematicalFrame && segment.routing_status === 'data_unavailable' && segment.physical_source_support_qualified === false &&
    segment.local_route_geometry_binding_verified === false &&
    Object.keys(wind.source_hashes).length === Object.keys(segment.source_hashes).length &&
    Object.entries(wind.source_hashes).every(([name,hash]) => segment.source_hashes[name] === hash);
  const failureLabels = {
    projected_box_outside_serialized_native_grid: 'Det omslutande området lämnar vindprovets sparade koordinatgränser.',
    segment_outside_nominal_time_support: 'Provsegmentets tidsintervall lämnar de sparade vindtiderna.',
    source_cell_budget_exceeded: 'Kontrollens arbetsgräns nåddes innan ett fullständigt underlag kunde redovisas.',
    missing_or_nonfinite_raw_node: 'Ett nödvändigt sparat värde saknas eller är inte ett ändligt tal.'
  };
  const failureText = () => (segment.inventory_failures ?? []).map(code => failureLabels[code] ?? 'Underlaget kunde inte verifieras som fullständigt.').join(' ');
  const coordinateLabel = token => { const [a,b='1'] = String(token).split('/'); return String(Number(a)/Number(b)); };
  function options(select, entries) { select.replaceChildren(); for (const [value,label] of entries) { const o = element('option', label); o.value = value; select.append(o); } }
  function safeLink(id, url) { const link = $(id); link.removeAttribute('href'); if (typeof url === 'string' && url.startsWith('https://')) link.href = url; }
  function selectProduct(p) {
    product = p; fieldKey = Object.keys(p.fields)[0]; timeIndex = 0; nodeIndex = 0;
    for (const b of $('products').children) b.setAttribute('aria-pressed', String(b.dataset.product === p.id));
    text('product-title', p.label); text('dataset', p.dataset); text('projection', p.projection);
    text('semantics', p.semantics); text('mask-note', p.mask_note); text('attribution', p.attribution);
    safeLink('source-link', p.source_url); safeLink('license-link', p.license_url);
    options($('field'), Object.entries(p.fields).map(([key,f]) => [key, `${f.label} (${f.unit})`]));
    options($('time'), p.times.map((t,i) => [i,date(t)]));
    options($('node'), p.y.flatMap((y,j) => p.x.map((x,i) => [j*p.x.length+i, `Rad ${j+1}, punkt ${i+1} · ${x}, ${y}`])));
    $('timeline').max = p.times.length-1; $('timeline').value = 0;
    text('validity', `Sparat tidsstöd: ${date(p.times[0])} – ${date(p.times.at(-1))}. Endast dessa tidpunkter visas.`);
    $('source-times').replaceChildren();
    pair($('source-times'), 'Modellreferenstid (inte utfärdandetid)', date(p.model_reference_time));
    pair($('source-times'), 'Faktisk utfärdandetid', date(p.issued_at));
    pair($('source-times'), 'Verifierad modellkörning', p.run_identity ?? 'Okänd');
    pair($('source-times'), 'Förenlighet mellan produkterna', 'Inte verifierad');
    pair($('source-times'), 'Separat maskkälla', p.mask_source ?? 'Saknas – ingen annan produkts mask används');
    $('segment-review').hidden = p.id !== 'wind' || !segmentAvailable;
    if (segmentAvailable) {
      const s = segment.segment;
      const places = new Set(segment.raw_nodes.map(n => n.index.slice(1).join(','))).size;
      const instants = new Set(segment.raw_nodes.map(n => n.index[0])).size;
      const local = segment.segment_coordinate_encoding === 'exact rational metres';
      const coordinates = local ? [s.start_east_m,s.start_north_m,s.end_east_m,s.end_north_m] : [s.start_latitude,s.start_longitude,s.end_latitude,s.end_longitude];
      const [a,b,c,d] = coordinates.map(coordinateLabel);
      const supportSummary = segment.raw_inventory_complete ? `Underlag: ${places} platser vid ${instants} sparade tider, sammanlagt ${segment.raw_nodes.length} prov.` : 'Fullständigt sparat stöd saknas.';
      text('segment-summary', `Provbana (${a}, ${b}) till (${c}, ${d}) ${local ? 'meter' : 'grader latitud/longitud på modellens sfär'}. Passage ${date(s.start_time)} – ${date(s.end_time)}. ${supportSummary}`);
      text('segment-outcome', segment.raw_inventory_complete ? 'Råinventeringen är komplett. Giltighet och verklig ruttberäkning är fortfarande inte godkända.' : failureText() + ' Ett överlappande delområde eller delintervall räcker inte; inga stödmarkeringar visas.');
      $('segment-hashes').replaceChildren();
      if (data.segment_source_sha256) pair($('segment-hashes'), 'Provbanans JSON SHA-256', data.segment_source_sha256);
      pair($('segment-hashes'), 'Granskningsrapport SHA-256', segment.report_sha256);
      pair($('segment-hashes'), 'Fryst vindunderlag SHA-256', segment.source_input_sha256);
    }
    $('hashes').replaceChildren(); for (const [name, hash] of Object.entries(p.source_hashes)) pair($('hashes'), name, hash);
    draw();
  }
  function draw() {
    const p = product, f = p.fields[fieldKey], cols = p.x.length;
    const j = Math.floor(nodeIndex/cols), i = nodeIndex%cols;
    const all = f.values.flat(2).filter(Number.isFinite), lo = all.length ? Math.min(...all) : 0, hi = all.length ? Math.max(...all) : 0;
    const color = v => Number.isFinite(v) ? `hsl(${210 - 175 * (hi === lo ? .5 : (v-lo)/(hi-lo))}, 65%, 43%)` : '#ffffff';
    const showSegment = p.id === 'wind' && segmentAvailable && $('segment-toggle').checked;
    const supportComplete = showSegment && segment.raw_inventory_complete === true;
    const supportNodes = new Set(supportComplete ? segment.raw_nodes.filter(n => n.index[0] === timeIndex).map(n => n.index[1]*cols+n.index[2]) : []);
    const box = showSegment ? segment.projected_enclosure_m : null;
    const west = box ? Math.min(p.x[0],Number(box.x[0])) : p.x[0], east = box ? Math.max(p.x.at(-1),Number(box.x[1])) : p.x.at(-1);
    const south = box ? Math.min(p.y[0],Number(box.y[0])) : p.y[0], north = box ? Math.max(p.y.at(-1),Number(box.y[1])) : p.y.at(-1);
    const x = v => 80 + (v-west)/(east-west)*585;
    const y = v => 350 - (v-south)/(north-south)*300;
    const grid = $('grid'); grid.replaceChildren();
    if (showSegment) {
      const [w,e] = box.x.map(Number), [s,n] = box.y.map(Number), shade = supportComplete ? '#704ba0' : '#99530c';
      grid.append(svgElement('rect',{x:x(w),y:y(n),width:x(e)-x(w),height:y(s)-y(n),fill:shade,'fill-opacity':'.08',stroke:shade,'stroke-width':2,'stroke-dasharray':'8 4','data-segment-envelope':'true'}));
      grid.append(svgElement('rect',{x:x(p.x[0]),y:y(p.y.at(-1)),width:x(p.x.at(-1))-x(p.x[0]),height:y(p.y[0])-y(p.y.at(-1)),fill:'none',stroke:'#536b75','stroke-width':2,'data-source-coverage':'true'}));
    }
    grid.append(svgElement('line',{x1:80,y1:350,x2:665,y2:350,class:'grid-axis'}), svgElement('line',{x1:80,y1:50,x2:80,y2:350,class:'grid-axis'}));
    grid.append(svgElement('text',{x:80,y:385},String(west)),svgElement('text',{x:665,y:385,'text-anchor':'end'},String(east)),svgElement('text',{x:80,y:417},p.axis_labels[0]),svgElement('text',{x:12,y:24},p.axis_labels[1]));
    grid.append(svgElement('text',{x:8,y:350},String(south)),svgElement('text',{x:8,y:55},String(north)));
    let missing = 0, excluded = 0, unknownMask = 0;
    p.y.forEach((north,row) => p.x.forEach((east,col) => {
      const value = f.values[timeIndex][row][col], mask = p.mask?.[row][col];
      if (!Number.isFinite(value)) missing++;
      if (p.mask && mask !== 1) { excluded++; if (mask === null) unknownMask++; }
      const index = row*cols+col;
      const c = svgElement('circle',{cx:x(east),cy:y(north),r:index === nodeIndex ? 10 : 7,fill:color(value),stroke:index === nodeIndex ? '#102e3d' : '#536b75','stroke-width':index === nodeIndex ? 3 : 1,tabindex:0,role:'button','aria-label':`Rad ${row+1}, punkt ${col+1}: ${format(value)} ${f.unit}`});
      if (supportNodes.has(index)) {
        c.setAttribute('data-segment-support','true');
        c.setAttribute('aria-label',c.getAttribute('aria-label') + ', ingår i provsegmentets råunderlag');
        grid.append(svgElement('circle',{cx:x(east),cy:y(north),r:13,fill:'none',stroke:'#704ba0','stroke-width':2,'pointer-events':'none'}));
      }
      c.append(svgElement('title',{},`${east}, ${north}: ${format(value)} ${f.unit}`));
      const choose = () => { nodeIndex = index; $('node').value = index; draw(); $('node').focus(); };
      c.addEventListener('click',choose); c.addEventListener('keydown',e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); } }); grid.append(c);
      if (p.mask && mask !== 1) grid.append(svgElement('text',{x:x(east)+10,y:y(north)-9,'pointer-events':'none'},mask === 0 ? '×' : '?'));
    }));
    text('plot-title', `${f.label} · ${date(p.times[timeIndex])}`);
    text('legend', `${lo} – ${hi} ${f.unit} · blå = lägre, orange = högre · ${missing} saknade prov av ${cols*p.y.length}` + (p.mask ? ` · ${excluded} punkter utan havsmask, varav ${unknownMask} okända (× land, ? okänt)` : ' · giltighetsmask saknas'));
    $('segment-status').hidden = !showSegment; $('segment-node').hidden = !showSegment;
    if (showSegment) {
      text('segment-status', (supportComplete ? '' : failureText() + ' Inget fullständigt stöd kan markeras. ') + `${supportNodes.size} punkter i provsegmentets underlag vid vald sparad tid. Även grannpunkter och tider utanför själva passagen ingår i granskningen. Det streckade området omsluter hela banan och visar inte banans form. Grå ram visar de sparade nodgränserna; diagrammets axlar kan utökas för att visa hela höljet. Giltighetsmask och beräkning mellan punkterna saknar verifiering. En verklig rutt kan ännu inte kopplas säkert till underlaget.`);
      text('segment-node', !supportComplete ? 'Provsegmentets underlag är ofullständigt. Vald punkt får inte användas som ett klippt positivt stöd.' : supportNodes.has(nodeIndex) ? 'Vald punkt ingår i provsegmentets råunderlag vid denna tid. Det bevisar inte att provet är giltigt för ruttberäkning.' : 'Vald punkt ingår inte i provsegmentets råunderlag vid denna tid.');
    }
    const latitudes = p.latitude.flat(), longitudes = p.longitude.flat();
    text('extent', `Sparade nodgränser: ${p.axis_labels[0]} ${p.x[0]} till ${p.x.at(-1)}; ${p.axis_labels[1]} ${p.y[0]} till ${p.y.at(-1)}. ${cols} × ${p.y.length} punkter. Källans latitudgränser ${Math.min(...latitudes)} till ${Math.max(...latitudes)}°; longitudgränser ${Math.min(...longitudes)} till ${Math.max(...longitudes)}°. Gränserna bevisar inte täckning mellan punkterna eller utanför dem.`);
    text('coordinates', `Källkoordinater: ${p.x[i]}, ${p.y[j]}. Latitud ${p.latitude[j][i]}°, longitud ${p.longitude[j][i]}°. Ingen datumomvandling till gemensamt kartunderlag antas.`);
    $('values').replaceChildren(); for (const other of Object.values(p.fields)) pair($('values'), `${other.label} (${other.unit})`, format(other.values[timeIndex][j][i]));
    text('mask', p.mask ? `Vågmask vid punkten: ${p.mask[j][i] === 1 ? '1 – hav' : p.mask[j][i] === 0 ? '0 – land' : 'okänd'}.` : 'Giltighetsmask: okänd.' );
    if (p.land_fraction) text('mask', `Giltighetsmask: okänd. Markandel: ${p.land_fraction[j][i]} (0–1).`);
    const series = $('series'); series.replaceChildren(); $('series-table').replaceChildren();
    series.append(svgElement('text',{x:15,y:24},`${f.label} (${f.unit})`),svgElement('text',{x:15,y:48},String(hi)),svgElement('text',{x:15,y:158},String(lo)));
    p.times.forEach((t,k) => {
      const value = f.values[k][j][i], px = 90 + k/(p.times.length-1)*570;
      const tr = element('tr'); tr.append(element('td',date(t)),element('td',`${format(value)}${Number.isFinite(value) ? ' '+f.unit : ''}`)); $('series-table').append(tr);
      if (Number.isFinite(value)) {
        const c = svgElement('circle',{cx:px,cy:150-(hi===lo?.5:(value-lo)/(hi-lo))*90,r:k===timeIndex?8:5,fill:color(value),stroke:'#163342'}); c.append(svgElement('title',{},`${date(t)}: ${value} ${f.unit}`)); series.append(c);
      } else series.append(svgElement('text',{x:px,y:150,'text-anchor':'middle'},'×'));
      series.append(svgElement('text',{x:px,y:187,'text-anchor':'middle'},new Date(t).toISOString().slice(11,16)));
    });
    $('timeline').setAttribute('aria-valuetext',date(p.times[timeIndex]));
  }
  for (const p of data.products) { const b = element('button',p.label); b.type='button'; b.dataset.product=p.id; b.addEventListener('click',()=>selectProduct(p)); $('products').append(b); }
  $('field').addEventListener('change',()=>{ fieldKey=$('field').value; draw(); });
  const setTime = value => { timeIndex=Number(value); $('time').value=timeIndex; $('timeline').value=timeIndex; draw(); };
  $('time').addEventListener('change',()=>setTime($('time').value)); $('timeline').addEventListener('input',()=>setTime($('timeline').value));
  $('node').addEventListener('change',()=>{ nodeIndex=Number($('node').value); draw(); });
  $('segment-toggle').addEventListener('change',draw);
  selectProduct(product);
})();
