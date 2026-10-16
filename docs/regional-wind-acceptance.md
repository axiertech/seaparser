# Acceptanskontrakt för regional vind och rumsligt datastöd

Status 2026-10-13: offline design inför framtida MET-kandidatgranskning.
Ingen vindadapter, vindhämtning eller godkänd prognos införs. Faktiska
MET DDS/DAS/tid och ett begränsat koordinatuttag är nu nådda; faktisk
vindimport är fortfarande okvalificerad. Se met-nordic-metadata-review.md. Den tidigare
dokumentationsgranskningen finns i [forecast-blockers.md](forecast-blockers.md);
Lambert-grid, fält och täckning måste verifieras i faktisk källartefakt.

## Vad befintlig motor kan representera

GridProduct i prototype/forecast_data.py kräver minst två strikt stigande
finita öst-/nordkoordinater och minst två UTC-tider. Values är frysta komponenter
ordnade [time][north][east]. Vind är en MOT-vektor i sann öst/nord, m/s,
markrelativ. Saknade noder lagras som None; invalid_cells avser slutna
rum/tid-celler. Ingen extrapolation eller interpolation genom luckor tillåts.

En uppslagspunkt kräver hela 2×2×2-stödet, även hörn med noll interpolationsvikt.
Ogiltiga cellers gemensamma gränser avvisas konservativt. Giltighet är [från,till),
med särskilt stöd för ett integrerat segments slut vid valid_until; separat
ankomstkontroll behåller sin exklusiva tidsgräns.

Segmentstödet prövas vid alla korsade gridplan och mellan dessa i den affina
lokala rum/tid-modellen. Det är ett bevis för den representerade frysta modellen,
inte för okänd native grid-geometri eller producentens upplösning/kvalitet.
Hårda vindgränser kräver dessutom befintlig konservativ segmentcertifiering;
en lyckad punktinterpolation eller stödsegmentkontroll räcker inte.

## Från native koordinater till fryst lokal representation

Källans grid_mapping och koordinataxlar måste läsas, med dokumenterade
projektionsparametrar, geodetiskt datum/ellipsoid, axelordning och enheter.
Ett projektionnamn eller en antagen EPSG-kod räcker inte. Transformering sker i
infrastrukturen med befintligt pyproj-stöd; ingen ny domäntransport införs.

För en framtida direkt representation krävs verifierad separerbarhet i lokala
öst/nordaxlar. Ett transformerat Lambert-grid får inte antas vara rektangulärt
i det lokala AEQD-planet. Källnodernas residualer, cellkanter och stödets
geometriska approximation måste granskas. Copernicus-adapterns nuvarande 1 m
nodtolerans är en avgränsad kontroll för dess lilla lat/lon-uttag; den är inte
automatiskt en accepterad MET-tolerans eller ett helt-cell-bevis.

Om native grid inte kan representeras direkt ska importen avvisas tills en
separat granskad metod finns. Framtida regridding måste ange målgrid, regel,
rumslig felgräns, nod-/cellstöd och hur ursprungliga luckor bevaras genom hela
målcellens rum/tid. Inget sådant metodval eller toleransbeslut fattas här.
Nearest-neighbour, punktprov eller hörnprov får inte automatiskt bli bevis för
hela målcellens stöd eller konservativa vädergränser.

## Vindsemantik och täckning före import

| Kontroll | Nödvändigt bevis | Avvisning |
| --- | --- | --- |
| Produkt | Faktisk forecast-produkt och dokumenterad run-proveniens | Analysis/latest-länk utan fryst identitet |
| Höjd/medel | Faktiska höjd- och cell_methods-attribut med dokumenterad betydelse | Antagen 10 m/medelperiod |
| Riktning | Sann/gridrelativ ram, FRÅN/MOT, nollriktning och vinkelordning | Okänd ram eller riktning |
| Vektorer | Dokumenterad konvertering och vid behov verifierad lokal rotation före interpolation | Gridkomponenter behandlas som sann öst/nord |
| Rumsligt stöd | Native koordinater, CRS, dimensioner, cellstöd och Vinga-området inklusive nödvändiga grannnoder | Deklarerad bbox utan faktiskt interpolationsstöd |
| Tidsstöd | UTC-konvertering med verifierad enhet/kalender, alla planens tidceller | Luckor eller extrapolation bortom sista prognos |
| Saknade värden | Dekodade fill/missing/NaN och källans eventuella giltighetsmask | Ersättning med noll eller närmaste giltiga nod |
| Run | Evidens enligt forecast-run-provenance.md för hela produktuppsättningen | Ifyllda datum eller payloadflag |

