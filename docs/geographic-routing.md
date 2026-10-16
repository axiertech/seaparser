# Geografisk routing: avgränsning och nästa steg

## Implementerad lokal referens

Polygon i prototype/polygon.py är en fryst enkel polygon (3–128 hörn), även
konkav, utan hål. Självkorsningar, dubbla hörn och kollineära intilliggande kanter
avvisas. Koordinater är öst/nord i meter. Kantkontakt och avstånd exakt lika med
marginal är kollision. Segmentets ändpunkter, kantkorsningar och minsta avstånd
till samtliga kanter kontrolleras. Marginalen är euklidisk, inte bara en utökad
box. Predikat och kvadrerade avstånd beräknas rationellt exakt för lagrade tal;
detta bevisar inte att verkliga källkoordinater eller geografisk projektion är exakta.
Informationspolygoner blockerar inte. Okänd kvalitet blir inte fri passage:
angivna hårda förbud undviks även då. Okänd omgivande täckning är inte säkerhetsbevis.

prototype/auto_routing.py skapar grafnoder vid start, mål och fyra hörn utanför
varje hård polygons omslutande box. Marginal + positiv separat hörnklarering
används. Boxarna genererar bara vägpunkter; alla grafkanter prövas mot polygonerna.
Enkla kompletta vägar genereras deterministiskt i stigande geometrisk längd.
Samma grafpunkt kan ingå i flera skilda kandidatvägar; inga färd-/tillståndsetiketter
slås ihop. application/obstacle_planning.py simulerar sedan alla genererade vägar
vid samtliga avgångar med samma frysta planeringstid/dataset och båtmodell.
Faktisk ankomsttid och position förs vidare mellan delsträckor. Hela accepterade
numeriska segment prövas igen mot hinder i befintlig färdmotor, med väder,
prognosstöd och separat ankomstkontroll oförändrade.

Standardbudget: 32 kandidater, 8 vägpunkter, 10000 expansioner/köposter,
66 noder. Hårda budgettak finns. Kandidat-, djup-, nod- eller expansionsgräns
rapporteras som truncated/search_limit eller node_limit; start/mål i förbud
som endpoint_blocked. limit_reason anger nådd budget. No_graph_path betyder ingen väg i just denna graf.
Även en uttömd graf täcker inte alla kontinuerliga möjliga rutter. Boxhörn kan
missa smala passager och konkava genvägar; tidig kandidatgräns kan missa snabbaste
väderrutt. Ingen kryss, väntan, geografisk global optimalitet eller manövermodell.
Hinderhål kräver flera polygoner eller framtida explicit stöd.

CLI: `.venv/bin/python -B -m scripts.plan_polygon --margin-m 2 --clearance-m 5`.
JSON innehåller geometry_search med parametrar/status/längder/scope samt planning
med ordinarie rutt-/avgångsrapport, eller null om inga kandidater genererades.
Top-level input_sha256 identifierar även sökparametrar, metadata och hinder.
JSON-wrappern är ett separat kontrakt; den äldre HTML-exporten tar den inre
planning-rapporten och dess nuvarande kartvy är för rektangelscenarier.
Inga filer publiceras automatiskt och inga externa källor hämtas.

## Förberedda kontrakt, ännu inte verklig integration

| Produkt | Nödvändiga metadata | Routingbetydelse |
| --- | --- | --- |
| Kartbakgrund | Källa/version, region, CRS, licens/attribution | Presentation; inte routingsbevis |
| Land/öar | Polygongeometri, källa/version, CRS, kvalitet/täckning | Hårt förbud enligt uttrycklig policy |
| Grund/djupområden | Geometri, djup/intervall eller unknown, enhet, vertikalt datum, kvalitet | Framtida djupgående + marginal; okänt djup avvisas som otillräckligt underlag |
| Restriktion | Geometri, regel, tidsvillkor/giltighet, källa/version | Hårt förbud eller tydligt informationslager enligt regel |
| Tidvatten | Vattenstånd, station/modell, tid, vertikalt datum, kvalitet | Kombineras med djup endast med kompatibla datum/verifierad transformation |

Nästa tekniska steg: fryst geografiskt underlag med explicit CRS/axelordning,
verifierad transformation till lokal modell inom en begränsad region och
oberoende distans-/projektionstester. Hantera datumlinje/poler eller avvisa dem
utanför dokumenterat stöd. Kartlager ska inte mata routingsmotorn via skärmpixlar.
GPX bör exportera route/rtept i ordning, latitud/longitud enligt GPX-kontrakt,
utan fabricerade GPS-spår eller höjder. Schemavalidering, roundtrip och plotter-
kompatibilitet utvärderas före verklig användning.

