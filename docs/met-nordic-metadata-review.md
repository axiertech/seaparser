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
