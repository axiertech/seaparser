// Map rendering only. GeoJSON is always longitude, latitude; Leaflet clicks are lat/lng.
export function createMap(L, element, scene, onPick) {
  const map = L.map(element, { maxZoom: 22, minZoom: scene.map_min_zoom ?? (scene.profile !== 'synthetic' ? 14 : 17), zoomControl: true });
  const coverage = L.geoJSON(scene.coverage, { style: { color: '#577f90', fillOpacity: 0.05, dashArray: '3 6' } }).addTo(map);
  // Calculation geometry remains intact; only its optional display is hidden.
  const basis = L.layerGroup();
  const basisStyle={color:'#718795',weight:1,dashArray:'4 5',fillOpacity:0,opacity:.8};
  if (scene.land_display) {
    L.geoJSON(scene.land_display,{style:basisStyle}).addTo(basis);
    map.attributionControl.addAttribution('Land: <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors, ODbL</a>');
  }
  L.geoJSON(scene.obstacles,{style:basisStyle}).addTo(basis);
  const margins = L.layerGroup().addTo(basis);
  const toggle=L.control({position:'topright'});
  toggle.onAdd=()=>{
    const box=L.DomUtil.create('div','leaflet-bar');
    const button=L.DomUtil.create('button','calculation-overlay-toggle',box);
    button.type='button';button.textContent='Visa beräkningsunderlag';button.setAttribute('aria-pressed','false');
    L.DomEvent.disableClickPropagation(box);L.DomEvent.disableScrollPropagation(box);
    button.addEventListener('click',()=>{const visible=map.hasLayer(basis);if(visible)map.removeLayer(basis);else basis.addTo(map);button.textContent=visible?'Visa beräkningsunderlag':'Dölj beräkningsunderlag';button.setAttribute('aria-pressed',String(!visible));});
    return box;
  };
  toggle.addTo(map);
  const routes = L.layerGroup().addTo(map);
  const markers = L.layerGroup().addTo(map);
  map.fitBounds(coverage.getBounds(), { padding: [20, 20] });
  map.setMaxBounds(coverage.getBounds().pad(0.5));
  map.on('click', event => onPick({ latitude: event.latlng.lat, longitude: event.latlng.lng }));
  function endpoints(start, target) {
    markers.clearLayers();
    for (const [point, color, name] of [[start, '#173344', 'Start'], [target, '#a22d3d', 'Mål']]) {
      const label = document.createElement('span'); label.textContent = name;
      L.circleMarker([point.latitude, point.longitude], { radius: 7, color, fillOpacity: 1 }).bindTooltip(label).addTo(markers);
    }
  }
  function show(result, identifier = null) {
    routes.clearLayers(); margins.clearLayers();
    // Thin outlines and labels replace the former dominant metric-width stroke.
    // The numerical margin is still evaluated by the unchanged route engine.
    const drawMargin = () => {
      margins.clearLayers();
      L.geoJSON(result.obstacles,{style:basisStyle,onEachFeature:(feature,layer)=>{
        const text=document.createElement('span');text.textContent=`Hinderhölje · routingmarginal ${feature.properties.margin_m} m (beräkningsvärde)`;layer.bindTooltip(text);
      }}).addTo(margins);
    };
    drawMargin();
    const selected = { type: 'FeatureCollection', features: result.routes.features.filter(f => identifier === null || f.properties.id === identifier) };
    L.geoJSON(selected, {
      style: feature => ({ color: feature.properties.kind === 'accepted' ? (['conditional_on_assumptions','estimated_high_uncertainty'].includes(feature.properties.qualification) ? '#b78023' : '#087156') : '#6c59a3', weight: feature.properties.kind === 'accepted' ? 4 : 2, dashArray: feature.properties.qualification==='estimated_high_uncertainty'?'8 5':feature.properties.kind === 'planned' ? '6 5' : null }),
      pointToLayer: (feature, latlng) => L.circleMarker(latlng, { radius: feature.properties.kind === 'waypoint' ? 4 : 2, color: '#66538c' }),
      onEachFeature: (feature, layer) => { const label = document.createElement('span'); label.textContent = `${feature.properties.candidate}: ${feature.properties.status}`; layer.bindTooltip(label); }
    }).addTo(routes);
  }
  return { map, endpoints, show, background() {
    if (scene.profile === 'synthetic') return;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxNativeZoom: 19, maxZoom: 22,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }).addTo(map);
  }, dispose() { map.remove(); } };
}
