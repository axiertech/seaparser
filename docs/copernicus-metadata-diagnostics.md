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
