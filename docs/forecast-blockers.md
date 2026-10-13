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

## Aktivt delpass 2026-10-13, 07:15 UTC

Metadataförsöket 07:15:54–07:15:56 UTC gav exit 2: tre MET-anrop med
`URLError`, Copernicus katalog-DNS med `gaierror`. Faktisk rapport:
`/home/web/seaparser/autonomy/forecast-metadata-20261013T0717Z/report.json`.
Inga nya subset eller originalväderfiler hämtades. SSH-provet är enligt
användarens aktuella instruktion verifierat; nätverksåtkomst i agentmiljön
är ändå inte verifierad. Feltyperna bevisar inte att källorna saknar data.

Oberoende offlinearbete förbättrar metadata-proben: fel för en marin produkt
bevarar den andra produktens resultat och försök. CSV-header, radstruktur,
filstorleksfält och metadatabudget kontrolleras. Tom fillista ger
`no_matching_files`, aldrig komplett metadataåtkomst. Antal listade filer
och SHA-256 är transportproveniens, inte modellkörningsbevis. Även komplett
transport lämnar alla tre planeringsblockerare och `data_unavailable`.
Inga modellutfärdanden härleds från namn, datumkolumn eller etag.

## 2026-10-13 21:41 UTC: MET-metadataformat och nytt källförsök

Aktivt auktoriserat pass, arbetsrot /tmp/seaparser-real-map-data på
 development/real-map-data. Metadataförsök 21:41:51–21:41:52 UTC gav exit 2:
MET tre URLError, Copernicus preflight gaierror. Rapport finns i
/home/web/seaparser/autonomy/forecast-metadata-20261013T2143Z/report.json.
Ingen ny marin data hämtades och feltyperna bevisar inte att data saknas.

Oberoende förbättring: MET DAS kräver Attributes-envelope; DDS och tids-ASCII
kräver Dataset-envelope. Fel sorts DAP-svar avvisas. Detta är en begränsad
transportkontroll, inte en fullständig DAP-parser eller run-verifiering.
Antagande: befintliga granskade endpoints behåller respektive DAP-envelope.
Åtta probetester passerar, inklusive båda felriktningarna och kvarvarande spärrar.
Full scripts/check.py passerar: 158+99 Python-tester, syntax, beroendelåsning,
pip check och domängränser. Frontend run check passerar. Alla tre frysta marina
hashar matchar manifestet; adapter_sample_checks=passed och routing unavailable.

Git ls-remote misslyckades med exit 128: Bad owner or permissions on
/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf. Systemfilen är orörd.
GitHub-connectorns repo/CI-anrop ger Unknown tool; ny CI är overifierad.
Nästa uppgift: källbundet offlinekontrakt för modellrun-proveniens eller faktisk
metadataåtkomst när miljön medger det. Samma marina fixtures återanvänds och
alla planning_blockers kvarstår. Publik demonstration är orörd.

Frontend test: första körning exit 1; socket.socket() gav PermissionError i
sandboxen. Godkänt sandboxundantag för befintliga lokala tester gav exit 0,
sex frontendtester passerar inklusive syntetisk och Vinga API/karta/GPX.
Loggar: autonomy/logs/met-envelope-{check,frontend,frontend-recheck,fixture}-20261013T2143Z.*.

Offline granskningskontrakt och acceptansmatris: [forecast-run-provenance.md](forecast-run-provenance.md). Design endast; ingen run-certifiering eller hävd spärr.
