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
