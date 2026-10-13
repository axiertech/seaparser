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

Befintliga filers faktiska run-evidens och gap: [forecast-run-inventory.md](forecast-run-inventory.md). Inget utfärdande/run-ID återfunnet; creation_date får inte användas som ersättning.

Regional vinds geometri, rotation, masker och segmentstöd: [regional-wind-acceptance.md](regional-wind-acceptance.md). Offline acceptansdesign; verklig MET-import och run-förenlighet fortfarande blockerade.

## 2026-10-13: MET-redirect avvisas före destinationshämtning

Granskning fann att urllibs standardredirect kunde lämna den fasta URL-listan
för metadata. MET använder nu en separat opener som avvisar redirects före
nytt HTTP-anrop. Alla redirects kräver källgranskning, även tillbaka till en
metadata-URL. Feltexten innehåller inte destination eller privat query.
Detta kan avvisa en legitim källredirect tills den granskas; inget nytt endpoint
eller undantag antas. DDS/DAS/ASCII-budget och formatkontroller kvarstår.

Tio riktade probetester passerar. HTTPRedirectHandlers faktiska felhantering
för 301/302/303/307/308 testas offline: destinationsopener anropas aldrig.
Separat test visar att ett redirectfel bevarar oberoende MET-resultat och alla
tre planeringsblockerare. Den verkliga MET-openern har enbart den avvisande
redirect-handlern. Inget nätverksförsök eller nytt väderuttag görs i dessa tester.
Ingen routing, adapter, databas eller publik demonstration ändras.

Full scripts/check.py passerar: 158+101=259 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar; full frontendintegration
var oförändrad och godkänd med sex tester i passets första kodleverans.
Alla tre marina hashvärden matchar fortfarande manifestet. Logg:
autonomy/logs/met-redirect-check-20261013T2154Z.log.
Nästa oberoende granskning: metadata-probens CSV/bytesbudget och partiella
transportproveniens; inga nya källor eller hävda planning_blockers.

## 2026-10-13: CSV-läsbudget och partiell transportproveniens

Metadata-probens marina CSV-läsning begränsas nu till 512001 bytes och
kontrollerar faktiskt läst antal mot 512000-bytebudgeten. Stat-kontrollen kvarstår
men räcker inte ensam när en fil växer. Överbudgetdata får ingen godkänd hash/
filräkning i rapporten. Toolboxens skapande av listfilen sker före denna kontroll;
ändringen begränsar lokal läsning, inte bibliotekets interna nätverksöverföring.

Ett under-budget-svar behåller bytes/SHA-256 även vid felaktig CSV/header/UTF-8.
Status är fortsatt blocked, file_count saknas och model_issue_time är null.
Hashen är transportbevis, inte lyckad validering eller run-identitet.
CSV läses med StringIO(newline='') så parsern får ursprungliga radgränser.
Tolv riktade probetester passerar, inklusive simulerad filväxt mellan stat/läsning
och hashproveniens för ogiltig header. Inga nya metadata-/väderanrop i testerna.
Planning_blockers och data_unavailable kvarstår. Publik demonstration är orörd.

Full scripts/check.py passerar: 158+103=261 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/metadata-budget-check-20261013T2156Z.log.
Nästa oberoende del: auditens dokumenterade modellreferens/issued_at-semantik,
med konservativ avvisning och syntetiska CF-regressioner före framtida certifiering.

## 2026-10-13: CF-modellreferens skiljs från utfärdandetid

scripts.audit_copernicus placerar inte längre forecast_reference_time i issued_at.
Dekodat scalar-värde redovisas i separat forecast_reference_time för granskning;
issued_at förblir null tills källspecifikt utfärdandebevis verifierats. Rapportens
schema 1 får ett additivt diagnostikfält; fryst adapterpayload ändras inte.
Tvetydiga/odekodade referenser förblir okända. Ingen run-certifiering införs.

Tio Copernicus-importtester passerar. Nya syntetiska NetCDF-fall visar att även
lika modellreferenstid plus creation_date för ström/vågor behåller båda
utfärdandespärrarna och run-förenlighetsspärren. Dubbla referenser/numeriskt
odekodat värde ger ingen referenstid. Befintliga råfiler regenererar exakt
samma reference.json-innehåll. Inga marina data hämtade eller befintliga filer
ändrade; publik demonstration och databas är orörda.

Full scripts/check.py passerar: 158+105=263 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/reference-time-check-20261013T2158Z.log.
Nästa oberoende granskning: CF-giltighetens precision/kalender före
normalisering till sekunder; kontrollera att verkliga tidsluckor inte döljs.

## 2026-10-13: CF-giltighet utan dold sekundtrunkering

Auditens exakta timsteg kontrolleras nu mot ursprungliga dekodade datetime-värden
innan normalisering till sekunder godkänns. Icke-datetime-giltighet avvisas;
subsekundförskjutning får inte bli ett till synes korrekt timsteg. Ingen
tidsmässig tolerans antas. Modellreferensdiagnostik bevarar delsekunder, medan
hela sekunder behåller tidigare format. Utfärdandetid/run förblir overifierade.

Tolv importtester passerar, inklusive förskjutning av en inre tid och av alla
tider med 250 ms samt bevarad .250-sekundprecision i syntetisk modellreferens.
Första riktade körningen fann en formateringsregression (auto gav minutformat);
formatet korrigerades och slutkörningen passerar. Befintliga verkliga marina
tider kontrollerade utan nätverk: alla fem ligger exakt på hela sekunder i
båda dynamiska produkter. Befintlig reference regenereras identiskt.
Inga nya marina filer, adaptrar, beroenden, databasoperationer eller publik ändring.
Logg autonomy/logs/cf-precision-targeted-20261013T2200Z.log.

