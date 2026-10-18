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

Den första begränsade metoden ovan har nu kompletterats med vattenvägar enligt
följande avsnitt. Nästa funktionssteg kopplar samma normalisering och befintliga färdmotor samman, med regional
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

## Kontrollerade reservvägar runt uddar

`nearest_valid_water_path` är ett uttryckligt val per variabel, med versionerad
konfiguration i `settings/vinga-uddevalla-reserve.json`. Där tillåts metoden för
ström och vågor; vindreserv är uttryckligen avstängd. Native-vindinterpolation
ändras inte. `configured_reserve_policies` validerar samtliga variabelval innan
uppslag och ger oföränderliga policykartor, utan filåtkomst under beräkning.

En rak kontrollerad vattenförbindelse används när den finns. Annars krävs samma
vattenkomponent och en konkret väg från den befintliga rena kandidatgeneratorn.
Varje delsegment kontrolleras mot hela landmodellen och vald reservmarginal.
Att punkterna tillhör samma vattenkomponent tillåter aldrig en genväg över land.
Den nya metoden tillför inga noder eller värden i prognosfältet.

Vattenvägens längd måste rymmas inom `max_distance_m`, utöver källtidsgränsen.
Alla möjliga förbindelser inom denna längd ryms i sökfyrkanten kring ändpunkternas
mittpunkt med samma sidlängd som avståndsbudgeten. För själva sökningen finns
explicit gridsteg, celltak, expansionstak, källförsökstak och marginal. Första
regionala inställningen är 250 m, 30 000 celler, 10 000 expansioner, högst 16
källförsök som behöver en omväg och 0 m särskild reservmarginal. Kustmodellens
konservativa grundskydd finns kvar. Båtens landmarginal är separat och är ännu
inte kopplad till en regional färdsimulering.

Produktens gemensamma policy använder minsta avstånds-/tids-/sökbudget, finaste
begärda gridsteg, största tidsvikt och största marginal. En variabel som kräver
rak synlighet kan inte få omväg genom en annan variabels inställning. Avstängd
reserv blockerar hela produktens reservuppslag. En begränsad geometri-LRU delar
exakta redan kontrollerade segment mellan uppslag; den är ingen beständig cache.

Proveniensen anger `distance_m` längs den funna vattenvägen och dessutom
`direct_distance_m`, förbindelsens WGS84-vägpunkter, expansioner, gridsteg och
`source_search_truncated` när budget eller ofullständig anslutningssökning berör
källvalet. Källposition, källtid, källvärde, signerad tidsavvikelse och hög
osäkerhet finns kvar för varje variabel. Rangordningen jämför funna förbindelser;
den bevisar varken kortast vattenavstånd eller globalt närmaste användbara källa.
Tömda budgetar ger aldrig påhittade värden eller bevis om omöjlig färd.

Det återupprepade verkliga stödprovet med denna konfiguration har 410
geometriska provpunkter och båda marina produkter, totalt 820 uppslag. Samtliga
har stöd; de tidigare 25 luckorna per produkt är borta i detta prov. Det ger
1 913 reservposter, varav 517 med kontrollerade vattenvägar, fördelade på 206
produktuppslag. Alla återtransformerade förbindelsesegment kontrollerades
separat mot vattengeometrin och deras summerade längd mot rapporterat avstånd
(0,1 mm numerisk tolerans). Största använda vattenavstånd var 4 273,42 m,
största raka avstånd 4 060,54 m och största absoluta tidsavvikelse 1 798,88 s.
78 variabelposter anger begränsad källsökning; osäkerheten döljs inte.

Första kalla stödprovet tog 22,49 s inklusive normalisering/inläsning.
Omprovet med extra förbindelsekontroll tog 14,77 s på samma maskin; detta är
ingen generell latensgaranti. Källor och data återanvändes helt. Underlaget
fortsätter att vara ett stödprov vid idealiserad tid, utan färd-, ankomst-,
vädergräns- eller GPX-kvalificering. Den integrerade färdens faktiskt uppslagna
tider, landmarginaler och segment måste kontrolleras i nästa komposition.
