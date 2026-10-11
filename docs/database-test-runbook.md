# Testdatabas och CI – körunderlag 2026-10-12

Alla databassteg nedan är förberedda och **inte utförda**. De kräver separat
användargodkännande. Administratören utför serverstegen med sitt befintliga
administratörskonto; utvecklingsagenten använder seaparser utan sudo.
Antagande: lokal PostgreSQL, port 5432, TCP 127.0.0.1. Administratören måste
bekräfta kluster/port först; utvecklingens privata konfiguration används aldrig.

## Vad databasadministratören ska köra

1. Inventera befintliga roller/databaser, HBA och aktiv serverversion i sin
   befintliga administrativa psql-session. Ingen utskrift av lösenord krävs:

   ```sql
   SHOW server_version;
   SHOW port;
   SHOW hba_file;
   SELECT rolname FROM pg_roles WHERE rolname = 'seaparser_test';
   SELECT datname FROM pg_database WHERE datname = 'seaparser_test';
   ```

   De två sista frågorna ska ge noll rader. Befintliga objekt kräver särskild
   granskning; filen tar inte över eller raderar dem.

2. I administratörens psql-session, ansluten till underhållsdatabasen postgres:

   ```psql
   \set ON_ERROR_STOP on
   \i /home/web/seaparser/app/deploy/test-database.sql
   SET password_encryption = 'scram-sha-256';
   \password seaparser_test
   ```

   Kör utan övergripande transaktion: CREATE DATABASE kan inte ligga i en sådan.
   Filen växlar därefter till seaparser_test som administratören, hårdgör public
   och lämnar bara nödvändiga schemarättigheter. Lösenord anges i psql:s dolda
   prompt, aldrig som SQL-literal, shellargument, Git-fil eller i arbetsloggen.
   Vid delvis misslyckande: inventera igen; återkör inte blint.

3. Administratören infogar [HBA-blocket](../deploy/test-pg_hba.conf.example)
   **före alla bredare matchande regler och inkluderade filer**, i filen som
   SHOW hba_file pekar ut. En enda tillåtande rad: testdatabas/testroll över
   127.0.0.1/32 med scram-sha-256. Därefter reject för testrollen över sockets,
   all IPv4 och all IPv6. Ingen fjärråtkomst, trust, IPv6-tillåtelse eller ändring
   av listen_addresses behövs. Blocket berör bara seaparser_test.

   Kontroll och reload i administratörens session:

   ```sql
   SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;
   SELECT pg_reload_conf();
   SELECT line_number, type, database, user_name, address, auth_method
   FROM pg_hba_file_rules WHERE 'seaparser_test' = ANY(user_name)
   ORDER BY line_number;
   ```

   Första frågan ska ge noll rader och reload true. Granska ordningen även mot
   tidigare all-regler. Slutlig anslutningsverifiering behövs: reload-resultat
   bevisar inte att rätt regel matchar.

## Minsta behörigheter

Serverrollen seaparser_test: LOGIN, inga medlemskap, ingen superuser,
CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS eller INHERIT. Den äger bara den
nya testdatabasen och sina testobjekt. CONNECT och CREATE i egen databas behövs
för migrationerna. TEMP tas bort. USAGE/CREATE i public behövs för
migrationshistoriken. Baslinjen skapar schema seaparser; ägaren får där rätt
att skapa/ändra sina tabeller. Inga generella rättigheter till utvecklingsdata,
PostGIS-installation eller andra databaser behövs.

PUBLIC får inga rättigheter i testdatabasen/public-schemat. Utvecklingsdatabasens
ACL ändras inte. Den kan fortfarande ha PUBLIC CONNECT: ett REVOKE bara från
testrollen hade då inte räckt. HBA:s uttryckliga reject är därför obligatoriskt.
Administratören ska inte ge rollen några medlemskap senare. Testrollen får DDL
för migrationer inom testdatabasen; en framtida produktionsroll måste vara separat.

## Exakta kommandon för senare verifiering

Kör från /home/web/seaparser/app som seaparser, först efter godkännande.
`env -i` tar bort ärvda PG*-inställningar; psql -X läser inte .psqlrc.
-W läser lösenord i dold prompt. Kommandona använder bara offentliga testnamn.

Positiv identitets- och behörighetskontroll (ska sluta med exit 0):

```bash
cd /home/web/seaparser/app
env -i PATH="$PATH" psql -X -W -h 127.0.0.1 -p 5432 -U seaparser_test -d seaparser_test --set=ON_ERROR_STOP=1 --single-transaction --file=deploy/verify-test-database.sql
```

