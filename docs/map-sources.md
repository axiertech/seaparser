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

## Vinga: separat granskningsleverans 2026-10-12

`make land-preview` skapar `frontend/land-dist/land-review.html` och två GeoJSON-filer.
Det är en separat land-/bakgrundsgranskning, inte en ny publik planeringsprofil.
Syntetiska index/API/prognoser och regressioner ändras inte. Lokal server behövs
för fetch; exempel: `.venv/bin/python -m http.server 8766 --bind 127.0.0.1
--directory frontend/land-dist` på ledig port. Ingen kopiering till webbroten eller tjänstomstart ingår.

Källa: ett manuellt, begränsat OSM API-utdrag för bbox
11.58,57.62,11.63,57.65; den frysta filen omfattar sex slutna landringar inom
11.593–11.614°E, 57.629–57.637°N runt Vinga. `fixtures/vinga-land.geojson`
innehåller hämttid, källhash, way-id/version/tid, täckning och licens.
Bidragares personuppgifter från XML ingår inte. Offlineimportören
`scripts.import_vinga_land` tar XML och explicit `--retrieved-at`; inga HTTP-anrop.
Öppna/icke entydigt sammanfogade kustlinjer inkluderas inte: fullständighet är
uttryckligen okänd. API-bbox kan dessutom missa korsande ways utan nod i bbox.
Frånvaro av land i utdraget betyder därför inte fri passage.
[Officiellt bbox-kontrakt](https://wiki.openstreetmap.org/wiki/API_v0.6#Retrieving_map_data_by_bounding_box:_GET_/api/0.6/map).

Landdatabas och härledda routinghöljen distribueras under ODbL-1.0 med
© OpenStreetMap contributors och nedladdningsbara källmetadata.
Licensen medger kommersiell användning med attribution/share-alike-villkor;
det ger inte obegränsad rätt till hosted API eller tiles.
[Licens](https://opendatacommons.org/licenses/odbl/1-0/),
[OSM:s licensförklaring](https://www.openstreetmap.org/copyright),
[API-policy](https://operations.osmfoundation.org/policies/api/).

Bakgrund: OSM standard raster, endast efter manuellt klick. Normal webbläsarcache,
synlig attribution och Referer, ingen prefetch/offlinearkiv eller automatisk
hämtning i tester. Best-effort utan SLA; annan leverantör krävs om produkttrafik
inte ryms inom policyn. [Tile-policy](https://operations.osmfoundation.org/policies/tiles/).
OpenSeaMap/OpenWaters-alternativen ovan är fortsatt separata, inte valda här.

Routingadapter använder WGS84 AEQD vid 57.633°N, 11.605°E, bara det angivna
rektangulära området (under 1.5 km radie); referenstest mot geodesiska avstånd
på 1000 m, tolerans 0.01 m. Orange visar ursprungliga landringar, rött deras
konservativa konvexa höljen. Exakta predikat kontrollerar att alla projicerade
landpunkter ligger i höljet; ett konvext hölje täcker även ringens raka kanter
och insida. Befintlig motor testar hela segment inklusive 10 m marginal.
Höljet kan spärra vikar/passager och garanterar inte källprecision, strandens
verkliga läge eller fullständighet. Det är geometriskt underlag, ingen snabbaste
väderrutt. Regional koppling till fryst syntetiskt väder/API-planering finns nu på granskningsbranchen; se geographic-routing.md.
Djup, djupgåendeutrymme och höjdreferens är okända; inget tidvatten kombineras.