Källgranskning ska redovisas separat för kartbakgrund, land, djup och restriktioner:
regional täckning/precision, navigationsstatus, versionsspårning, uppdateringar,
licens för kommersiellt bruk, offline/cachning och export samt eventuell kostnad.
Ingen källa är vald; ingen databasändring, hämtning, betalning eller konto ingår.

## Regional Vinga-planering (granskningsbranch)

`GET /api/scene?profile=vinga` ger område, rekommenderade start/mål, fryst OSM-land
för presentation, sex konservativa routinghöljen och 10 m standardmarginal.
`POST /api/plans` använder `profile: "vinga"`; utelämnad profil behåller det äldre
syntetiska scenariot. Hinder-/väder-/polarlogik finns i motorn, inte endpoints.
Region, koordinater, marginal 0–10 m och högst två fasta avgångar valideras.

Fryst dataset `seaparser-estimated-vinga-weather`, version `vinga-v1-<scenario>`,
är uppskattat syntetiskt testväder, **ingen aktuell/verklig prognos**.
Planeringsklockan är 2026-01-01T00:00:00Z; utfärdandetid 100 s före planeringen,
avgång 02:00Z/02:10Z, giltighet 02:00Z–02:30Z. Prognosålder bedöms vid fryst
planeringstid. Dataset normaliseras före jämförelsen och är oföränderligt.
Rutnät: x=[−700,−400,0,300,520], y=[−420,−200,0,200,420] lokala meter,
t=[0,300,600,1800] sekunder efter 02:00Z. Vind 4 m/s FRÅN 315° över mark;
ström 0 till 0.2 m/s MOT 90° över mark efter 600 s. Hs 1 m söder om y=0,
1/3 m norr därom; Tm02 5 s, vågor FRÅN 0° över mark. Samma tidigare dokumenterade
komponentinterpolation och luck-/segment-/ankomstkontroller används. Polarens
vattenrelativa vind härleds av modellen, vädergränsen gäller markvind.
Scenarierna weather-limit, unverified och missing-waves är separata frysta
versioner med tidigare definierade avvikelser.

Fram: WGS84 AEQD vid 57.633°N 11.605°E, högst 1.5 km radie och bara den frysta
landtäckningens lat/lon-box. Geodetiska referenstester använder 1000 m och
0.01 m tolerans. Lokala raka färdsegment och lokala nord/östaxlar är en begränsad
plan modell; inte en global geodetisk seglingsmodell. Väderområdet är 1220×840 m.
Utanför dess interpolationsstöd avvisas färden som otillräckligt underlag.

Sökbudget: 26 noder, 1000 expansioner, högst 2 kandidater och 8 mellanvägpunkter,
två avgångar, 30 s integrationssteg, 1800 s/2000 steg per färd. Hela integrerade
segment kontrolleras konservativt mot vädergränser samt land/marginal; det är inte
ett påstående om säkerhet grundat på tät sampling. Kandidatgränsen kan missa
andra omvägar och den verkligt snabbaste/bekvämaste rutten. Geometrisk längd
ordnar sökningen, kompletta tidsatta kandidater jämförs sedan av tidigare motor.

`make land-preview` exporterar separat `frontend/land-dist/vinga.html` med samma
kart-/API-/controllerkomponenter som den syntetiska demonstrationen. Marginalens
kantbredd är en ungefärlig visning vid aktuell kartskala, uppdateras vid zoom
eller ändrad marginal; motorns avståndstest använder lokala meter. OSM-bakgrund
är opt-in och aldrig routingsunderlag. Ingen extern datahämtning sker under
rutt-/avgångsjämförelsen. Lokal granskning: `.venv/bin/python -B -m scripts.local_demo --profile vinga
--port 8766` på ledig port, öppna `http://127.0.0.1:8766/vinga.html`. Servern
binder endast loopback och monterar bara den publika exportkatalogen; API och
HTML/JS testas tillsammans. Ingen aktiv webbrot eller tjänst uppdateras.

Resultat innehåller landversion/källhash, väderversion, projektion, båtmodell,
ankomstkontroll och samlad inputidentitet. `depth_status: unknown`,
`land.completeness: unknown`, `navigational_safety: not_assessed` kvarstår även
vid verifierade modellgränser. GPX är en planerad granskningsrutt med samma
osäkerheter, ODbL-attribution och landidentitet; export nekas om väder/ankomst
inte godkänts. Ingen navigationssäkerhet, djupbaserad passage, tideffekt,
manöver/kryssplanering eller plotterkompatibilitet garanteras.

Djupgående/vertikala datum: [offline acceptanskontrakt](depth-acceptance.md).
Horisontell margin_m är inte marginal under kölen. Ingen djupgate är implementerad.
