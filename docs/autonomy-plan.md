# Autonomy-plan

## Sammanfattning

`~/autonomy` är ett separat Git-repo som styr autonoma Codex-arbetspass mot
SeaParser-worktreet. Repot fungerar (SSH-prov, femtimmarspass, CI-kvitton och
proveniens i `copernicus-prepared-d0bd906/` är bra mönster), men det har vuxit
ohämmat: 56 markdown-filer, 17 JSON-filer, 16 Python-filer, 30 loggkataloger
(114 MiB, 1534 filer) och en `published-urls.log` på 377 KiB/1438 rader utan
rotation. Sex statusfiler överlappar varandra, tre lock-filer är 0 byte och
används inkonsekvent (flock i `run.sh` men fil-existens i andra skript), och
`work_session.py` (666 rader) blandar preflight, retry-policy, tmux-hantering
och processövervakning. Planen konsoliderar status, inför ett enda flock-baserat
lås, roterar loggar, samlar preflight-skripten i ett gemensamt gränssnitt och
delar upp `work_session.py`. Inget i `~/autonomy` ändras av denna plan.

## Nuvarande problem (numrerade, med bevis)

### 1. Sex överlappande statusfiler utan en enda källa till sanning
`CURRENT-STATUS.md`, `current-status.json`, `HANDOFF.md`, `SCENARIO-STATUS.md`,
`permanent-recovery-latest.json` och `resume-worktree.json` beskriver alla
arbetspassets tillstånd. `CURRENT-STATUS.md` och `HANDOFF.md` är byte-identiska
i innehåll (samma rubrik "Aktuell Trelleborg-leverans och API-förberedelse
2026-10-19T20:45:05.481325+00:00"), medan `current-status.json` innehåller en
helt annan, äldre struktur (`five_hour_pass`, `recovery_delivery`,
`publication`). Det är oklart vilken fil som är auktoritativ, och en läsare
måste läsa alla sex för att veta vad som gäller. Risk: en föråldrad fil kan
läsas som aktuell och leda till felaktiga start-/stoppbeslut.

### 2. Lock-filer är 0 byte och används inkonsekvent
`run.lock`, `ssh-probe-launch.lock` och `work-launch.lock` är alla 0 byte
(`ls -la` visar storlek 0). `run.sh` använder `flock -n 9` på `run.lock`
(rad `exec 9>"$BASE/run.lock"` följt av `flock -n 9 || exit 75`), vilket är
korrekt och kraschsäkert. Men `ssh-probe-launch.lock` och `work-launch.lock`
är separata filer vars existens (inte flock) tycks användas som lås i andra
skript. Risk: om en process kraschar utan att ta bort en existens-baserad
lock-fil blir låset permanent fastlåst (stale lock), och tre separata lås kan
inte garantera ömsesidig uteslutning mellan probe/work/launch.

### 3. Loggtillväxt utan rotation eller rensning
`logs/` innehåller 30 underkataloger, 1534 filer och 114 MiB. `work-five-hours/`
har 14 passkataloger plus en `latest`-symlänk, och varje passkatalog innehåller
många `turn-*.jsonl`/`turn-*.stderr.log`-filer. `published-urls.log` är 377 885
byte och 1438 rader utan någon rotation (ingen `.1`, `.gz` eller rensning
synlig). Risk: obegränsad tillväxt fyller disken och gör det svårt att hitta
relevanta loggar.

### 4. Preflight-spridning: 10 fristående skript utan gemensamt gränssnitt
Det finns 10 `*preflight*.py`-filer (`compact-source-preflight.py`,
`stream-land-preflight.py`, `trelleborg-combined-preflight.py`,
`trelleborg-endpoints-preflight.py`, `trelleborg-reversed-preflight.py`,
`trelleborg-rss-preflight.py`, `trelleborg-trim-preflight.py`,
`trelleborg-weather-release-rss-preflight.py`,
`trelleborg-weather-rss-preflight.py`, `water-stage-preflight.py`). De är
engångsmätningar med hårdkodade `resource.setrlimit`-värden (1100/1500/700 MiB),
hårdkodade sökvägar och olika utdataformat (vissa skriver `status='ok'`,
andra `status='rss_budget_stop'`). Inget gemensamt gränssnitt, ingen gemensam
argument-/utdatakontrakt. Risk: duplicerad logik, svårt att återanvända och
testa, och hårdkodade budgetar spridda på tio ställen.

### 5. `work_session.py` är 666 rader med blandade ansvarsområden
`work_session.py` (666 rader) innehåller preflight (`preflight()` rad 63),
usage-retry (`usage_retry()` rad 149), capacity-retry (`capacity_retry()` rad
193), budget (`task_budget()` rad 225), processövervakning (`stop_process()`
rad 240), worker-loop (`worker()` rad 258 med nästlad `turn()`/`recover_timeout()`
rad 349/433), samt start/stopp (`check_start`, `check_resume`, `launch`, `stop`
rad 549–628). `ssh_probe.py` (164 rader) är mer fokuserad men delar
`worker()`-mönstret. Risk: en enda stor modul är svår att testa isolerat och
svår att ändra utan att bryta flera flöden.

### 6. Hårdkodade konstanter och sökvägar spridda i koden
`work_session.py` hårdkodar `SSH_HEAD`, `HEAD`, `MODEL='gpt-6.1-sol'`,
`CODEX`, `SOCKET`, `SESSION` och `LOGROOT` (rad 17–31), och `run.sh` hårdkodar
`WORKDIR`, `CODEX` och `BASE`. `current-status.json` hårdkodar
`expected_commit` och `workdir`. Risk: byte av commit/modell/worktree kräver
redigering på flera ställen, vilket ökar risken för inkonsekvens (jämför
README:s notering om att körskriptet uppdaterades under ett aktivt pass och gav
exit 127).

## Föreslagna ändringar (numrerade)

### Ändring 1: Konsolidera statusfiler till en enda maskinläsbar källa
- **Vad:** Gör `current-status.json` till den enda auktoritativa statusfilen
  med ett versionsfält och en `updated_at`-tidsstämpel. Generera
  `CURRENT-STATUS.md` och `HANDOFF.md` från den (eller gör dem till korta
  pekare). Flytta `permanent-recovery-latest.json`, `resume-worktree.json` och
  `SCENARIO-STATUS.md` till en `archive/`-katalog eller slå ihop dem i
  statusfilen som historik.
- **Varför:** Löser problem 1 (sex överlappande filer, byte-identiska
  CURRENT-STATUS.md/HANDOFF.md, olika JSON-strukturer).
- **Filer som påverkas:** `current-status.json`, `CURRENT-STATUS.md`,
  `HANDOFF.md`, `SCENARIO-STATUS.md`, `permanent-recovery-latest.json`,
  `resume-worktree.json` (i `~/autonomy`; ändras inte av denna plan, bara
  beskrivs).
- **Testplan:** Enhetstest att JSON-parsning ger samma fält som markdown-
  generatorn; test att `updated_at` är monotont ökande; test att arkiverade
  filer inte längre läses av start-/stoppskripten.
- **Migreringsrisk:** Medel – statusfiler läses av flera skript; alla läsare
  måste pekas om samtidigt.
- **Beroenden:** Inga; kan göras först.

### Ändring 2: Ett enda flock-baserat lås för alla start-/stoppflöden
- **Vad:** Behåll `run.lock` med `flock` (som i `run.sh`) som det enda låset.
  Ta bort `ssh-probe-launch.lock` och `work-launch.lock`, eller gör dem till
  flock-baserade lås på samma fil. Dokumentera att låset aldrig får tas bort
  manuellt (flock släpper automatiskt vid krasch).
- **Varför:** Löser problem 2 (0-byte-filer, existens-baserade lås som kan bli
  stale, tre separata lås utan ömsesidig uteslutning).
- **Filer som påverkas:** `run.sh`, `work_session.py`, `ssh_probe.py`,
  `start-probe.sh`, `start-work.sh`, `stop-work.sh`.
- **Testplan:** Integrationstest att två samtidiga `run.sh`-anrop ger exit 75
  för den andra; test att en dödad process (SIGKILL) inte lämnar ett stale lås
  (flock släpper); test att probe och work inte kan köra samtidigt.
- **Migreringsrisk:** Låg – flock är redan det korrekta mönstret i `run.sh`.
- **Beroenden:** Kan göras oberoende, men samordnas med Ändring 5 (uppdelning
  av `work_session.py`).

### Ändring 3: Loggrotation och rensning
- **Vad:** Inför rotation för `published-urls.log` (t.ex. `logrotate` eller en
  inbyggd storleks-/åldersgräns) och en rensningspolicy för `logs/`
  (behåll senaste N passkataloger, komprimera äldre `turn-*.jsonl`).
- **Varför:** Löser problem 3 (114 MiB, 1534 filer, 1438 rader utan rotation).
- **Filer som påverkas:** `published-urls.log`, `logs/`-strukturen, eventuellt
  ett nytt `rotate-logs.sh`.
- **Testplan:** Test att rotation skapar `.1`/`.gz` vid tröskel; test att
  rensning behåller senaste N och tar bort äldre; test att `latest`-symlänken
  förblir giltig.
- **Migreringsrisk:** Låg – rent additivt, men måste inte radera data som
  fortfarande behövs för revision.
- **Beroenden:** Inga.

### Ändring 4: Gemensamt preflight-gränssnitt
- **Vad:** Samla de 10 preflight-skripten i en modul med ett gemensamt
  kontrakt: `preflight(name, budget_mib, fn) -> {status, seconds,
  peak_rss_kib, ...}`. Flytta hårdkodade budgetar (1100/1500/700 MiB) till en
  central konfig. Behåll varje mätning som en funktion, inte ett fristående
  skript.
- **Varför:** Löser problem 4 (10 fristående skript, olika utdataformat,
  hårdkodade budgetar).
- **Filer som påverkas:** Alla 10 `*preflight*.py` samt en ny
  `preflight_common.py`.
- **Testplan:** Enhetstest att varje preflight returnerar samma schema; test
  att budgeten läses från konfig och inte är hårdkodad; test att ett
  misslyckat preflight ger `status='failed'` med `error_type`.
- **Migreringsrisk:** Medel – skripten är engångsmätningar med specifika
  sidoeffekter (rlimit, faulthandler); konsolidering måste bevara exakt
  beteende.
- **Beroenden:** Inga; kan göras parallellt med Ändring 1.

### Ändring 5: Dela upp `work_session.py`
- **Vad:** Dela upp i minst tre moduler: `preflight.py` (identitets-/HEAD-/
  autentiseringskontroll), `retry.py` (usage-/capacity-retry-policyer) och
  `runner.py` (tmux/process/worker-loop). Behåll `ssh_probe.py` separat men
  dela dess `worker()`-mönster med `runner.py`.
- **Varför:** Löser problem 5 (666 rader blandade ansvarsområden) och gör
  retry-policyerna testbara isolerat (jämför befintliga `test_capacity_retry.py`
  på 20 KiB).
- **Filer som påverkas:** `work_session.py`, `ssh_probe.py`, nya
  `preflight.py`/`retry.py`/`runner.py`.
- **Testplan:** Befintliga 22 offlineprov (nämnda i FIVE-HOUR-PASS.md) måste
  fortsätta passera; nya enhetstester per modul (retry utan riktig Codex,
  preflight med fejkad git/HEAD).
- **Migreringsrisk:** Hög – `work_session.py` är kärnan i passhanteringen och
  har nästlade closures (`worker()` med `turn()`/`recover_timeout()`).
- **Beroenden:** Ändring 2 (lås) bör göras först så att låslogiken inte
  dupliceras under uppdelningen.

### Ändring 6: Centralisera konstanter och sökvägar
- **Vad:** Flytta `SSH_HEAD`, `HEAD`, `MODEL`, `CODEX`, `SOCKET`, `SESSION`,
  `LOGROOT`, `WORKDIR` till en enda konfigfil (t.ex. `autonomy.conf` eller
  `config.json`) som läses av `run.sh`, `work_session.py` och `ssh_probe.py`.
- **Varför:** Löser problem 6 (hårdkodade konstanter på flera ställen, risk
  för inkonsekvens vid commit-/modellbyte).
- **Filer som påverkas:** `run.sh`, `work_session.py`, `ssh_probe.py`, ny
  konfigfil.
- **Testplan:** Test att alla skript läser samma konfig; test att en ändrad
  commit i konfig slår igenom i alla skript utan kodändring.
- **Migreringsrisk:** Medel – konfigfilen måste skyddas (umask 077, som redan
  används i `run.sh`) och får inte innehålla hemligheter.
- **Beroenden:** Samordnas med Ändring 5.

## Rekommenderad ordning

1. **Ändring 1 (statuskonsolidering)** – ~1–2 h. Låg risk, ger omedelbar
   klarhet och är oberoende av övriga ändringar.
2. **Ändring 3 (loggrotation/rensning)** – ~1 h. Additivt, låg risk, stoppar
   disktillväxten tidigt.
3. **Ändring 2 (ett flock-lås)** – ~1–2 h. Låg risk, förbereder Ändring 5.
4. **Ändring 4 (gemensamt preflight-gränssnitt)** – ~2–3 h. Kan göras
   parallellt med 1–3.
5. **Ändring 6 (centraliserade konstanter)** – ~1 h. Förbereder Ändring 5.
6. **Ändring 5 (dela upp work_session.py)** – ~3–4 h. Högst risk, görs sist
   när lås och konfig är på plats.

Total uppskattning: ~9–13 h, exklusive granskning och eventuell omkörning av
de 22 offlineproven.

## Öppna frågor till användaren

1. Vilken statusfil ska vara auktoritativ? `current-status.json` har en annan
   struktur än `CURRENT-STATUS.md`/`HANDOFF.md` (som är byte-identiska). Ska
   JSON vara källan och markdown genereras, eller tvärtom?
2. Får äldre passkataloger och `turn-*.jsonl`-filer komprimeras/raderas, eller
   måste all historik bevaras för revision? (114 MiB/1534 filer växer.)
3. Ska `ssh-probe-launch.lock` och `work-launch.lock` tas bort helt, eller ska
   de behållas som separata flock-lås för att tillåta probe och work samtidigt?
   (I dag är det oklart om de ska vara ömsesidigt uteslutande.)
4. Ska de 10 preflight-skripten bevaras som körbara engångsmätningar (med
   hårdkodade budgetar) eller omvandlas till funktioner under ett gemensamt
   gränssnitt? Vissa har specifika sidoeffekter (rlimit, faulthandler,
   RSS-vakt) som måste bevaras exakt.
5. Är `gpt-6.1-sol` (hårdkodad i `work_session.py` rad 25) fortfarande rätt
   modell, eller ska modellvalet flyttas till konfig och kunna ändras utan
   kodändring?
6. Ska `published-urls.log` roteras via systemets `logrotate` (kräver
   root/systemkonfig) eller via ett eget skript i `~/autonomy` (utan root)?
