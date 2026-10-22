# Autonoma körningsskript

Dokumentation för `scripts/runner.py` och `scripts/verify_run.py`.

## Overview

`scripts/runner.py` kör en avgränsad uppgift från `<root>/AUTONOMOUS_TASK.md` i
en isolerad Git-worktree. En DeepSeek-modell föreslår ändringar via Tool Calls
(`read_file`, `write_file`, `edit_file`, `run_command`), varefter ändringarna
verifieras med rootens verifieringskommando och granskas av
`application.deepseek_review`. Endast vid `verdict=approve` skapas en commit.
`scripts/verify_run.py` tar sedan över: den slår upp körningen i
`RUN_HISTORY.json`, verifierar worktreen på nytt och mergar branchen in i den
branch du står på. Inget av skripten pushar. `verify_run.py` mergar in i
**aktuell branch**, men nekar alltid merge till `main`/`master` och till ett
okänt branchnamn (detached HEAD eller git-fel): steget `merge target`
misslyckas och ingen merge sker. En merge till `main` görs manuellt utanför
skriptet efter användarens uttryckliga godkännande. Kontrollera därför
`git branch --show-current` och stå på en arbetsbranch före körning.

## Flaggor för runner.py

`--root app|autonomy` väljer vilken projektrot körningen gäller (standard
`app`). Varje rot har egen uppgiftsfil, historik, rapportmönster, verifierings-
kommando och worktree-prefix, så använd rätt rot för att undvika att fel
projekt ändras.

`--fast` använder rotens `fast_verify_cmd` i stället för `verify_cmd` under
iterationerna. Använd det för snabbare återkoppling när en billig delmängd av
kontrollerna räcker. Flaggan påverkar bara agentens iterationer: den
fullständiga verifieringen görs ändå i `verify_run.py` **utan** `--fast` före
merge. `verify_run.py --fast` hoppar däremot över den (se nedan).

`--force` kör uppgiften även om en tidigare körning med samma innehåll i
uppgiftsfilen redan är `completed`. Använd det när uppgiften medvetet ska köras
om, till exempel efter en ändrad modell eller ett nytt försök.

`--dry-run` använder en fejkad klient som inte gör några API-anrop, så inga
kostnader uppstår. Använd det för att kontrollera worktree-skapande, rapporter
och historik innan en riktig körning.

`--clean` tar även bort worktrees och brancher för `completed`-körningar vid
uppstart. Använd det bara när du bestämt dig för att inte merga de körningarna,
eftersom de annars behövs för `verify_run.py`.

`--keep-failed` behåller worktrees från misslyckade körningar för manuell
inspektion. Använd det vid felsökning; annars städas icke-slutförda körningar
bort automatiskt.

## Flaggor för verify_run.py

Skriptet tar ett positionellt argument `<run>`: antingen dagens körnummer
(`3`) eller `datum_nummer` (`2026-10-21_3`). Värdet hämtas från `run`-fältet i
`<root>/RUN_HISTORY.json` och skrivs ut av `runner.py` som `Run: <datum>_<nr>`.
Endast körningar med `status=completed` och en commit kan verifieras.

`--root app|autonomy` väljer samma projektrot som körningen skapades för
(standard `app`). Historik, verifieringskommandon och worktree-sökvägar läses
från den rotens konfiguration.

`--dry-run` kör verifieringsstegen och kontrollerar även merge-målet, men
hoppar över själva mergen och städningen. Använd det för att granska en körning
innan den släpps in i den aktuella branchen: står du på `main`/`master` eller
på ett okänt branchnamn rapporterar `merge target` att en riktig körning skulle
nekas.

`--no-cleanup` behåller worktreen och branchen även efter lyckad merge. Använd
det när du vill inspektera resultatet eller branchen efteråt.

`--fast` hoppar över den fullständiga verifieringen i worktreen och kör bara
`fast_verify_cmd`. Skriptet vägrar `--fast` när aktuell branch är `main` eller
`master`, och även när branchnamnet inte kan läsas (detached HEAD eller
git-fel): steget `fast guard` misslyckas och ingen merge sker, eftersom branchen
annars skulle mergas innan `verify_cmd` körts i roten. På andra brancher skrivs
en explicit varning till output när en merge faktiskt är på väg att ske (inte
vid `--dry-run`): `WARNING: --fast skips the full verify in the worktree. The
branch is merged before verify_cmd runs in the root.` Efter merge körs alltid
`verify_cmd` i roten, men då har branchen redan mergats. Använd därför `--fast`
endast för utkast och arbetsbrancher: full `verify_cmd` måste köras och passera
före merge till en branch som kan nå `main`.

## Worktree-livscykel

1. `runner.py` skapar en worktree från `HEAD` på en ny branch
   (`development/run-<datum>_<nr>` för `app`, `autonomy-run-<datum>_<nr>` för
   `autonomy`) under `/home/web/seaparser/worktrees`.
2. Agenten ändrar filer i worktreen via Tool Calls; tempfiler städas bort.
3. Verifieringskommandot körs i worktreen, därefter granskningen. Vid
   `request_changes` skickas fynden tillbaka till agenten.
4. Vid `approve` skapas en commit i worktreen och körningen registreras som
   `completed` i `RUN_HISTORY.json`.
5. `verify_run.py` verifierar worktreen, kontrollerar att `HEAD` matchar
   commit i historiken och mergar branchen med `--no-ff` in i aktuell branch
   (aldrig `main`/`master`).
6. Efter merge körs `verify_cmd` i roten; därefter tas worktree och branch bort
   (om inte `--no-cleanup` eller `--dry-run`).

## Exempel

```bash
# Kör uppgiften med snabb verifiering under iterationerna
python -B -m scripts.runner --root app --fast

# Granska körning 3 från idag utan att merga
python -B -m scripts.verify_run --root app 3 --dry-run

# Verifiera fullt ut och merga körning 3 (kontrollera aktuell branch först)
git branch --show-current
python -B -m scripts.verify_run --root app 3
```