Full scripts/check.py passerar: 158+107=265 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Logg:
autonomy/logs/cf-precision-check-20261013T2200Z.log.
Nästa oberoende möjlighet: ett avgränsat metadata-only åtkomstförsök med
sandboxundantag prövat av auto-review, eftersom tidigare fel var från den
begränsade nätverksmiljön; ingen ny marin väderfil får hämtas. Vid avslag eller
fortsatt källfel: dokumentera exakt resultat och fortsätt offlinegranskning.

## 2026-10-13: MET-metadata nådd med godkänt sandboxundantag

Granskat metadata-only försök gav tre faktiska MET-svar: DDS/DAS/tids-ASCII.
Metadatafixture och granskning finns i fixtures/met-nordic-metadata och
met-nordic-metadata-review.md. 1796×2321 Lambert-grid med sfärradie 6371000 m,
59 timsteg och explicit modellreferens 2026-10-13 00Z återfunna. Ingen faktisk
höjdkoordinat/cell_methods, regional cellgeometri eller utfärdande verifierade.
Inga vindvärden eller nya marina data hämtade. Alla planning_blockers kvarstår.
Nästa steg är begränsad native koordinatgranskning, inte vindadapter/routing.

Övergripande metadataförsök slutade exit 124 vid 180 s-gränsen under Copernicus-
steget. Ingen marin CSV eller report.json skapades; orsaken inom det steget är
inte verifierad. MET:s tre lyckade svar bevarades och hash-/bytekontrollerades.
Partiell arbetsrapport autonomy/met-source-partial-result-20261013T2205Z.json.
Tolv metadata-probetester passerar; lokala dokumentlänkar kontrollerade.
Tidigare kodcommit 080483b har 265 Python-tester och frontend check godkända.
Ingen kod ändras i denna metadata-/dokumentationsleverans.

## 2026-10-13: verkliga MET-koordinater och lokalt representationshinder

Auto-review-godkända koordinatanrop gav native x/y (43241 bytes) och ett
8×7 lat/lon-subset (2120 bytes). URL-kodning rättade ett första HTTPError.
Svar/hashmanifest och geometry-review.json återanvänds i MET-metadatafixturen.
Decimal-axlar har exakt 1000 m intervall. 56 källreferensnoder jämfördes med
sfärisk LCC: maxavvikelse 0.249077 m. Lokal AEQD-diagnostik visar minst
184.738574 m maxfel för varje separerbar östaxel över detta subset; direkt
lokal gridrepresentation är blockerad. Datumekvivalens/routingstöd certifieras inte.
Ingen vinddata/adapter eller ny marin data. Alla planning_blockers kvarstår.
Nästa oberoende förbättring: checkpoint av metadata-probens delrapport före
potentiellt långsamma anrop, så timeout inte tappar lyckad proveniens.

Verifiering: fem MET-källhashar/byteantal, geometrierapportens hash, 56 nodreferenser,
rapportens nedre felgräns och dokumentlänkar kontrollerade. Tolv befintliga
metadata-probetester passerar. Logg autonomy/logs/met-coordinate-tests-20261013T2211Z.log;
verifieringskvitto autonomy/met-coordinate-verification-20261013T2211Z.json.
Ingen applikationskod ändrad; tidigare 080483b har 265 Python-tester och
frontend check godkända. Geometridiagnostiken kvalificerar inte verklig routing.

## 2026-10-13: successiva metadata-checkpoints före långsamma steg

probe_forecast_metadata skriver report.json före transportstart, före/efter
varje MET-anrop, före Copernicus preflight och före/efter varje marin produkt.
Varje skrivning sker till temporär fil som ersätter rapporten atomiskt; läsaren
får föregående eller nytt fullständigt JSON, inte en avsiktligt halvskriven rapport.
Detta är processavbrottstålighet, inte ett påstående om hållbarhet vid strömavbrott.

attempt_status=in_progress, active_step och finished_at=null anger ofullständigt
försök; det bevisar inte i sig timeout eller att processen fortfarande kör.
Extern exitkod behövs för avslutsorsaken. metadata_complete förblir false tills
samtliga steg avslutats och transportkriterier passerar. Slutrapport anger
attempt_status=finished även vid källfel, med metadata_complete=false vid luckor.
In_progress för en marin produkt får aldrig räknas som lyckad listning.

Fjorton probetester passerar. Simulerat avbrott före första MET-svaret ger
läsbar initial checkpoint; avbrott under andra marina produkten bevarar samtliga
MET-resultat och första marina produktens hash. Alla planning_blockers kvarstår.
Inga nya nätverksanrop/väderfiler, beroenden, adaptrar, databas eller publik ändring.

Full scripts/check.py passerar: 158+109=267 Python-tester, syntax, låsfiler,
pip check och domängränser. Frontend run check passerar. Tre marina och fem
MET-källhashar är oförändrade. Loggar:
autonomy/logs/metadata-checkpoint-check-20261013T2213Z.log och
metadata-checkpoint-targeted-20261013T2213Z.log.
Nästa begränsade del kan pröva endast marin metadata-listning med progress-
checkpoints och kort tidsgräns, utan upprepning av MET eller marina väderuttag.
