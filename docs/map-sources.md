# Kartbakgrund: officiell granskning 2026-10-12

Bakgrund är separat från geografiska hinderdata. Bildsymboler, djupfärger eller
frånvaro av symbol bevisar inte navigerbarhet. Den fungerande demonstrationen
väljer ett lokalt syntetiskt lager; inga externa tiles hämtas. Varken verklig
bakgrund eller verkliga hinder importeras i denna leverans.

| Kandidat | Format och attribution | Licens/kommersiell användning | Trafik/drift |
| --- | --- | --- | --- |
| OpenSeaMap | Raster PNG seamark-overlay, z/x/y; separat baskarta behövs. OpenSeaMap och OSM-attribution och licenslänk ska visas | Officiell FAQ anger ODbL för data och CC BY-SA 2.0 för karttiles; kommersiell användning med villkor, inte obegränsad hosted kapacitet | Ingen verifierad numerisk kvot/SLA eller komplett aktuell kommersiell tile-policy funnen i granskade officiella sidor; klarlägg före produkttrafik/bulk/offline |
| OpenWaters Seamap | MapLibre-style JSON med vektortiles/TileJSON, sprites och fonts; inte direkt ett Leaflet rasterlager. Bevara style-attribution | Seamap tiles/styles/sprites CC BY 4.0; © Open Waters: Seamap samt OSM/andra källors attribution. Specifik sida skiljer GPL-3.0-pipeline/style/symbolkod från ärvd MIT-kod | Ingen verifierad Seamap-specifik numerisk trafikgräns/SLA funnen; AIS-tilekvoten gäller inte Seamap. Kommersiell produkttakt/offlinevillkor behöver klarläggas |

[OpenSeaMap FAQ](https://openseamap.org/index.php?L=1&id=faq),
[officiell tile-serverlista](https://wiki.openseamap.org/wiki/OpenSeaMap-dev:Server),
[OpenWaters Seamap](https://openwaters.io/charts/seamap/),
[officiell style-README](https://github.com/openwatersio/seamap/blob/main/style/README.md).

OpenWaters varnar uttryckligen att detta inte är officiellt navigationsunderlag:
OSM-sjömärken kan saknas/vara gamla och djup är inte reducerade till sjökortsdatum
eller korrigerade för tidvatten. Därför får dess djupbilder inte bli routingsdjup.
Generell MIT-/CC0-översikt ersätter inte Seamaps specifika licenser.
[Licensöversikt](https://openwaters.io/license/).

Om OSM-standardtiles väljs som separat baskarta gäller dess egen policy, bland
annat identifiering/Referer, caching och förbud mot bulk/offline-prefetch. Den är
inte OpenSeaMaps eller OpenWaters tillstånd. Ingen tjänstkontakt/konto/köp gjordes.
[OSMF:s officiella policy](https://operations.osmfoundation.org/policies/tiles/).

Demobeslut: Leaflet 1.9.4 (BSD-2-Clause, officiellt stabil version) distribueras
lokalt från versionslåst npm, utan tile-URL. Externa bakgrunder lämnas urkopplade
för offlineflöde och oklar hosted trafikpolicy. Detta binder inte framtida kart-
eller designereditorval. [Leaflet-versioner](https://leafletjs.com/download.html).
