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
