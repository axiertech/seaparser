# Avgränsad diagnostik av Copernicus metadataflöde

Verifierat 2026-10-13 i aktivt pass med installerad Toolbox 2.5.0.
Tidigare metadata-only get-försök nådde tidsgränsen för vågor/ström utan CSV.
Separata, auto-review-godkända steg har nu prövats utan väderhämtning.
Inga paket-, system-, autentiseringsfil- eller privata konfigurationsändringar.

| Separat steg | Faktiskt resultat | Vad det inte bevisar |
| --- | --- | --- |
| get_config_and_check_version_get(False) | Exit 0, en katalog, anrop cirka 0.12 s | Inte run-identitet eller att alla tjänster är åtkomliga |
| get_dataset_metadata för vågor | Exit 0, två katalogversioner, låst 202311 finns, anrop cirka 0.32 s | Ingen original-fillista, run- eller utfärdandeverifiering |
| Validering av redan sparad autentisering | Exit 124 vid 25 s; checkpoint saved_auth_validation | Inte ogiltiga credentials eller verifierad felorsak på servern |

Delrapporter och externa exitkvitton finns under autonomy/:
marine-config-stage-20261013T2220Z, marine-catalogue-stage-20261013T2221Z och
marine-auth-stage-20261013T2222Z. Samlat kvitto med rapport-/granskade bibliotekshashar:
marine-stage-diagnostics-20261013T2223Z.json. Katalognamnen är ID, inte modellrun.

Bibliotekets lästa implementation visar att Python-get först skapar GetRequest.
create_get_request anropar get_and_check_username_password före get_function,
vars senare steg är versionskonfiguration, dataset-/serviceval och fillistning.
Det ger en konkret förklaring att undersöka: autentiseringsvalideringen kan
fördröja metadata-get innan katalog eller S3-listning nås. Detta är en inferens
från kodordning och det separata försöket, inte en spårning av de tidigare
fullständiga get-anropens interna förlopp.

Det separata autentiseringsförsöket använde Toolboxens ordinarie funktion och
redan sparade uppgifter. Användarnamn, lösenord, token, privata adresser och
bibliotekets felmeddelanden ingår inte i rapporten; bara steg, status och tider.
Ingen interaktiv inloggning eller lösenordsåterställning gjordes. Den kvarvarande
in_progress-rapporten är en checkpoint; verifierad extern exit 124 innebär att
försöket avslutats utan slutresultat. Den ska inte beskrivas som fortsatt aktivitet.

Ingen autentiseringskontroll kringgås och ingen annan identitet används för
originaltjänsten. Snabb offentlig katalogåtkomst får inte användas som bevis att
autentisering lyckats. Vid framtida försök ska saved-auth-validering ha en egen
kontrollerad tidsbudget och inga credentialvärden loggas. Upprepa inte hela
fillistningen innan ny åtkomstevidens motiverar det.

Alla planning_blockers kvarstår. Katalogversion är fortsatt inget modellutfärdande;
issued_at/run-ID/förenlighet är okända och planering ger data_unavailable.
Befintliga marina data och MET-metadata återanvänds utan nya uttag i diagnostiken.
Nästa oberoende tillåtna arbete är MET-vindens höjd/medelperiod från faktisk
officiell dokumentation eller offline kontraktsverifiering mot sparade metadata.

## Ny åtkomstevidens 2026-10-16

Ordinarie saved-auth-validering med befintlig Toolbox 2.5.0 gav exit 0 på
cirka 2,18 s inom separat 25 s-budget. Inga authvärden eller biblioteksutskrifter
loggades; ingen authfil eller privat konfiguration ändrades. Den tidigare
25 s-timeouten från 2026-10-13 gäller det historiska försöket, inte dagens åtkomst.
Kvitton: autonomy/marine-auth-recheck-20261016.json och motsvarande
marine-auth-recheck-execution-20261016.json.

Därefter kördes befintlig list_marine_metadata separat för waves och current,
med create_file_list+dry_run, fixerade dataset/versioner, datumfilter 20261013
och 60 s-gräns. Endast CSV-filer skapades; inga NetCDF-väderfiler hämtades.
Båda processer slutfördes på cirka fyra sekunder. Ursprungliga rapporter gav
exit 2/blocked eftersom vår validator krävde enbart siffror i storlekskolumnen.
Faktiska Toolbox-svar hade heltalsstorlekar med decimalsuffix .0.

