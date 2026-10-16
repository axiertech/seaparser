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
    $('hashes').replaceChildren(); for (const [name, hash] of Object.entries(p.source_hashes)) pair($('hashes'), name, hash);
    draw();
  }
  function draw() {
    const p = product, f = p.fields[fieldKey], cols = p.x.length;
    const j = Math.floor(nodeIndex/cols), i = nodeIndex%cols;
    const all = f.values.flat(2).filter(Number.isFinite), lo = all.length ? Math.min(...all) : 0, hi = all.length ? Math.max(...all) : 0;
    const color = v => Number.isFinite(v) ? `hsl(${210 - 175 * (hi === lo ? .5 : (v-lo)/(hi-lo))}, 65%, 43%)` : '#ffffff';
    const x = v => 80 + (v-p.x[0])/(p.x.at(-1)-p.x[0])*585;
    const y = v => 350 - (v-p.y[0])/(p.y.at(-1)-p.y[0])*300;
    const grid = $('grid'); grid.replaceChildren();
    grid.append(svgElement('line',{x1:80,y1:350,x2:665,y2:350,class:'grid-axis'}), svgElement('line',{x1:80,y1:50,x2:80,y2:350,class:'grid-axis'}));
    grid.append(svgElement('text',{x:80,y:385},String(p.x[0])),svgElement('text',{x:665,y:385,'text-anchor':'end'},String(p.x.at(-1))),svgElement('text',{x:80,y:417},p.axis_labels[0]),svgElement('text',{x:12,y:24},p.axis_labels[1]));
    grid.append(svgElement('text',{x:8,y:350},String(p.y[0])),svgElement('text',{x:8,y:55},String(p.y.at(-1))));
    let missing = 0, excluded = 0, unknownMask = 0;
    p.y.forEach((north,row) => p.x.forEach((east,col) => {
      const value = f.values[timeIndex][row][col], mask = p.mask?.[row][col];
      if (!Number.isFinite(value)) missing++;
      if (p.mask && mask !== 1) { excluded++; if (mask === null) unknownMask++; }
      const index = row*cols+col;
      const c = svgElement('circle',{cx:x(east),cy:y(north),r:index === nodeIndex ? 10 : 7,fill:color(value),stroke:index === nodeIndex ? '#102e3d' : '#536b75','stroke-width':index === nodeIndex ? 3 : 1,tabindex:0,role:'button','aria-label':`Rad ${row+1}, punkt ${col+1}: ${format(value)} ${f.unit}`});
      c.append(svgElement('title',{},`${east}, ${north}: ${format(value)} ${f.unit}`));
      const choose = () => { nodeIndex = index; $('node').value = index; draw(); $('node').focus(); };
      c.addEventListener('click',choose); c.addEventListener('keydown',e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); } }); grid.append(c);
      if (p.mask && mask !== 1) grid.append(svgElement('text',{x:x(east)+10,y:y(north)-9,'pointer-events':'none'},mask === 0 ? '×' : '?'));
    }));
    text('plot-title', `${f.label} · ${date(p.times[timeIndex])}`);
    text('legend', `${lo} – ${hi} ${f.unit} · blå = lägre, orange = högre · ${missing} saknade prov av ${cols*p.y.length}` + (p.mask ? ` · ${excluded} punkter utan havsmask, varav ${unknownMask} okända (× land, ? okänt)` : ' · giltighetsmask saknas'));
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
  selectProduct(product);
})();
