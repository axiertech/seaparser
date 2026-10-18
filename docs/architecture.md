# Arkitektur

## Grundprincip

En modulär applikation med separat beräkningsprocess. Ingen mikrotjänstplattform behövs i första leveransen. AI används för utveckling och granskning; själva ruttberäkningen utförs av en deterministisk motor.

## Föreslagen teknik

Python för motor och backend, FastAPI för API, PostgreSQL/PostGIS för beständig och geografisk lagring samt React/TypeScript för frontend. Detta är föreslagen inriktning, inte en installerad eller versionslåst stack. Visuell layouteditor återstår att välja. Containerdrift utvärderas mot serverns förutsättningar och behörigheter innan installation.

## Ansvar

Frontend presenterar komponenter och samlar användarval. API validerar anrop och kontrollerar identitet och behörighet. Applikationslagret samordnar användningsfall. Domänen innehåller båtprestanda, begränsningar och ruttberäkning. Infrastrukturen implementerar väderhämtning, databasåtkomst och jobbhantering.

Domänen känner inte till API-ramverk, databassessioner, leverantörers JSON-format eller layouteditor. Infrastrukturen omvandlar externa data till dokumenterade interna modeller.

## Data och konfiguration

Hemligheter och miljöinställningar ligger utanför repositoryt i `/home/web/seaparser/config/app.env`. Filformatet läses av en definierad konfigurationsladdare; filen ska inte förutsättas vara ett shellscript. Tomma nödvändiga värden ska ge tydliga fel utan hemligheter. Gemensamma icke-hemliga standardvärden versionshanteras. Båtprofiler och användarpreferenser lagras som applikationsdata.

Varje ruttresultat ska identifiera indata, båtmodell, prognoskälla och prognosversion, körningstid, giltighetstider, algoritmversion och begränsningar. Gemensamma prognosfält kan återanvändas mellan användare. Lagringsformat för stora prognosfält väljs efter mätning; alla rutnätsvärden ska inte automatiskt bli separata databasrader.

## Routing

Algoritmvalet är öppet. Jämför en enkel verifierbar referens med tidsutvidgad graf eller isokronbaserad sökning. Enbart bästa ankomst per geografisk punkt är inte ett tillräckligt tillstånd när tid, komfort eller manöverkostnader påverkar fortsatt resa. Dokumentera approximationer, tidssteg, upplösning och eventuell väntan innan optimering.

## Layout utan programmerare

Bygg funktionella komponenter med dokumenterade inställningar. En visuell editor ska kunna komponera dem, styra responsiva layouter och använda ett gemensamt tema. Förhandsgranskning och publicerad layout ska hållas åtskilda. Layoutversioner ska kunna återställas och egna komponenter behålla sin kod och API-koppling oberoende av editorn. Export eller egen lagring ska utvärderas innan bindande verktygsval.

## Uppgraderingar

Låsfiler och fasta deploymentversioner, kontrollerade beroendeuppdateringar, automatiska tester och versionshanterade migrationer. Driftplanen ska omfatta hälsokontroller och återställning. En kodrollback återställer inte automatiskt databasen; migrationer måste planeras separat.

Utveckling använder endast databas och roll seaparser. Enhetstester kräver ingen
databas. Databastester begränsas till rollback och testegna objekt. Inför drift
ska miljön separeras och en ny driftroll skapas; utvecklingsuppgifter återanvänds inte.

Prognosadaptrar ligger i infrastrukturlagret och normaliserar färdighämtade
externa payloads till domänens ForecastDataset. Underlaget är en helt
materialiserad, fryst uppsättning GridProduct med separat ProductMetadata för
vind/ström/vågor. Det implementerar miljögränssnittet utan SQL, HTTP eller lazy
callbacks. Rutt-/avgångsmotorn får samma underlag hela jämförelsen; byte av
prognos sker endast genom ett nytt explicit underlag/anrop. Transport ingår inte
i den syntetiska adaptern. Lokalt geografiskt origo, enheter, referensramar,
interpolationsregel och gap/masker valideras före planering. För frysta rutnät
kontrolleras dessutom interpolationsstöd längs hela accepterade integrerade
segment. Markrelativ vindstyrka och Hs certifieras med konservativa cellhöljen
över segmentets rum/tid-box; osäkra bevis avvisas. Ankomst kontrolleras separat.
Övriga väder-/komfortdata och verklig källkvalitet är inte kontinuerligt verifierade.

application/planning.py samordnar ett fryst PlanRequest till domänens
avgångsjämförelse och ett reproducerbart JSON-resultat med indata-/dataset-/
båtfingeravtryck. scripts/plan_synthetic.py komponerar syntetisk adapter och
usecase samt sköter CLI-presentation. Ingen transport eller databas ingår.
Algoritm-/schemaversion och alla parametrar följer resultatet; observerad
exekveringstid hålls separat från den deterministiska resultatidentiteten.

