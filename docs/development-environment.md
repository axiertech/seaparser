# Kontrollerad utvecklingsmiljö – förslag 2026-10-12

## Omfattning och antaganden

Pythonprototypen använder endast standardbiblioteket. Ingen frontend, API eller
produktdatabasmodell finns. Därför låses nu en tom beroendegraf i
requirements.lock och frontend/package-lock.json. Det är inte en låsning av
framtida FastAPI/React/editor. Python 3.14.4, Node 22.22.1 och npm 9.2.0 har
verifierats lokalt; versionerna är baslinje, inte påstående om senaste version.
Inget installerades. Officiella versioner/licenser ska verifieras före varje
framtida installation. Editorval kräver kravens fullständiga utvärdering.

Python isoleras i .venv med system-site-packages avstängt (venv-standard).
Frontendberoenden placeras i frontend/node_modules via npm ci, utan globala
installationer. Verktygsversioner finns i .python-version, .nvmrc och package.json.
pyproject.toml beskriver projektet; körning sker från projektrot utan paketering.
Inga tredjepartsverktyg krävs för nuvarande tester. När beroenden tillkommer:
granskade exakta versioner och transitive hash-lås för Python, npm-lås för frontend;
uppdatera samtidigt scripts/check.py som nu uttryckligen bevakar den tomma grafen.

## Konfiguration och separation

settings/development.toml och settings/test.toml innehåller offentliga standarder.
Utveckling läser endast kända nycklar i /home/web/seaparser/config/app.env via
infrastructure/settings.py, aldrig genom shell source. Format: KEY=value med
valfri hel citering, inga export-rader, interpolationer eller inline-kommentarer.
APP_ENV kontrolleras om det finns; tomma nödvändiga värden avvisas.

Test läser aldrig denna fil, aldrig DB_* eller DATABASE_URL som fallback.
Testlösenord måste lämnas explicit som TEST_DB_PASSWORD. Testdatabas och roll
måste båda vara seaparser_test; utveckling kräver seaparser/seaparser.
Felmeddelanden och objektvisning döljer lösenord. scripts/config_presence.py
visar bara kända nycklar och om värden finns. Alla sex förväntade värden finns;
anslutning, autentisering och verkliga databasvärden är inte verifierade.

Applikationsskydd räcker inte för godtycklig framtida SQL-kod. Separat testroll,
separata lösenord, inga rollmedlemskap och serverns pg_hba-begränsningar
krävs som andra barriär. deploy/test-database.sql är ett granskningsunderlag för
administratören. Återanvänd inte utvecklingsrollen i tester. Ingen rätt att skapa
roller/databaser eller PostGIS behövs för vanlig utveckling/testkörning.

## Migrationer och kontroller

scripts/migrate.py använder psql, explicit miljö, verklig identitetskontroll,
transaktion, lås och checksumhistorik. Utan --apply görs ingen anslutning.
Anslutningsfel döljs; psql får inga lösenord i argumenten. Migrationer versionshanteras
i migrations/. Baslinjen skapar bara schema. PostGIS krävs inte för denna migration.
Migreringsroll behöver CONNECT samt CREATE på sin databas och ägarskap över
skapade objekt. Framtida driftroll ska få mindre rättigheter än migreringsrollen.

Enligt godkänt mandat: `make prepare-python`, därefter `make check`.
Nu kan befintlig Python köra `python3 -B -m scripts.check` utan installation.
Kontrollerna omfattar syntax, TOML, beroendebas, tillåtna domänimporter och
kravbaserade unittest-tester. Detta är en grundkontroll, inte full lint/typecheck.
Frontend kör syntax och node:test men har ännu noll produkttester.

GitHub Actions använder GitHub-hostade runners, inga serverhemligheter eller
self-hosted runner. Separat tillfällig PostgreSQL testar migration, omkörning och
ändrad checksumma. CI-lösenordet är endast syntetiskt och gäller engångscontainern.
CI-rollen är containerns bootstraproll; serverrollen ska sakna superuser.
Actions-taggar och postgres:17 är rörliga: granska officiella revisioner och lås
SHA/digest före aktivering. CI är inte körd; tillgänglighet för Python-version,
psql och runner är ännu inte verifierad. Ingen CI-installation skedde lokalt.

## Godkänt mandat och kvarvarande gränser

Mandatet är nu dokumenterat i AGENTS.md: projektändringar, offlinekontroller,
lokala commits av egna granskade ändringar, .venv-installationer och npm ci är
godkända. Officiella register, versionskontroll och låsfiler krävs. Systempaket,
sudo, databasoperationer, privata filändringar och push ingår inte.

Administratörens steg, minsta behörigheter, exakta framtida verifieringskommandon
och CI-jobb beskrivs i [database-test-runbook.md](database-test-runbook.md).
Separat godkännande återstår för administratörens databas/HBA/lösenordsåtgärder,
agentens databasanslutning och testmigrationer samt push/CI-aktivering. Eventuell
saknad systemklient måste hanteras av administratör. Ingen ny paketinstallation
utöver nuvarande låsfiler förutsätts genom detta underlag.
