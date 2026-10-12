const map=L.map('map').setView([57.633,11.605],15);
map.attributionControl.addAttribution('Land: <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors, ODbL</a>');
for (const [url,color] of [['land.geojson','orange'],['routing.geojson','red']]) {
 const response=await fetch(url); if(!response.ok) throw new Error('Saknat landunderlag');
 L.geoJSON(await response.json(),{style:{color,weight:2,fillOpacity:.12}}).addTo(map);
}
document.querySelector('#background').addEventListener('click',event=>{
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxNativeZoom:19,maxZoom:22,
 attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
 event.target.disabled=true;
},{once:true});