Validatorn accepterar nu exakt icke-negativa integrala decimaltoken, såsom
112961233.0, utan flyttalskonvertering. Bråk, negativa tal, NaN, Infinity och
exponentnotation avvisas. Lokalt granskad Toolbox-skrivare serialiserar
s3_file.size direkt till CSV. Ingen generell tids-/run-tolkning tillkommer.

De två befintliga CSV-filerna återvaliderades offline genom samma funktion,
med transport ersatt av lokal kopiering. Ursprungliga försöksrapporter lämnas
oförändrade; separat marine-list-offline-review-20261016.json anger resultatet.

| Produkt | Bytes / SHA-256 | Faktiskt listade basnamn |
| --- | --- | --- |
| waves | 478 / d14f5238ad0d3c61b3753b3060408c23e89a42975cd20ffa1ed8ae5c58d16be4 | BAL-WAM_WAV2026101300.nc; BAL-WAM_WAV2026101312.nc |
| current | 482 / bfb6e262c7cd00cda9b83e2e3b0cebe7c448de24b386ba472ec323224e47e188 | BAL-NEMO_PHY-2026101300.nc; BAL-NEMO_PHY-2026101312.nc |

CSV och externa exitkvitton finns under autonomy/marine-list-recheck-
{waves,current}-20261016/. Offlinegranskningen verifierar två poster per produkt.
Filnamn är kandidatreferenser, inte verifierade run-ID:n eller faktisk
utfärdandetid. size/last_modified/etag binder inte historiska ARCO-värden
till originalfilen. Ingen ny källkoppling eller förenlighetsregel har bevisats;
alla planning_blockers/data_unavailable kvarstår. Ingen ny hämtning gjordes
för offlinevalideringen och samma marina råfiler återanvänds fortsatt.

## Bedömning av originalfilers metadata-only åtkomst 2026-10-16

Granskad installerad Toolbox 2.5.0 skiljer transportmetadata från NetCDF-
attribut: _get_file_size_last_modified_and_etag använder HeadObject och
returnerar ContentLength/LastModified/ETag. _download_one_file använder
session.download_file för objektet. Ingen separat NetCDF-attributexport
identifierades i dessa granskade kodvägar. Detta är ett avgränsat kodfynd,
inte bevis att ingen annan tjänst kan ha sådan metadata.
[Officiell Python-interface](https://toolbox-docs.marine.copernicus.eu/en/stable/python-interface.html)
lästes som kompletterande API-referens; ingen ny originalhämtning kördes.

[h5py:s file-like-dokumentation](https://docs.h5py.org/en/stable/high/file.html#python-file-like-objects)
beskriver läs-/seek-gränssnitt och flera lagringsdrivrutiner. Ett file-like-
gränssnitt begränsar hur bytes läses, men intygar inte att ett godtyckligt
läsintervall enbart innehåller metadata. Detta sista är vår slutsats, verifierad
av det syntetiska motexemplet nedan.

Offline lässpårning av redan sparade hashkontrollerade filer gav:

| Fil | Läsanrop / summerade lästa bytes | Överlapp med inventerade väderchunkar |
| --- | --- | --- |
| waves.nc | 40 / 20054 | 0 |
| current.nc | 44 / 21344 | 0 |
| wave-mask.nc | 27 / 14106 | Ej tillämpligt: inga våg-/strömvariabler inventerade |

Summeringen räknar även återlästa byteintervall, inte unika bytes eller
nätverkstrafik. Dessa är lokala subsetfiler och resultatet kvalificerar inte
originalfilernas okända layout. Rapport: autonomy/hdf5-read-review-20261016.json.
Globala attributvärden eller kontakt-/history-fält loggades inte.

En körbar syntetisk HDF5-regression skapar kompakt lagrade vädervärden. Trots
att konsumenten bara begär units-attributet innehåller ett HDF5-läsfönster de
identifierade väderbytesen. Därmed räcker logisk attributläsning inte som garanti
för att en framtida range-transport aldrig hämtar väderdata. Det är ett
motexempel, inget påstående att våra originalfiler har kompakt lagring.

PROJECT_BLOCKER: ingen verifierad metod i granskad kedja för att garantera
originalfilernas metadataåtkomst utan väderbytehämtning. Inget remote range-
anrop, HEAD eller nytt get/subset gjordes i denna del. Fortsatt arbete kräver
separat metadataartefakt/tjänst med verifierad semantik eller nytt mandat för
annan dataåtkomst. Befintliga nio källfiler och dagens CSV återanvänds.
Alla planning_blockers och data_unavailable kvarstår.
