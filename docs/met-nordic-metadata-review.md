# Faktisk MET Nordic-metadataåtkomst och kvarvarande importkrav

Verifierat 2026-10-13 under aktivt pass. Auto-review godkände ett avgränsat
sandboxundantag för befintliga probe_forecast_metadata: fasta MET DDS/DAS och
tids-ASCII, samt Copernicus metadata-only listning. Inga vindvärden eller nya
marina väderfiler hämtades. MET:s tre faktiska svar är bevarade i
[metadatafixture](../fixtures/met-nordic-metadata/manifest.json) med SHA-256.

Källfil: [MET fast forecast 2026-10-13 00Z](https://thredds.met.no/thredds/dodsC/metpparchive/2026/10/13/met_forecast_1_0km_nordic_20261013T00Z.nc.dds).
Detta är nu verifierad metadataåtkomst, inte endast en dokumenterad sökväg.
Originala svar återanvänds offline; hämta inte dem igen för samma granskning.

## Faktiskt lästa fält

| Uppgift | Faktiskt innehåll | Gräns för slutsatsen |
| --- | --- | --- |
| Grid | x=1796, y=2321, time=59; latitude/longitude är 2D | Ingen granskad Vinga-cell/täckning utan koordinatvärden |
| Projektion | lambert_conformal_conic, standard_parallel=63,63, lon_0=15, lat_0=63, earth_radius=6371000 m | Sfärmodell; får inte tyst ersättas med WGS84-ellipsoid |
| Gridaxlar | projection_x_coordinate/projection_y_coordinate, enhet m | Axelvärden/ordning/cellstöd ännu inte lästa |
| Vindfart | wind_speed_10m: standard_name=wind_speed, m/s, [time,y,x] | Inga vindvärden lästa |
| Vindriktning | wind_direction_10m: wind_from_direction, degree, [time,y,x] | Kräver fortsatt granskad riktnings-/referenskonvention |
| Höjd/medel | Variabelnamnen innehåller 10m; ingen höjdkoordinat eller cell_methods i dessa svar | Namn räcker inte till verifierad höjd/medelperiodsemantik |
| CF-tid | seconds since 1970-01-01 00:00:00 +00:00; explicit forecast_reference_time | Kalenderattribut saknas i svaret; ingen publiceringstid verifierad |
| Referensvärde | 1791849600 = 2026-10-13T00:00:00Z enligt explicita tidsenheter | Modellreferens, inte issued_at |
| Giltighet | 59 steg med exakt 3600 s intervall, 13 okt 00Z till 15 okt 10Z | Tidsstöd utan rumsligt/vind-/run-förenlighetsbevis |
| Underliggande källa | source=meps; summary anger MEPS och observationsunderlag | Ingen antagen förenlighet med marina modeller |
| Annan referens | NC_GLOBAL meps_forecast_reference_time är textvärdet 1791838800 | Attributets egen enhet/semantik inte verifierad här |
| History | Created 2026-10-13T00:26:17Z | Skapandetid får inte fylla issued_at |

Den tidigare marina inventeringen och detta svar innehåller olika tids-/källbegrepp.
Ingen referenstid ersätter den okända marina utfärdandetiden eller run-ID.
MET:s globala geografiska min/max är deklarerade attribut, inte kontrollerad
regional interpolationsgeometri. land_area_fraction är inte en automatisk
vindgiltighetsmask eller bevis för navigerbarhet.

## Verifiering och nästa avgränsade steg

Fixturehashar/längder är verifierade mot de tre hämtade svaren. ASCII-värdena
lästes som Decimal före Unix-tidskonvertering: 59 heltalssekunder, varje intervall
3600 s, referensvärde 1791849600. Alla fem marina giltighetstimmar 12–16 UTC
finns i tidskoordinaten. Detta bevisar inte kompatibla prognoskörningar.

Nästa steg är ett separat avgränsat koordinatmetadataförsök: native x/y-värden
samt ett litet område med lat/lon-referenser för Vinga-cellstöd. Först därefter
kan projektion, axelordning och lokalt representationsfel bedömas enligt
[regional-wind-acceptance.md](regional-wind-acceptance.md). Inga vindvärden eller
ny adapter bör tas in innan semantik/rumsligt stöd har granskats.

Run-bindning, utfärdandetid och förenlighetsregel följer
[forecast-run-provenance.md](forecast-run-provenance.md). Alla planning_blockers
kvarstår. Manifestets routing_status är data_unavailable och issued_at=null.

Övergripande metadataförsök slutade exit 124 vid 180 s-gränsen under Copernicus-
steget. Ingen marin CSV eller report.json skapades; orsaken inom det steget är
inte verifierad. MET:s tre lyckade svar bevarades och hash-/bytekontrollerades.
Partiell arbetsrapport autonomy/met-source-partial-result-20261013T2205Z.json.
Tolv metadata-probetester passerar; lokala dokumentlänkar kontrollerade.
Tidigare kodcommit 080483b har 265 Python-tester och frontend check godkända.
Ingen kod ändras i denna metadata-/dokumentationsleverans.

## Native koordinatgranskning efter första metadataåtkomsten

Två nya, avgränsade koordinatanrop godkändes av auto-review. Native x/y ASCII
är 43241 bytes och lat/lon för y=509..516, x=692..698 är 2120 bytes (56 noder).
Inga vindvärden ingår. Första lat/lon-anropet med okodade hakparenteser gav
HTTPError; URL-kodad begäran lyckades. Ingen felkod härleds från det första felet.
Svarens exakta adresser/hashar finns i metadatafixturens manifest.

x har 1796 värden från -897442.2 till 897557.8 m; y har 2321 värden från
-1104322 till 1215678 m. Decimal-läsning verifierar exakt 1000 m mellan varje
tryckt koordinat. En första kontroll med binära floats gav en falsk avvikelse
på cirka 6e-11 m; den ersattes med exakt jämförelse av ASCII-decimalerna.

Kandidatindex valdes genom den dokumenterade sfäriska LCC-projektionen av
Vinga-boxens fyra hörn, med grannnoder runt kandidatområdet. Det är urval för
granskning, inte fullständig kvalificering av hela boxens cell-/maskstöd.
Källans subset-x/y matchar samma index i de fulla axlarna.

[geometry-review.json](../fixtures/met-nordic-metadata/geometry-review.json)
redovisar den numeriska granskningen. För alla 56 noder jämfördes källans
lat/lon med invers av faktisk LCC och källans sfärradie. Maximal geodetisk
avvikelse på den sfären är 0.249077 m. Detta är jämförelse mot producentens
separata koordinatfält, inte endast roundtrip genom samma bibliotek. Ingen
ny accepterad projektionstolerans eller datumtransformation beslutas här.

Som separat diagnostik tolkades producentens vinklar i den befintliga lokala
WGS84 AEQD-modellen vid 57.633°N, 11.605°E. Datumekvivalens är inte certifierad.
Samma kolumn varierar upp till 369.477149 m i lokal östposition mellan rader;
samma rad varierar upp till 315.963130 m i nordposition mellan kolumner.
Varje enskild separerbar östaxel måste därför i denna diagnostik ha maximalt
nodfel minst halva kolumnvariationen: 184.738574 m. Värdena får inte passeras
som befintlig Copernicus-adapters 1 m-nodrepresentation.

Det konkreta representationshindret kvarstår: native LCC-grid kan inte direkt
behandlas som motorns separerbara lokala grid. En framtida granskad native-grid-
eller regriddingmetod krävs, med datastöd och konservativa hårdgränser bevarade.
Ingen sådan metod implementeras nu. Höjd/medelperiod, vindmask, utfärdande,
marina run och förenlighetsregel kvarstår också. data_unavailable oförändrat.

## Officiell höjd-/medelperiodsgranskning

Den [officiella MET Nordic-sidan](https://github.com/metno/NWPdocs/wiki/MET-Nordic-dataset#parameters)
kontrollerades mot sparad DAS. Leverantören beskriver båda vindfälten vid 10 m
med 10-minutersmedel; riktningen anger varifrån vinden kommer med norr=0° och
öster=90°. Dokumenterade enheter är m/s respektive grader. Detta stöder
normalisering till MOT-komponenter före interpolation. Ingen faktisk vindimport görs.

[wind-semantics-review.json](../fixtures/met-nordic-metadata/wind-semantics-review.json)
binder den strukturerade granskningen till dokumentets SHA-256 och aktuell DAS-hash.
Den offentliga markdowntexten var 22554 bytes vid läsningen; endast digest och
strukturerad granskning sparas, inte hela dokumentet. Sidan är föränderlig och
hashen ersätter inte en framtida kontroll när källmetoden eller dokumentet ändras.

DAS saknar fortfarande höjdkoordinat och cell_methods. Dokumentationsstöd är
separat från attribut i just payloaden. Det lästa underlaget anger inte explicit
medelfönstrets placering före/efter giltighetstiden eller höjdreferensen i ett
verifierbart koordinatfält. Dessa uppgifter förblir null i granskningen. Inga
tidsbounds eller vertikala metadata fabriceras från text eller variabelnamn.

600 s medelperiod är inte 600 s prognossteg: befintlig tidskoordinat har 3600 s
mellan noder. Medelvind får inte omtolkas som momentan vind, byvind eller maximalt
värde över timintervallet. Produktens prognossteg och mät-/medelsemantik ska
bevaras separat i en framtida källspecifik normalisering.

Alla planeringsblockerare kvarstår, även i MET-manifestet. Denna semantikgranskning
certifierar inte maskat datastöd, lokal regridding, utfärdandetid eller kompatibla
marina körningar. Nästa begränsade oberoende del är ett beviskontrakt för eventuell
regridding mot motorns hårdgränser; metod och tolerans är ännu inte valda.

## Reproducerbar offlineaudit

Kör utan nätverk eller nya nedladdningar:

```bash
.venv/bin/python -B -m scripts.audit_met_metadata fixtures/met-nordic-metadata
```

Verktyget läser endast det granskade femfilsformatet, med 512 KB-budget per fil,
kontrollerar hash/byteantal, Decimal-axelsteg, tidssteg och subsetkartornas bindning
till native axlar. Det reproducerar jämförelsen mot de 56 producentnoderna och
lokal separerbarhetsdiagnostik. Det är ingen generell DAP-parser eller vindadapter.
JSON skrivs till stdout; fixtures ändras inte. Scope/routing_status anger alltid
diagnostik/data_unavailable och issued_at förblir null, oberoende av manifestflaggor.
Funktionens granskade projektion och lokala origo är explicita, inte antagna
utifrån en godtycklig fil. Andra projektioner kräver ny granskning.

Offlineauditens tidskontroll binder nu DDS/ASCII-deklarationerna till 59 värden,
vindfältens DDS-dimensioner till 59×2321×1796 och DAS-tidsattribut till de
faktiskt observerade UTC-sekundenheterna och standardnamnen. Den kräver en
entydig skalär ASCII-modellreferens och redovisar 1791849600 epoch-sekunder
(2026-10-13 00:00 UTC) separat som model_reference_not_issuance. Frånvarande
calendar-attribut redovisas som null; ingen kalender eller utfärdandetid fylls i.
Detta är strikt verifiering av den frysta granskade layouten, inte en generell
DAP-parser eller bevis att separata nätverkssvar härrör från samma körning.
Hashar identifierar sparade svar; modellreferensen kvalificerar inte marin
run-förenlighet. Ändrade tidsenheter, dimensioner, saknad/dubbel referens och
ändrat referensvärde avvisas även med uppdaterat manifest.

## Separat faktisk native vindsubset

2026-10-13 under aktivt pass nåddes ett nytt budgetbegränsat vind-/landuttag
från samma fasta MET-fil. Detta är råvärdesgranskning, skild från tidigare
metadataåtkomst: time-index 12–16 (12–16 UTC), y=509–516 och x=692–698,
56 noder och fem timmar. Svaret innehåller 280 vindfarter, 280 från-riktningar,
56 landfraktioner och skalär modellreferens. Befintliga metadata/koordinater
och marina data återhämtades inte. Fasta URL, byteantal, SHA-256, observationstid,
subset och attribution finns i fixtures/met-nordic-wind-sample/manifest.json.

Transport: ett av auto-review godkänt läsanrop, 15 s timeout, 128000 byte tak,
befintlig redirect-spärr och yttre 25 s processgräns. Faktiskt svar 7604 byte,
SHA-256 52ca1126d058bd98bdee8107b865c2e454fc192e524f41ffa6204c4f5123504d.
Originala ASCII-svaret sparas och ska återanvändas offline.

Auditens nya --wind-sample-kontroll binder alla produktkartor till sparade
native axlar och båda vindprodukternas fem tider till sparad giltighet.
Referensvärdet stämmer med den tidigare modellreferensen; det är fortfarande
inte utfärdandetid eller bevis för korsprodukt-run-förenlighet. Exakta råtal:
fart 11.273894–17.250252 m/s, från-riktning 142–160 grader; landfraktion
0–0.94 med 21 icke-noll noder. Alla 616 värden är finita i detta lilla uttag.
Ingen vektornormalisering, cellmask, regridding eller regional adapter införs.
Landfraktion är inte vindgiltighetsmask och bevisar inte navigerbarhet.

Reproducerbar offlinekontroll:

```bash
.venv/bin/python -B -m scripts.audit_met_metadata fixtures/met-nordic-metadata --wind-sample fixtures/met-nordic-wind-sample
```

review.json återger diagnostiken. issued_at=null, data_unavailable och samtliga
planeringsspärrar kvarstår, även om manifestet förses med datum eller flaggor.

## Felgränser i offlineverktyget

Läsgränsen måste vara ett positivt heltal högst 512000 byte. Vindråsvaret
läser högst 128001 byte och avvisar den extra byten; manifestet kan inte öka
budgeten. Metadata-/vindmanifest måste ha granskad struktur, källfilernas
byteantal/hash och komplett koordinatsubset. Felaktiga tal, NaN/Infinity,
token längre än 64 tecken och absoluta Decimal-exponenter över 64 avvisas.
Dessa talgränser är bearbetningsbudgeter för det frysta formatet, inte
meteorologiska toleranser, avrundning eller nya giltighetsantaganden.

Vid fil-, teckenkodnings- eller valideringsfel skriver CLI ett JSON-svar med
scope=offline_audit_failed, routing_status=data_unavailable, issued_at=null
och endast felklass, och avslutar med exit 1. Rådata och filvägar återges inte
i felrapporten. Inget partiellt lyckat svar skrivs. Giltig fixturediagnostik
är oförändrad och kvalificerar fortfarande ingen routing.

## Koordinattalens utbredning mot marina fixtures

Valfri --marine-directory komponerar befintlig MET-/vindgranskning med
befintlig Copernicus-audit av de tre sparade NetCDF-filerna. Ingen ny decoder
eller adapter införs. Före NetCDF-auditen begränsas varje fil till 512000 byte;
manifeststruktur och samtliga råhashar kontrolleras. Koordinater läses från
faktiska NetCDF, inte en payload med deklarerade källhashar.

MET:s 56 producentnoder har numeriska extremer latitud 57.60443–57.669865 och
longitud 11.558033–11.664452. De fyra våg- och fyra strömnoderna ligger inom
dessa talintervall. Marina grid är inte identiska: våglatituder
57.62477111816406/57.64143753051758, strömlatituder
57.62488555908203/57.64155197143555; även longituderna skiljer sig.
Ingen rumslig interpolation, datumbindning, måltransformation eller masköverföring
görs. En lat/lon-box är inte den transformerade native-cellens utsträckning,
och en nodjämförelse bevisar inte hela celler/segment eller att sfäriska och
marina geografiska referenser är förenliga.

Rapporten anger scope=coordinate_number_extents_not_spatial_coverage_proof,
datum_equivalence_verified=false och whole_cell_coverage_verified=false.
Dessa false betyder overifierat, inte bevisad oförenlighet. Alla nio källhashar
binds separat; inga antagna gemensamma körningar. Utfärdande förblir null,
data_unavailable och blockerare från båda befintliga auditer kvarstår.

Kör offline:

```bash
.venv/bin/python -B -m scripts.audit_met_metadata fixtures/met-nordic-metadata --wind-sample fixtures/met-nordic-wind-sample --marine-directory fixtures/vinga-copernicus
```

## Strikt DAS-fältsemantik 2026-10-16

Befintlig offlineaudit kräver nu exakt de granskade attributuppsättningarna
för wind_speed_10m, wind_direction_10m och land_area_fraction i faktisk DAS.
Enheter är m/s, degree respektive 1; standardnamn är wind_speed,
wind_from_direction respektive land_area_fraction. coordinates måste vara
longitude latitude och grid_mapping måste vara projection_lcc. Befintliga
UInt32 _ChunkSizes för vind bevaras som del av den fasta källstrukturen.

Varje block och attribut måste vara entydigt. Ändrad typ, saknad/dubbel
uppgift eller ytterligare ogranskad semantik avvisas även när testmanifestets
hash uppdateras. Nya scale_factor, add_offset, _FillValue, missing_value och
cell_methods får inte tyst ändra hur de sparade ASCII-värdena tolkas.
Detta är ett snävt kontrakt för vårt frysta uttag, ingen allmän DAP-parser;
en ändrad producentstruktur kräver ny explicit granskning.

Fyra negativa testmatriser visar avvisning av ändrade enheter, FRÅN/MOT,
byvind/medelvind, maskbetydelse, CRS-/koordinatlänkar och attributambiguitet.
Felaktig källsemantik avvisas före läsning av vindvärden. Före rättningen
accepterades flera sådana ändringar med uppdaterad hash. Samtliga 34 riktade
MET-tester passerar efter rättningen. Regionalrapporten för originalfixturen
är exakt oförändrad, inklusive samtliga nio källhashar och planeringsspärrar.
Ingen höjd, medelfönsterplacering, giltighetsmask, datumekvivalens eller
utfärdandetid fabriceras. data_unavailable kvarstår.

## Konsistent källgeometri 2026-10-16

Samma strikta attributläsning används nu för x, y, latitude, longitude och
projection_lcc. Native axlar kräver meter och rätt projection_x/y_coordinate;
geografiska fält kräver sparade degree_north/east och rätt standardnamn samt
koppling till projection_lcc. Det namngivna projektionsblocket måste samtidigt
innehålla granskad proj4, lambert_conformal_conic, båda standardparallellerna
63, centralmeridian 15, origo 63 och sfärradie 6371000 m, med granskade typer
samt rårepresentation. Motstridiga/extra ellipsoid- eller offsetfält avvisas.

Tidigare räckte förekomst av proj4-strängen någonstans i DAS. Fyra negativa
testmatriser visade femton accepterade motsägelser innan rättningen, inklusive
ett omdöpt projektionsblock. Efter rättningen passerar alla 38 riktade MET-tester.
Originalets regionalrapport och nio hashbindningar är exakt oförändrade.
Kontrollen tolkar inte sfären som WGS84 och häver ingen geometri-, vindram-,
mask-, utfärdande- eller run-spärr. Detta är fortsatt fryst källgranskning,
inte en generell CF-parser eller en kvalificerad ruttprognos.

## Samma kontrollerade metadata vid materialisering 2026-10-16

read_wind_sample använder nu de källtexter som den interna metadataauditen
redan läst med bytebudget, hashkontroll och semantikkontroll. Native axlar och
tidskoordinater öppnas inte på nytt efter den kontrollen. Det publika audit-
resultatet är oförändrat; källtexterna följer inte med i rapport/export.
Detta är per-fils hashbindning till lästa bytes, ingen atomisk filsystemsnapshot
eller run-certifiering av flera produkter.

Tre regressioner använder enbart temporära fixturekopior. Samordnad ändring
av metadataaxel respektive giltighetstid och vindfilens kartlänkar efter
metadataaudit avvisas, även när vindmanifestets hash räknas om. Före rättningen
kunde de ändrade koordinaterna materialiseras med den gamla metadatahashen.
Borttagning av redan kontrollerade koordinatfiler påverkar inte resultatet
under samma inläsning; originalets kontrollerade bytes används i minnet.
Alla 41 riktade MET-tester passerar. Originalets regionalrapport och nio
hashbindningar är exakt oförändrade; samtliga prognosspärrar kvarstår.

## Koordinatprecision: ASCII och deklarerad Float32 2026-10-16

Källans DDS deklarerar Float32 för x/y. Befintlig parser bevarar de sparade
ASCII-talen som exakta Decimal. En separat offlinekontroll avrundar dessa tal
till IEEE binary32 via standardbibliotekets struct och jämför exakt med
Fraction. Den återvinner inte ursprungliga producentbytes och ändrar inga axlar.

| Område/axel | Max absolut skillnad ASCII till diagnostisk binary32 | Diagnostiska grannsteg |
| --- | --- | --- |
| Full x, 1796 noder | 1/80 m = 0,0125 m | min 999,984375 m, max 1000,015625 m |
| Vindsubset x, 7 noder | 1/320 m = 0,003125 m | 1000 m |
| Full y och vindsubset y | 0 m | 1000 m |

I vindsubsetet är binary32-minus-ASCII för varje x exakt -1/320 m.
Originalets ASCII-x-steg är fortsatt exakt 1000 m. Att Float32-avrundning av
hela axeln ger något varierande steg är ingen instruktion att byta geometri
eller acceptera avvikelse i befintlig kontroll. Diagnostiken beskriver bara två
representationer av samma sparade decimaltal.

Två regressioner verifierar de kända rationella skillnaderna, DDS-typerna och
att regionala NativeWindSample fortfarande innehåller samma Decimal-axlar och
källhash. Float64 används endast som mellanrepresentation vid struct-packning;
resultatet är här en numerisk kontroll av de sparade ändliga talen, ingen
generell algoritm för exakt Decimal-till-binary32 eller DAP-serialisering.

Utan verifierad serialiseringsregel eller ursprungliga binära koordinatbytes
är skillnaden inte en säker felgräns för den verkliga producentaxeln. Den
bevisar heller ingen WGS84-likvärdighet, ruttmarginal eller celltäckning.
Ingen routingtolerans väljs; alla planning_blockers/data_unavailable kvarstår.

## Strikt tidsmetadata före vindvärden 2026-10-16

Offline-regression i fixturekopior med uppdaterade hashvärden visade att den
äldre tidsparsern accepterade tillagda scale_factor/add_offset/missing-/bounds-
attribut och ändrad chunkmetadata. Den kontrollerade endast utvalda namn och
kalenderfrånvaro. Korrekt hash är identitet, inte bevis om oförändrad semantik.

Båda blocken time och forecast_reference_time använder nu samma strikt granskade
attributparser som vind/geometri. Exakt units/standard_name krävs och endast
time får den befintliga UInt32 _ChunkSizes 512. Saknade, dubbla, omtypade,
ändrade och extra deklarationer avvisas; framtida legitim metadata kräver separat
granskning innan parsern utvidgas. Detta är avsiktligt ett kontrakt för den
frysta källlayouten, ingen generell DAP-parser.

Två nya testmetoder prövar 12 semantiktillägg över de två tidsblocken före
vindvärdes-I/O samt tre chunkförändringar. Före rättning gick de förra vidare
till en avsiktligt saknad vindfil och de senare avvisades inte. Efter rättning
avvisas alla i tidsgranskningen. Oförändrade råfixtures läses fortsatt korrekt.
Ingen utfärdandetid fylls i, inga tidsgränser uppfinns och alla planning_blockers
kvarstår. Ingen ny vind-/marinhämtning, adapter eller publik ändring.

## Manifestidentitet utan dubbla JSON-nycklar 2026-10-16

Fyra negativa offlinefall visade att tidigare json.loads accepterade motsägande
dubbla nycklar genom att behålla sista värdet. Metadata-manifestets schema och
en filposts sha256 samt vindmanifestets sha256 och nästlade subset.x_first
kunde då vara tvetydiga även när sista värdet stämde med råbytes.

Gemensam read_manifest för de två befintliga MET-läsningarna använder nu
object_pairs_hook och avvisar varje duplicerad nyckel, även i nästlade objekt.
Felltexten är fast och återger inga källnycklar/värden. Befintlig bytebudget,
form-/hash-/dimension-/semantikvalidering återanvänds; ingen ny adapter skapas.
Dubblettfri JSON är inte producentautenticitet eller run-förenlighetsbevis.
Manifestets ifyllda issued_at/routing_status/blockers ger fortfarande ingen
kvalificering och får inte ändra data_unavailable. Råfixtures förblir orörda.

Två nya testmetoder med fyra subfall misslyckades före rättning och passerar
efteråt. 30 riktade manifest-/metadata-/vind-/budgettester passerar.
Källidentitet/semantik hämtas fortsatt ur samma hashkontrollerade bytebilder;
inga källdata eller officiella körtider har hämtats eller hittats i denna del.
