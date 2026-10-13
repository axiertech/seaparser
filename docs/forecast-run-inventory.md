# Offlineinventering av det frysta marina uttaget

Verifierat 2026-10-13 under aktivt pass i /tmp/seaparser-real-map-data.
Underlag: tre befintliga NetCDF-filer i fixtures/vinga-copernicus, öppnade
skrivskyddat med xarray och decode_times=False efter hashkontroll mot manifestet.
Inga nya marina data hämtades. Resultatets omfattning är dessa lokala filer,
inte vilka metadata som finns hos producenten eller i originalfilerna.

Maskinläsbar evidens: [run-metadata-inventory.json](../fixtures/vinga-copernicus/run-metadata-inventory.json).
Den innehåller dimensioner, variabelnamn, globala attributnamn, ett begränsat
urval offentliga källattribut samt råa tidskoordinater/enheter/kalendrar.
Kontaktvärden, full history och andra irrelevanta attributvärden ingår inte.
Ingen datumtolkning av creation_date eller run-certifiering görs.

## Faktiskt återfunna metadata

| Fält | waves.nc | current.nc | wave-mask.nc |
| --- | --- | --- | --- |
| Dimensioner | time=5, latitude=2, longitude=2 | time=5, depth=1, latitude=2, longitude=2 | latitude=2, longitude=2 |
| Prognos-/maskvariabler | VHM0, VMDR, VTM02 | uo, vo | deptho, mask |
| time standard_name | time | time | Ingen tidsvariabel |
| Rå tidsenhet | seconds since 1970-01-01 | days since 1900-01-01 | Ej tillämpligt |
| Kalender | standard | proleptic_gregorian | Ej tillämpligt |
| source | FMI-WAM_CMEMS | CMEMS BAL MFC NEMO model output converted to NetCDF | Attributet saknas |
| creation_date | Attributet saknas | 2024-11-25 17:05:11 | Attributet saknas |
| forecast_reference_time-variabel | Saknas | Saknas | Saknas |
| Globalt forecast_reference_time/analysis_time/model_run/run_id | Saknas | Saknas | Saknas |

Strömfilens creation_date är ett faktiskt attributvärde med okänd betydelse i
detta uttag. Det är inte en verifierad utfärdandetid; varken den eller filens
katalogversion används som modellrun. Källans source-/institution-strängar
identifierar allmän producent/modellfamilj men inte en viss körning/revision.

Alla variablers attribut genomsöktes även efter forecast_reference, run_id,
model_run, issu och analysis_time: inga träffar. Den sökningen är en ledtråd,
inte ett generellt bevis om andra producentfält eller andra filformat.

Befintlig audit verifierar de normaliserade giltighetstiderna 2026-10-13
12–16 UTC och komponenter/grid. Inventeringen bevarar rå tidsrepresentation:
ström och vågor har olika epoker och kalendrar. Samma normaliserade timsteg
är fortsatt inte bevis för kompatibla prognoskörningar.

## Evidensgap mot granskningskontraktet

| Krav i kontraktet | Resultat för befintligt uttag | Fortsatt nödvändigt bevis |
| --- | --- | --- |
| Filidentitet | Alla tre SHA-256 matchar manifestet | Ingen ytterligare nedladdning behövs för hashkontroll |
| Produktidentitet/transport | Dataset/version/del/service/variabler finns i manifestet | Transportproveniens certifierar inte run |
| Modellreferenstid | Inget explicit granskat fält i dessa filer | Äkta källmetadata och dokumenterad fältsemantik |
| Utfärdande/publicering | Okänt; creation_date får inte ersätta värdet | Separat verifierad källspecifik definition och metadata |
| Run/revision per tid/variabel | Okänd | Granskad historisk bindning till respektive originalrun |
| ARCO-urval | Inget bindningsbevis i inventerat underlag | Producent-/tjänstevidens för exakt redan hämtat uttag |
| Regional vind | Ingen vindprodukt i de tre filerna | Faktisk MET-kandidatgranskning och fryst regionalt stöd |
| Förenlighet | Ingen certifiering | Versionsbunden regel för hela produktuppsättningen |
| Strömmask/geometri | Inventeringen kvalificerar inte routingstöd | Separat native-mask-/transformations-/segmentverifiering |

Resultat: data_unavailable. ProductMetadata.issued_at förblir null för de
befintliga dynamiska produkterna och alla planning_blockers kvarstår.

## Identifierad framtida semantikfråga

scripts/audit_copernicus.py letar efter standard_name=forecast_reference_time
och skulle lägga ett ensamt dekodat värde i rapportens issued_at.
scripts/freeze_copernicus_reference.py för vidare detta fält. Nuvarande fixtures
har inget sådant fält, så resultatet är null och denna inventering ändrar inga
filer med vädervärden eller adapterbeteenden.

Före framtida certifiering måste rapport-/importkontraktet skilja modellreferens
från produktens publicering/utfärdande enligt
[forecast-run-provenance.md](forecast-run-provenance.md). Ett positivt syntetiskt
CF-test av dekodning skulle inte ensamt verifiera producentens betydelse.
Detta är ett dokumenterat kodgranskningsfynd, inte en verifierad källuppgift.