Senare lågprioriterad trafikbelastningsinformation använder ett separat fryst
TrafficSnapshot och visar observerad/historisk täckning tillsammans med planens
passagetider. Ruttmotorn läser inte AIS-strömmar. Ingen GPS-/trafikövervakning,
CPA-/kollisionsanalys eller undanmanöver ingår. Tidvatten och stationsström får
separata adapterkontrakt med vertikalt datum respektive riktning/djup; ingen
stationsprognos får bli ett områdesfält utan verifierad modell.

HTML-granskningsverktyget i presentation/scenario_html.py konsumerar befintliga
JSON-rapporter; HTML/CSS ligger i frontend/. scripts/export_scenario_html.py
orkestrerar syntetiska scenarier utanför ruttmotorn och genererar en enda
självförsörjande HTML-fil. Publik webbrot innehåller endast genererad visning.
Se frontend/README.md för export, bevisstatus och avgränsningar.

Geografisk routing separerar versionsbundet hinder-/djupunderlag från kartbakgrund.
Lokala syntetiska polygoner prövar slutna segment och euklidisk marginal med exakta
predikat på lagrade tal. En begränsad graf genererar kompletta kandidater före
befintlig tidsberoende simulering; geometrisk längd är ingen väderkostnad.
application/obstacle_planning.py redovisar sökstatus separat från färdresultat.
Geografisk transformation, kartpresentation och waypointexport för plotter är
nästa steg; ingen GPS-följning. Se geographic-routing.md för avgränsningar,
metadata och kompatibla vertikala datum för djup/tidvatten.

Teknisk geografisk integration: api/ validerar/hanterar HTTP; JobStore i
infrastructure/ kör separata tidsbegränsade processer. application/geographic_plan.py
återanvänder planering, presentation/gpx.py exporterar och frontend/map/
skiljer layout, kartkomponent och transport. AEQD-transformering ligger utanför
domänen. Ingen SQL eller offentlig API-deployment ingår. Se geographic-api-demo.md.


## Verklig utvecklingsrouting med redovisade antaganden 2026-10-17

Standardens geografiska Vinga-usecase komponerar frysta verkliga MET-native-
vindnoder och befintliga WAV/PHY-grid. application/development_weather.py läser
explicit utvecklingskonfiguration och bevarar källmetadata separat från antagna
fält. infrastructure/development_forecast.py implementerar miljö-/segment-
gränssnittet utan SQL, HTTP eller filåtkomst under ruttjämförelsen. Både
produkternas assumed_fields och resultatets övergripande villkor finns med i
proveniens och identitet. Råkällor och strikta granskningsrapporter ändras inte.

MET samplas på native-grid; ingen gles omgridning till marinens 2x2-grid införs.
Stöd och ett konservativt verkligt vindnodshölje förbereds före routing. Befintlig
marin cell-/segmentkontroll återanvänds för ström och vågor. Domänens generella
certifieringsfunktion kan välja waves separat vid denna komposition, medan
standardanropet för GridProduct-baserade vind/vågfall är oförändrat. Källan får
fortfarande status unverified även när modellgränserna uppfylls villkorligt.
Se development-real-routing.md för parametrar, begränsningar och grafisk leverans.

Native-läget i samma CopernicusMarineAdapter materialiserar NativeMarineDataset
med produktens egna geografiska axlar. infrastructure/native_marine.py sköter
punktinterpolation och konservativ hel-disk-/tidsomslutning utan transport,
SQL eller UI. Legacy GridProduct-läget och 1 m-gränsen är oförändrade. Samma
NetCDF-fältmaterialisering används. Namngiven utvecklingskomposition kan
använda native-läget med oförändrat 900 m-tak och separat käll-/antagandeproveniens.
Se native-marine-geometry.md; större landgranskning är separat från kartbakgrund.

Exakt polygonbox-avvisning och en begränsad geometri-LRU minskar kostnaden utan att ändra hinderpredikat. Native-kandidataudit använder explicit offlinebudget66, alla24hinder och befintlig planering. API-budgeten är oförändrad. Se native-candidate-budget.md.

Regionala grundkomponenter separerar materialiserad OSM-vattengeometri i
`infrastructure/coastal_water.py`, ren budgetbegränsad kandidatgenerering i
`prototype/water_routing.py` och uttryckliga reservuppslag i
`infrastructure/marine_reserve.py`. Normaliserade marina komponenter och
MET-native-vind återanvänds. Ingen transport sker under uppslag eller sökning.
Reservposter ger hög osäkerhet, aldrig vädergränscertifiering. Kontrollerade
reservvägar runt uddar återanvänder samma rena kandidatgenerator med explicita
budgetar och spårbar förbindelse. Regional färdkomposition återstår;
se coastal-reserve.md.

Valbar vinga-native-profil komponerar fast17-oktober-väder/24hinder och exakt900m-kandidatdisk i befintlig A*-graf. Alla hinder och integrerade segmentkontroller kvar,21noder inom26gränsen. Befintlig frontend/layout och jobbsystem återanvänds. Se supported-native-routing.md.
