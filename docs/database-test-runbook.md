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
bort. Actions är låsta till granskade fullständiga SHA; se actions-review.md.
Ingen CI-körning på GitHub är verifierad.

Framtida databastester ska vara uttryckligen valda. Använd BEGIN/ROLLBACK och
uniknamngivna testegna objekt eller tillfälliga tabeller. Kör aldrig TRUNCATE,
DELETE utan avgränsning, DROP av befintliga objekt eller en återställning av databasen.
Rollback återställer inte sekvensvärden eller externa sidoeffekter: ändra därför
inte befintliga rader eller sekvenser. Testegna objekt ska återställas även vid fel;
behörigheter och eventuella triggers måste granskas före körning. Integrationstester är förberedda enligt planen nedan men har inte körts.

Första migrationen är godkänd och tillämpad; se migrations/README.md och
docs/progress.md. `make migration-plan` läser ingen privat konfiguration eller
databas. Framtida --apply kräver separat uttryckligt godkännande och granskning.
Inför drift ska utveckling och drift separeras och en ny driftroll med minsta
rättigheter skapas. Utvecklingsrollen eller dess lösenord får inte återanvändas i drift.

## TLS för alla databasverktyg

DB_SSLMODE har standard require och accepterar endast require, verify-ca och
verify-full. disable/allow/prefer och tomt explicit värde avvisas. TCP krävs;
Unix-sockets avvisas eftersom libpq ignorerar sslmode för dem. Diagnostik,
migration/status och de förberedda integrationstesterna använder samma rena
libpq-miljö med PGSSLMODE, PGSSLROOTCERT när angiven och PGGSSENCMODE=disable.
Det senare förhindrar att GSS-kryptering väljs framför TLS. Ärvt PGSERVICE,
PGOPTIONS eller PGSSLMODE kan inte försvaga anslutningen. require ger ingen
okrypterad fallback men garanterar inte servernamnets identitet.

För verify-full anges privat (exempelvärden, ingen filändring genomförd):

```dotenv
DB_HOST=db.example.invalid
DB_SSLMODE=verify-full
DB_SSLROOTCERT=/home/web/seaparser/config/trusted-db-ca.pem
```

Servernamnet måste gå att slå upp och matcha certifikatets SAN. Använd det riktiga
certifierade namnet; ersätt inte med 127.0.0.1 om certifikatet inte täcker den
adressen. CA-filen ska vara en betrodd CA-kedja från en verifierad källa, med
absolut sökväg utanför Git. verify-ca kräver också explicit CA men verifierar inte
namnet. Laddaren läser inte CA-filens innehåll; libpq kontrollerar fil/kedja/namn
vid anslutning och nekar fel. Ingen server-TLS eller privat konfiguration ändras.
TLS-handshake och certifikat har inte verifierats mot servern i denna leverans.

Officiella referenser granskade 2026-10-12:
[libpq SSL](https://www.postgresql.org/docs/18/libpq-ssl.html) och
[anslutningsparametrar inklusive GSS](https://www.postgresql.org/docs/18/libpq-connect.html).

## Förberedda PostgreSQL-integrationstester – inte körda

Offlineplan: `.venv/bin/python -B -m scripts.verify_migrations_integration`.
Framtida uttryckligen godkänd körning använder samma kommando med --run.
Ingen automatisk körning i make check eller CI, ingen separat databas/roll/lösenord.

Varje fall använder seaparser-identiteten men genererar ett unikt
seaparser_it_<UUID>-schema och en slumpad separat 64-bitars advisory-låsnyckel.
Verktyget återanvänder migrationsgeneratorn med testegna migrationer i minnet och
ersätter historiktabellens referenser till testschemat. Normal migrations-CLI har
inga sådana overrides. Ingen produktmigration efter baslinjen laddas/körs.
Projektets public.seaparser_migrations, spatial_ref_sys och migrationslås berörs inte.
Skrivskyddad förkontroll kräver seaparser-identitet och att inga aktiva DDL-
eventtriggers finns; sådana triggers kan påverka befintliga objekt eller externa
system även vid testegen DDL och därför stoppar testet före skrivning.
Frånvaron av testschemat kontrolleras före start. CREATE SCHEMA utan IF NOT EXISTS
stoppar även en namnkonflikt mellan kontroll och skapande; inget befintligt tas över.

1. Rollback: BEGIN, skapa testschema/historik och registrera testbaslinjen, kontrollera
   att historikraden finns och framkalla ett känt fel i andra testmigrationen.
   Psql med ON_ERROR_STOP stänger sessionen utan COMMIT. Ny lässession måste visa
   att testschemat försvunnit. Ett anslutningsfel räknas inte som godkänt rollbacktest.
2. Samtidighet: en separat psql-session tar testets transaktionslås och ger en
   beredskapsmarkör. En andra migrationskörning måste ge just låsavvisningen innan
   DDL. Låshållaren gör ROLLBACK; samma migration måste därefter lyckas och avslutas
   med explicit ROLLBACK. Frånvaron av testschemat kontrolleras igen.

Alla testskrivningar är transaktionsbundna. Inga befintliga rader, sekvenser,
behörigheter eller triggers används; ingen COMMIT, DROP, TRUNCATE eller cleanup-DML.
SQL/client-timeout och låshållarens idle-in-transaction-timeout begränsar körning.
Vid klienttimeout dödas/stängs psql; låshållaren avslutas även vid undantag så att
PostgreSQL rullar tillbaka. Slutlig läskontroll försöks även efter fel. Kan städning
inte verifieras rapporteras misslyckande; inventera skrivskyddat före nytt försök.
Ingen automatisk reparation eller DROP. Backend-städning efter avbruten anslutning
måste bekräftas av läskontrollen; den förutsätts inte ha verifierats här.
