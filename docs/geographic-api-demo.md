# Geografisk API- och kartdemonstration

Sammanhängande flöde: kartklick för start/mål → POST /api/plans → separat
beräkningsprocess → GeoJSON i Leaflet → granskade modellvägpunkter som GPX.
Återanvänder polygonroutingen, frysta prognoser, polar, väder- och ankomstkontroller.
Ingen databas, GPS, AIS eller extern prognoshämtning. Designereditor återstår.

## Koordinater och giltighet

infrastructure/geography.py använder PROJ/pyproj:s ellipsoidiska azimutalt
avståndsriktiga projektion (AEQD), WGS84, origo 58°N 11°E, meter öst/nord.
[Officiell projektionsdefinition](https://proj.org/en/stable/operations/projections/aeqd.html).
Alltid longitude/latitude till pyproj och GeoJSON, explicit latitude/longitude
som namngivna API-fält. Ingen höjd-/tidvattenomvandling. Nätverksgrids avstängda.
Giltigt stöd: geodesisk radie högst 1000 m från origo, ytterligare förfilter
57.98–58.02°N, 10.96–11.04°E; allt utanför avvisas. Datumlinje/poler ingår inte.
Prognosområdet är ännu mindre: öst -50…150 m, nord -50…50 m. Utanför prognosen
blir stöd otillräckligt även om koordinaten kan projiceras. Inga extrapolerade data.

Numerisk referenstolerans 0.01 m; tester mot fristående geod-direktreferenser
100/500/900 m använder 0.00001 m, separat WGS84-meridianintegral 0.000001 m.
Roundtrip kontrolleras separat och används inte ensam som korrekthetsbevis.
AEQD bevarar radialavstånd/azimut från origo; godtyckliga raka lokala segment är
inte exakt geodesiska bågar. För denna högst kilometerradie är projektions-
skillnaden liten men inte bevis för verklig hinderprecision. Ingen verklig
säkerhetsmarginal/navigerbarhet certifieras. Syntetiska vind-/strömvektorer har
fasta öst/nord-axlar vid origo; verkliga vektorer behöver positionsberoende
referensramskontroll före integration. Projektionens definition och versioner
följer resultatet. GPX rundar till 10 decimalgrader, utan påhittade GPS-tider/höjder.

## Gränssnitt och arbetsbudget

FastAPI i api/ validerar indata; application/geographic_plan.py komponerar
befintlig planering och presentation/gpx.py exporterar GPX 1.1 rte/rtept.
POST /api/plans accepterar två positioner, marginal 0–10 m, scenario och högst
två unika avgångsoffset ur {0,600} s för det frysta underlaget. Inga godtyckliga
prognoser, polygoner eller sökparametrar tas emot. 202 ger jobb-id; GET samma
resurs returnerar queued/running/completed/failed. GET /api/scene ger fryst scen.
GET /api/plans/{id}/routes/{route}/gpx exporterar endast framgångsrik kandidat.
GeoJSON skiljer streckad hel kandidat, accepterad delbana, vägpunkter och hinder.
Avbrott ger inte fabricerad ankomst/exponering eller ett verifierat helt segment.

Högst 8192 byte kropp, 5 s mottagningstid, 2 aktiva jobb, 8 jobb i minnet,
20 s verklig tidsgräns/job. Varje jobb körs i egen process som dödas/återtas vid
avbrott, tidsgräns eller nedstängning. 429 vid upptagen kapacitet. Resultat tas
bort efter 300 s från skapandet, och omstart tappar jobb. En enda API-worker
krävs; fler skulle multiplicera gränserna. Domänbudget: 8 kandidater, 4 väg-
punkter, 1000 grafexpansioner, 10 noder, 2000 färdsteg och 1800 s simulerad tid.
Ingen beständig kö eller global optimalitet. Jobb-id är inte användarautentisering.

## Lokal körning och deployment

Installera endast låsta projektberoenden i .venv: pip --require-hashes
--only-binary=:all: -r requirements.lock. Låset gäller CPython 3.14 Linux x86_64.
`npm --prefix frontend ci --ignore-scripts`, sedan `npm --prefix frontend run build`.
`.venv/bin/python -B -m scripts.local_demo` ger helhetsflödet endast på
http://127.0.0.1:8765/. Inget startas automatiskt eller fristående i bakgrunden.
Frontendbuild har en explicit publik fillista och lokal Leaflet inklusive licens.
Ingen karta/prognos laddas från tredje part; syntetisk bakgrund är valt demolager.
Framtida verklig bakgrund väljs separat enligt [map-sources.md](map-sources.md).

Apache-proxy och systemtjänst är konkreta förslag i deployment/, inte aktiverade.
Samlat administratörsunderlag där omfattar proxy, tjänst, tidigare 403 och publik
frontend. Ingen ny offentlig API-publicering, systemändring eller DB-migration.