Negativ kontroll med samma testlösenord (ska nekas av HBA):

```bash
env -i PATH="$PATH" psql -X -W -h 127.0.0.1 -p 5432 -U seaparser_test -d seaparser --set=ON_ERROR_STOP=1 --command='SELECT 1'
```

Godkänt resultat är uttryckligt HBA-reject för utvecklingsdatabasen, inte bara
ett valfritt fel eller fel lösenord. Om anslutningen lyckas: stoppa innan
migration, rapportera isoleringsfelet. Positiv kontroll måste först ha lyckats.
Varken återställning eller databasradering ingår.

Migrationsplan kräver ingen anslutning:

```bash
.venv/bin/python -B -m scripts.migrate --environment test
```

Migration och omkörning, med testlösenord tillfälligt i processmiljön:

```bash
# Kör i bash med tracing avstängd. Läs aldrig app.env med source.
set +x
unset TEST_DB_HOST TEST_DB_PORT TEST_DB_NAME TEST_DB_USER
read -r -s -p 'Testdatabasens lösenord: ' TEST_DB_PASSWORD
printf '\n'
export TEST_DB_PASSWORD
APP_ENV=test .venv/bin/python -B -m scripts.migrate --environment test --apply
APP_ENV=test .venv/bin/python -B -m scripts.migrate --environment test --apply
unset TEST_DB_PASSWORD
```

Båda kommandona ska ge exit 0; om första misslyckas, stoppa och undersök före
omkörning. TEST_DB_HOST/PORT/NAME/USER lämnas osatta och får de versionshanterade
teststandarderna; rensa eventuella sådana ärvda variabler före körning.
Versionskontroll efteråt:

```bash
env -i PATH="$PATH" psql -X -W -h 127.0.0.1 -p 5432 -U seaparser_test -d seaparser_test --set=ON_ERROR_STOP=1 --command='SELECT version, checksum FROM public.seaparser_migrations ORDER BY version'
```

För denna baslinje ska exakt en rad, 0001_baseline, finnas med SHA-256 som matchar
`sha256sum migrations/0001_baseline.sql`. Omkörning ska behålla samma historik.
Ändra inte migrationsfilen på servern för checksumprov; CI gör det i en engångskopia.

## CI-jobb, behörigheter och körning

.github/workflows/checks.yml körs vid push, pull_request och manuellt
workflow_dispatch. Push är fortfarande förbjuden utan godkännande. Konton för
Actions och kostnad/kvot ska kontrolleras innan aktivering. Ingen serverrunner,
serverns app.env eller repository secrets används. Båda jobben har 10 minuters
maxtid. GITHUB_TOKEN har endast contents: read; checkout sparar inte credentials.
Inga deploy-, write-, OIDC-, paketpublicerings- eller PR-kommentarsrättigheter.

| Jobb | Miljö och arbete | Databasrättigheter |
| --- | --- | --- |
| offline | Ubuntu 24.04, Python 3.14.4 och Node 22.22.1; syntax/TOML/domängränser, 38 prototyptester, 4 konfigurationstester, frontendsyntax och node:test | Ingen databas eller anslutning |
| migrations | Egen tillfällig postgres:17-service; migration, omkörning, därefter checksumändring som måste nekas | Containerns bootstraproll är superuser enbart i engångscontainern; ingen åtkomst till servern |

CI:s migrationsjobb verifierar SQL/checksumma, **inte serverrollens minsta
behörigheter eller HBA-isolering**. Dessa provas separat med kommandona ovan.
CI använder nu rörliga action-taggar och PostgreSQL-taggen; granska officiella
revisioner och lås action-SHA/image-digest före aktivering. Runner/psql och
Python-versionens tillgänglighet är inte verifierad genom en faktisk CI-körning.
Frontend har noll produkttester tills första komponenten införs.

Officiella referenser granskade 2026-10-12:
[PostgreSQL HBA](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html),
[PostgreSQL GRANT](https://www.postgresql.org/docs/current/sql-grant.html),
[GitHub workflow-syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Lokal miljöstatus och nästa steg

npm ci med https://registry.npmjs.org lyckades; låsfilen har inga externa paket.
make prepare-python misslyckades eftersom Python 3.14 saknar ensurepip.
.venv är delvis skapad och får inte beskrivas som färdiginstallerad.
Administratören behöver tillhandahålla python3.14-venv (eller motsvarande
ensurepip-stöd för befintlig Python); agenten installerar inget systempaket.
När systemstödet finns kan agenten återköra make prepare-python enligt mandatet.
psql finns i /usr/bin/psql; inga anslutningar är gjorda.
