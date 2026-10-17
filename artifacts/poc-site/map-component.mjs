// Map rendering only. GeoJSON is always longitude, latitude; Leaflet clicks are lat/lng.
export function createMap(L, element, scene, onPick) {
  const map = L.map(element, { maxZoom: 22, minZoom: scene.profile !== 'synthetic' ? 14 : 17, zoomControl: true });
  const coverage = L.geoJSON(scene.coverage, { style: { color: '#577f90', fillOpacity: 0.05, dashArray: '3 6' } }).addTo(map);
  if (scene.land_display) {
    L.geoJSON(scene.land_display, { style: { color: '#9a5830', fillOpacity: 0.35 } }).addTo(map);
    map.attributionControl.addAttribution('Land: <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors, ODbL</a>');
  }
  L.geoJSON(scene.obstacles, { style: { color: '#9a5830', fillColor: '#c6b38d', fillOpacity: scene.profile !== 'synthetic' ? 0.1 : 0.8 } }).addTo(map);
  const margins = L.layerGroup().addTo(map);
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
  let marginHandler;
  function show(result, identifier = null) {
    routes.clearLayers(); margins.clearLayers();
    // Buffer strokes visualize metric margin at current map scale, not new routing geometry.
    const drawMargin = () => {
      margins.clearLayers();
      const pixelsPerMetre = map.getSize().x / Math.max(1, map.distance(map.containerPointToLatLng([0, 0]), map.containerPointToLatLng([map.getSize().x, 0])));
      L.geoJSON(result.obstacles, { style: feature => ({ color: '#9a5830', fillOpacity: 0, weight: Math.max(1, 2 * feature.properties.margin_m * pixelsPerMetre), lineJoin: 'round' }) }).addTo(margins);
    };
    if (marginHandler) map.off('zoomend', marginHandler);
    marginHandler = drawMargin; map.on('zoomend', drawMargin); drawMargin();
    const selected = { type: 'FeatureCollection', features: result.routes.features.filter(f => identifier === null || f.properties.id === identifier) };
    L.geoJSON(selected, {
      style: feature => ({ color: feature.properties.kind === 'accepted' ? (feature.properties.qualification === 'conditional_on_assumptions' ? '#b78023' : '#087156') : '#6c59a3', weight: feature.properties.kind === 'accepted' ? 4 : 2, dashArray: feature.properties.kind === 'planned' ? '6 5' : null }),
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
