# Regionala Copernicus-uttag och lokal cache

Budgetarna gäller diagnostisk hämtning, inte kvalificering för planering.
Användarens mandat 2026-10-17 ersätter provets 2 MB fil / 5 MB överföring med
konfigurerbara GB-budgetar för kostnadsfritt dataarbete. Inga köp ingår.

`python -B -m scripts.download_copernicus --help` visar alla parametrar.
Standard är 2 GB per resultatfil, 10 GB uppskattad överföring per begäran,
20 GB summerad uppskattad överföring per körning och 1 GB kvarvarande
lagringsreserv. GB betyder 1 000 000 000 byte. Ändra med
`--file-budget-gb`, `--transfer-budget-gb`, `--total-transfer-budget-gb` och
`--disk-reserve-gb`. Rutinmässiga höjningar inom mandatet kräver inte ny
bekräftelse; ange och redovisa vald budget. Ingen automatisk obegränsad höjning.

Avgränsa med `--bbox WEST SOUTH EAST NORTH`, `--start`, `--end`,
`--products waves current wave-mask` och `--variables`. Tidsgränser måste ha
explicit tidszon. Endast granskade produktvariabler godtas och varje vald
produkt måste ha minst en vald variabel. För ström kan `--minimum-depth` och
`--maximum-depth` sättas tillsammans; annars används katalogens granskade
ytnära lager. WAV saknar djupaxel och får inget påhittat djupurval.
`strict-inside`, explicit dataset/version/part/service och `raise_if_updating`
behålls. Standardvärden för datum/område är det historiska Vinga-uttaget;
ange alltid avsedda giltighetstider vid nya uttag.

Exempel för WAV-fallet:

```bash
scripts/download-copernicus.sh /tmp/seaparser-regional \
  --products waves --bbox 11.58 57.62 11.63 57.65 \
  --start 2026-10-17T00:00:00Z --end 2026-10-17T04:00:00Z \
  --variables VHM0 VTM02 VMDR \
  --file-budget-gb 2 --transfer-budget-gb 10 --total-transfer-budget-gb 20
```

Wrappern behåller privat logg, lås och timeout. Timeout är nu konfigurerbar via
`SEAPARSER_DOWNLOAD_TIMEOUT_SECONDS`, standard 3600 sekunder, för regionala
uttag. Anpassade urval märks diagnostiska; den äldre fullbundle-auditen körs
automatiskt bara för standardanrop utan extra argument. Manuell fullbundle-
audit och all planeringskvalificering är fortsatt separata krav.

Inför varje cachemiss görs dry_run. Saknade, negativa eller icke-finita
estimat avvisas. Både överföringsbudget och filbudget kontrolleras och fri disk
på cache-/målvolymerna måste täcka två uppskattade resultatfiler plus reserv.
Efter hämtning kontrolleras faktisk filstorlek och diskutrymme inför kopiering.
Toolbox 2.5.0:s NetCDF-estimatorer använder divisorn 1048e3 i
`download_functions/utils.py`; konverteringen till byte följer denna kod.
Estimat är inte en mätning av verklig nättrafik och garanterar inte faktisk
komprimering, temporär diskåtgång eller minnesåtgång. Logg och manifest skiljer
uppskattad överföring, uppskattad resultatstorlek och faktisk resultatstorlek.

Cache: `/tmp/seaparser-copernicus-cache`, kan flyttas med `--cache` till en
volym med lämplig kapacitet. Begärans område, giltighet, variabler, djup,
dataset/version/part/service och Toolbox-version ingår i identiteten;
utkatalogen gör det inte. Cacheträff kräver komplett metadata, rätt storlek,
SHA-256 och ålder inom `--cache-max-age-hours` (standard 6). Identiska
samtidiga begäranden låses per nyckel. Ofullständiga hämtningar ligger i
staging och blir inte cacheträffar. Hashning sker strömmande för stora filer.
Cacheträff hoppar över subset/dry_run, men katalogmetadata läses fortfarande.
Överföringsestimat för cacheträffens väderdata under aktuell körning är noll;
ursprungligt estimat och ursprunglig hämtningstid bevaras.

Cache är ett återanvänt snapshot. TTL eller katalogversion bevisar inte att en
muterbar ARCO-produkt är senaste körningen. Ingen hämtningstid får användas som
issued_at/run-ID. Korrupta eller utgångna poster hämtas om vid begäran; ingen
automatisk cacheeviktering eller bakgrundshämtning införs. Befintliga fixtures
utan exakt begäransidentitet importeras inte godtyckligt till cachen.

## Verifierat WAV-uttag 2026-10-17

Dataset `cmems_mod_bal_wav_anfc_PT1H-i`, 202311/default/arco-geo-series,
Vinga-boxen ovan, 00–04 UTC, VHM0/VTM02/VMDR. Privat resultat i
`/tmp/seaparser-wav-regional-20261017`, fil 26 114 byte, SHA-256
`9030a4d3cb945410e3ec7d69018886e43f859d3696e973360eea96b4b65bf279`.
Överföringsestimat cirka 42,6 miljoner byte; resultatestimat cirka 13,9 kB.
Verklig överföringsvolym är inte uppmätt. Samma begäran verifierades som
cacheträff med oförändrad filhash och ingen ny väderhämtning.

Filen har 5 × 2 × 2 noder per variabel, timvisa giltigheter 00, 01, 02, 03,
04 UTC. Latitud 57.62477111816406/57.64143753051758 och longitud
11.597147941589355/11.62492561340332. Inga fill-/icke-finita värden i dessa
60 variabelvärden. Alla tre har fortfarande `cell_methods="time: mean"` utan
tidsbounds. `forecast_reference_time`, `forecast_period`, utfärdandetid,
run-ID och revision saknas. Ingen ny källbunden run-/tidsstödsevidens har
alltså löst de tidigare blockerarna. Ingen ruttkörning eller ändring av
planeringsspärrarna följer av uttaget.
