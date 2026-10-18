# Regional landgeometri och uttryckliga reservvärden

Grundkomponenter för Vinga–Uddevalla, ännu inte en aktiverad regional färdmodell.
De tio överlämnade filerna har granskats och färdigställts utan nya datauttag.
Befintliga prognos- och GPX-flöden ändras först när kompositionen är verifierad.

`scripts.build_coastal_water` använder OSM-kustens riktning (land till vänster).
Öppna kedjor nodas mot den faktiska uttagsgränsen; ingen rak inlandskord läggs
till. Inre lösa ändar, ogiltig topologi och ofullständig partition stoppar bygget.
Topologin snäpps till 0,1 mm, följt av en konservativ 1 mm vattenerosion.
`CoastalWater` kontrollerar hela slutna affina segment och marginal mot alla
vattenkanter. Det är ett uppskattat landhinder, utan kvalificerade djup,
landfullständighet eller navigerbarhet. ODbL-attribution bevaras.

Den bevarade bunten `/home/web/seaparser/data/vinga-uddevalla-20261018` innehåller
51 758 883 byte OSM-källa, 585 179 noder och 12 001 kustvägar. Materialiserat
vatten har sex vattenytor och 8 585 landytor, utan lösa ändar eller topologisnitt.
Käll-SHA256: `ffabbf8c6fdf537b651b033190dde341b16d5694db1a29824a28cfe87f08c2e7`.
Vatten-SHA256: `6a938adf7cf3b26e82b7f361e230abf2b28302cc85ccdd328cf294015e379fe8`.
Byggskriptet återanvänder befintligt hashkontrollerat WKB i stället för att skriva
över det. Buntens cirka 67 MiB återanvänds; inga identiska uttag har gjorts.

`prototype.water_routing` är en deterministisk, budgetbegränsad A*-sökning med
åtta grannar och kontrollerad siktutjämning. Geometrin tillförs som rena funktioner.
Varje kant kontrolleras med samma landmodell; gränser för celler, expansioner,
kandidater och vägpunkter redovisas. Ändpunkter utanför sökområdet avvisas.
Detta är kandidatgenerering, utan väderkostnad, färdtid eller global optimalitet.
Den tidigare sparade 250 m-kandidaten har 32 mellanvägpunkter, cirka 88,96 km
geometrisk längd och uppmätt söktid 26,84 s. Den är inte en simulerad färd.

`MarineReserve` tar redan normaliserade komponenter från befintliga
`wave_node`/`current_node`; ingen andra Copernicus-adapter införs. Först prövas
full bilinjär rumslig och linjär tidsinterpolation på produktens egna noder.
Alla stödnoder måste ha raka kontrollerade vattenförbindelser till provpunkten.
Vid saknat stöd krävs en explicit `ReservePolicy` för varje variabel:

- `method`: `none` eller `nearest_valid_water`.
- `max_distance_m`: högst tillåtet källavstånd i Vinga-AEQD, standard 20 000 m.
- `max_time_offset_seconds`: högst absolut källtidsavvikelse, standard 21 600 s.
- `time_weight_m_per_second`: avstånds-/tidsrangordning, standard 1 m/s.

Rangordningen minimerar avstånd + absolut tidsavvikelse gånger tidsvikten bland
tillåtna, synliga vattennoder. Exakta likheter får stabil källordning. Ett helt
produktvärde hämtas från samma nod och tid: samtliga variabelpolicyer måste
uppfyllas, med minsta avstånds-/tidsgräns och största tidsvikt. Strömkomponenter
och våghöjd/period/riktning blandas alltså inte från olika reservkällor.
Normal interpolation av vågriktning sker fortsatt med riktningskomponenter.

Reservvärden har metod `nearest_valid_visible_water` och osäkerhet `high`.
Varje variabel registrerar källposition, källtid, källvärde, avstånd och signerad
tidsavvikelse. Verkliga nollor bevaras; inga saknade värden ersätts med noll.
Oändliga och fysiskt ogiltiga källvärden avvisas även när en annan komponent
saknas. Metoden utfärdar inga vädergränscertifikat. `NativeWindWithReserve`
behåller befintlig MET-native-interpolation och räknar reservnodernas positioner
från exakt samma native-axlar som värdena. Vindens källmask och andra okvalificerade
källuppgifter måste fortsatt redovisas separat vid komposition.

## Faktiska prov 2026-10-18

De redan hämtade marina noderna normaliserades med befintliga fältfunktioner.
Vid avgång 09 UTC finns landfria reservförbindelser vid båda ändpunkterna:

| Punkt | Produkt | Källposition lon/lat | Avstånd | Tidsavvikelse |
|---|---|---|---:|---:|
| Vinga | Ström | 11,624906 / 57,624886 | 1 150 m | 0 s |
| Vinga | Vågor | 11,624926 / 57,624771 | 1 161 m | 0 s |
| Uddevalla | Ström | 11,902682 / 58,341541 | 530 m | 0 s |
| Uddevalla | Vågor | 11,902696 / 58,341408 | 516 m | 0 s |

Ett tätare stödprov längs den sparade geometrikandidaten använder högst 250 m
mellan provpunkterna och idealiserad 5 kn-tid utan ström, enbart för att finna
dataluckor. Detta är ingen färdsimulering eller accepterad restid. För både
ström och vågor saknar 25 provpunkter en tillåten rak vattenförbindelse, bland
annat på kandidatens elfte segment. Större radie eller samma vattenkomponent
är inte tillräckligt när förbindelsen korsar en udde.

Nästa funktionssteg är uttryckligt konfigurerad reservförbindelse som följer
kontrollerat sammanhängande vatten, med spårbar väg och vattenavstånd. Därefter
kopplas samma normalisering och befintliga färdmotor samman, med regional
rörelseram, hela-segment-kontroller, per-segment-proveniens och särskild
uppskattningsstatus i karta, jämförelse och GPX. Källmetadata och antagna
modelluppgifter får inte slås samman. Fram till dess förblir den publicerade
regionala förkontrollen blockerad och skapar ingen GPX.

Shapely 2.2.0 och dess CPython 3.14 Linux-hjulhash har verifierats mot officiella
PyPI. Låset kräver inga systempaket eller globala installationer. Riktade
regressioner prövar kända landbarriärer, marginalkontakt, verkliga nollor,
tidsavvikelser, cirkulär vågriktning, ogiltiga källvärden och deterministiska
sökgränser. Första passets lås-/syntax-/fulltest- och exakta CI-resultat förs i
arbetsloggen och överlämningen efter körning.
