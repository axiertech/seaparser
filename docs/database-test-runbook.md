# Databasdiagnostik och tester – beslut 2026-10-12

Projektet har en utvecklingsmiljö. Databas och roll heter seaparser.
Ingen separat testdatabas, testroll eller testlösenord krävs eller ska skapas.
De tidigare administratörsunderlagen för testdatabas och HBA har tagits bort.

Skrivskyddad diagnostik är godkänd med projektrollen, utan administratörsuppgifter:

```bash
cd /home/web/seaparser/app
.venv/bin/python -B -m scripts.diagnose_database
```

Kommandot läser privat app.env som data, utan shell source. Det skriver inte ut
lösenord eller anslutningssträngar. psql körs med -X och en ren processmiljö,
read-only som sessionsstandard och BEGIN READ ONLY/ROLLBACK. Kontrollen läser
serveridentitet/version, PostGIS-extensionens version, rollflaggor/medlemskap,
databasägare samt databas-, schema- och tabellbehörigheter utan att läsa produktrader.
Serverns HBA ändras inte. CONNECT räcker för anslutning; schema USAGE och
objektprivilegier avgör dataåtkomst. CREATE behöver granskas för framtida migrationer,
men någon behörighetsändring görs inte av diagnostiken.

`make check` kör endast databasfria enhetstester och lokala kontroller.
GitHub Actions har endast offlinejobbet; det tidigare migrationsjobbet har tagits
bort. Ingen CI-körning är verifierad. Granska och lås actionrevisioner före aktivering.

Framtida databastester ska vara uttryckligen valda. Använd BEGIN/ROLLBACK och
uniknamngivna testegna objekt eller tillfälliga tabeller. Kör aldrig TRUNCATE,
DELETE utan avgränsning, DROP av befintliga objekt eller en återställning av databasen.
Rollback återställer inte sekvensvärden eller externa sidoeffekter: ändra därför
inte befintliga rader eller sekvenser. Testegna objekt ska återställas även vid fel;
behörigheter och eventuella triggers måste granskas före körning. Inga skrivande
integrationstester är införda eller körda i denna leverans.

Första migrationen är godkänd och tillämpad; se migrations/README.md och
docs/progress.md. `make migration-plan` läser ingen privat konfiguration eller
databas. Framtida --apply kräver separat uttryckligt godkännande och granskning.
Inför drift ska utveckling och drift separeras och en ny driftroll med minsta
rättigheter skapas. Utvecklingsrollen eller dess lösenord får inte återanvändas i drift.
