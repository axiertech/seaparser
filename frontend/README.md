# Grafisk ruttjämförelse med verkliga data

Standard är nu Vinga med verklig fryst MET-vind samt Copernicus-vågor/ström och
uttryckliga utvecklingsantaganden. Öppna den självförsörjande visningen i
`artifacts/real-route-review/index.html`, eller se
[utvecklingsflödet](../docs/development-real-routing.md) för kartklick och egen
ruttberäkning. Inga syntetiska marina ersättningsvärden används i standardflödet.

Historiska underlag, antaganden och okänd källkvalificering redovisas tydligt.
Syntetiska referensfall nedan finns kvar för regressionstester.

# Syntetiska referensfall för tester

`make check` verifierar lokala HTML/CSS-resurser och Python-tester för rapport,
export, säker textåtergivning och kontrollstatus. Den statiska rapportens åtta tester ligger i tests/test_scenario_html.py.
Den interaktiva kartintegrationen har fyra Node-tester. Leaflet/jsdom och deras
beroenden är versionslåsta med integritet i package-lock.json.

Generera en självförsörjande visning med fem reproducerbara scenarier:

```
.venv/bin/python -B -m scripts.export_scenario_html --output /tmp/seaparser-demo-index.html
```

En befintlig JSON-rapport kan visas med `--report rapport.json`. Varje scenario
kan exporteras som exakt ursprunglig JSON via nedladdningslänken; rapportens
SHA-256 visas för kontroll. HTML innehåller inbäddad CSS och SVG, inga skript,
nätverksanrop, externa typsnitt eller kartresurser. Publicera endast målfilen.

Layout/CSS finns i scenario-demo.html och scenario-demo.css. Presentationen i
presentation/scenario_html.py läser färdiga rapporter och beräknar inga rutter.
Orkestrering sker i scripts/export_scenario_html.py. Streckade linjer visar hela
kandidaten; heldragna linjer endast accepterade integrerade segment.

Kontroller gäller den numeriska modellen och explicit undersökta alternativ.
Konstaterat överskridande skiljs från otillräckligt konservativt bevis eller
saknade data. Ingen verifierad kandidat är inte bevis för att andra rutter är
omöjliga. Markvind/Hs certifieras konservativt; komfort är syntetisk och ej
validerad. Syntetiska koordinater/hinder är ingen sjökarta. Uppskattad polar,
fryst planeringstid, datasetversion, avbrottsorsaker och ankomstkontroll visas.

Detta är ett granskningsverktyg. Visuell editor väljs separat efter utvärdering;
HTML/CSS uppfyller inte ensamt kravet på visuell redigering. AIS är fortsatt
lågprioriterat. Ingen GPS, övervakning eller kollisionsrådgivning ingår.

## Interaktiv geografisk teknisk demo

`npm run build` genererar endast publika filer i dist/. Generera också regionala
bundlet med `.venv/bin/python -B -m scripts.land_preview --bundle --output frontend/land-dist`. Kör sedan från repo:
`.venv/bin/python -B -m scripts.local_demo` och öppna http://127.0.0.1:8765/.
Kartklick → FastAPI-jobb → beräknad GeoJSON → planerad GPX. Leaflet distribueras
lokalt; standardprofilen använder verkliga prognosgrid och fryst OSM-land, med explicit konfigurerade metadataantaganden. `npm test` provar
flödet med verkligt loopback-API och Leaflet i jsdom, inte en visuell browseraudit.
Se docs/geographic-api-demo.md och deployment/README.md; inget publiceras automatiskt.