FRÅN-riktning konverteras till MOT-komponenter före interpolation. För en
syntetisk referens med sann nord som nollpunkt och medurs vinkel innebär
10 m/s FRÅN norr (east,north)=(0,-10), FRÅN öster=(-10,0).
Sådana referenser verifierar matematiken, inte MET-källans faktiska konvention.
Enhets-/ramsnormalisering måste föregå sammanfogning med marina produkter.

En land-/havsmask är inte automatiskt en vindgiltighetsmask: vind över land kan
ha giltiga modellvärden. Den källspecifika giltighetsmaskens semantik måste
verifieras. Inga våg- eller strömmasker överförs till vindens grid. Maskdata är
inte ett navigerbarhetsbevis.

## Verifieringsmatris och befintliga regressionsbevis

| Referensfall | Förväntat beteende | Befintlig testgrund |
| --- | --- | --- |
| 359°/1° | Interpolation i komponenter utan felaktig 180°-vändning | test_direction_wrap_359_1_for_wind_and_waves |
| Saknat stödhörn eller stängd ogiltig cellgräns | DataUnavailable även vid gräns/nollvikt | test_invalid_cell_and_shared_boundary_cannot_be_bypassed |
| Kort maskad lucka mellan ordinära färdprov | Segment avvisas | test_forecast_segments.py |
| Kort spatial/tidslig vindtopp | Hård gräns får inte hoppas över | test_short_spatial_and_temporal_peaks_missed_by_ordinary_samples |
| Högt hörn utanför själva banan | Osäkert bevis redovisas; ingen säker rutt | test_high_off_path_corner_is_uncertainty_not_observed_exceedance |
| Cellkontroll-/certifieringsbudget nådd | Uttrycklig avvisning; inget tyst bortfall | test_certificate_budget_cannot_silently_drop_box_cells |
| Okänd projektion/rotation eller native-målstöd | Import/routing otillgänglig | Framtida källspecifika referenstester krävs |
| Vind tillagd men marin run okänd | data_unavailable för båda ruttmål | test_dates_and_payload_flags_do_not_certify_run_compatibility |

Befintliga tester är syntetiska eller avser det frysta marina underlaget.
De kvalificerar inte verklig MET-routing. Framtida positiva projektionstester
ska ha oberoende granskade referenskoordinater, rotation och felgränser;
roundtrip genom samma bibliotek ensamt är otillräckligt.

## Native nodrutor och rumtidsstöd 2026-10-16

Befintlig audit_wind_sample redovisar nu native_cell_inventory från samma
hashkontrollerade axlar, tider och finita råvärden. Sju x-noder och åtta y-noder
ger 6×7=42 intilliggande nodrutor. Fem timsteg ger fyra tidsintervall, alltså
168 rumtidsrutor med åtta hörnnoder vardera. Detta räknar rådatas adjacency,
inte producentcertifierade cellpolygoner eller vald interpolation.

Inventeringen redovisar första/sista native x/y i meter och tid i epoksekunder.
Rektangelgränserna följer yttersta noden; inget halvt gridsteg läggs till utanför
uttaget. Inga WGS84-koordinater eller lokala segment projiceras till området.
provider_cell_validity_verified, interpolation_rule_verified och
route_segment_coverage_verified är uttryckligen false. Alla planning_blockers
kvarstår. Ett ogranskat manifestflag kan inte ändra dessa resultat.

Inför nästa implementation krävs separat beslut/granskning av källans
interpolationsregel och giltighetsmask, även vid gemensamma cellgränser och
nollvikter. Landfraktion är inte en vindgiltighetsmask. En lokal rutt måste ha
verifierad datum-/geometribindning för hela transformerade segmentet innan
native nodrutorna kan användas som stödbevis. Analytisk LCC-inversion vid noder
räcker inte till det. Nodrutor får heller inte förlänga tidsstöd efter sista
prognosnoden eller ge fabrikat av saknade värden.

Två nya regressioner kontrollerar kända 42/168 rutor, exakta tids-/y-gränser och
fortsatt okvalificerat resultat, samt att NaN i en uppdaterad fixturekopia
avvisas före komplett inventering. Inga vindvärden normaliseras/importeras.
