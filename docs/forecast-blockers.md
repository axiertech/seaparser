# Kvarvarande prognosblockerare och metadataövergång

Arbetskatalog: `/tmp/seaparser-real-map-data`, branch `development/real-map-data`.
Återanvänd endast `fixtures/vinga-copernicus/` för det granskade marina uttaget.
SHA-256 finns i dess manifest; originalen ligger i `/tmp/seaparser-cmems-vinga/`.
Inga nya uttag för samma data behövs. Publik demonstration ändras inte.

## Nuvarande avvisning

CopernicusMarineAdapter normaliserar befintliga CF-fält och behåller separata
grid. ProductMetadata innehåller explicita planning_blockers. Färdberäkning,
segmentkontroll och ForecastPolicy avvisar okänd körförenlighet; ifyllda datum
eller ett payloadflag är inte evidens. Giltighetstider, katalogversion,
hämtningstid och creation_date är olika saker. Ingen rutt/GPX kan godkännas
med det partiella underlaget. Vind saknas separat.

## Fortsatt arbete efter adaptergranskningen

MET:s officiella wiki dokumenterar MET Nordic Forecast som regionalt,
deterministiskt, timvis uppdaterat underlag på 1 km Lambert conformal conic-grid.
Dokumenterade variabler är wind_speed_10m (m/s) och wind_direction_10m (grader,
FRÅN nord medurs), som avser 10-minutersmedel vid 10 m. Analysprodukten är
separat och får inte användas som framtida vind. Faktiska CF-attribut, grid,
giltighet, modellreferens och Vinga-täckning måste granskas innan en adapter
eller något nytt vinduttag görs.

Verifierade dokumentationskällor 2026-10-13:
[MET Nordic](https://github.com/metno/NWPdocs/wiki/MET-Nordic-dataset),
[MET data access](https://github.com/metno/NWPdocs/wiki/Data-access).
Den äldre länkade katalogsidan /thredds/metno.html ger fortfarande 404 via
webbverktyget. Direkt metadataåtkomst till THREDDS kunde inte verifieras.
Wiki dokumenterar konkreta metpparchive/metpplatest-sökvägar; scriptet prövar
metadata för den fasta forecast-filen från 2026-10-13 00Z, inte en föränderlig
_latest-länk. Sökvägen är en dokumenterad kandidat tills servern svarar.

Copernicus skiljer mellan originalproducerade filer (`get`) och omorganiserad
ARCO-data (`subset`). ARCO kan harmonisera koordinater/tidsrepresentation och
metadata. Avsaknad av körtid i de befintliga subset-filerna kan därför inte
lösas genom antaganden om filskapandetid eller ett nytt identiskt subset.
Nästa steg är att identifiera originalfil och läsa dess dokumenterade körmetadata.
[Officiell beskrivning av original/ARCO](https://help.marine.copernicus.eu/en/articles/8656000-differences-between-original-producer-files-and-arco-data).

## Exakt metadataförsök i vanlig SSH-terminal

```bash
cd /tmp/seaparser-real-map-data
umask 077
PROBE_DIR=/home/web/seaparser/autonomy/forecast-metadata-$(date -u +%Y%m%dT%H%M%SZ)-$$
timeout --signal=TERM --kill-after=5s 180s .venv/bin/python -B -m scripts.probe_forecast_metadata --output "$PROBE_DIR"
printf 'EXIT_CODE=%s\nREPORT=%s/report.json\n' "$?" "$PROBE_DIR"
```

Detta läser endast DDS/DAS och tidskoordinater från MET samt skapar listor över
Copernicus-originalfilers namn/storlek/modifieringstid. `get` körs med både
create_file_list och dry_run; inga ursprungliga väderfiler eller subset hämtas.
Sparad autentisering återanvänds av Toolbox 2.5.0; inga hemligheter ingår i
argument, logg eller script. Metadataresponsen begränsas till 512 KB per fil.
Exit 2 innebär ofullständigt metadataförsök, 124 timeout; report.json visar
vilka oberoende anrop som misslyckats. Exit 0 betyder endast komplett transport
av metadata, aldrig godkänd vindprognos, modellutfärdande eller rutt.

Agentförsök 2026-10-13 05:28:42–05:28:44 UTC gav exit 2. MET-anropen gav
URLError och Copernicus preflight gaierror. Rapport:
`/home/web/seaparser/autonomy/forecast-metadata-probe-20261013/report.json`.
Inga nya väderdata hämtades. Scriptet fortsätter till andra metadataanrop när
ett MET-anrop misslyckas; fortsatt blockerad åtkomst kräver vanlig terminal.

## Nästa konkreta uppgift och acceptans

1. Kör metadataförsöket ovan i en nätverksåtkomlig miljö och granska report.json.
2. Kontrollera faktisk forecast_reference_time, time-enheter/kalender,
   höjd, wind-field standard_name/cell_methods, Lambert-grid/CRS och Vinga-box.
3. Koppla de befintliga marina filernas fem timsteg till dokumenterat
   originalfil/run-ID och äkta utfärdandetid. Filename/last_modified är bara ledtrådar.
4. Definiera och testa en källspecifik förenlighetsregel för identifierade körningar.
   Häva inte planning_blockers förrän detta och vindens rum/tidstöd är verifierat.
5. Vid fortsatt nätverksblockering: arbeta med oberoende kontrakt/tester och
   metadataanalys. Ingen punktvind sprids över området och inga produktionsspärrar tas bort.

Inför autonom överlämning: kontrollera git status och HEAD mot kvittot i
`/home/web/seaparser/autonomy/HANDOFF.md`. Inget bakgrundspass förutsätts vara
startat. Worktree-, data-, branch- och mandatgränser följer AGENTS.md.
