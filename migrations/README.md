# SQL-migrationer

Numrerade SQL-filer är oföränderliga efter tillämpning. Nya ändringar får ny fil.

- `.venv/bin/python -B -m scripts.migrate --environment development`: offlineplan.
- Samma kommando med `--status`: skrivskyddad status, version/checksum/tid eller pending.
- Samma kommando med `--apply`: tillämpa väntande migrationer efter separat godkännande.

Första migrationen skapar endast public.seaparser_migrations och registrerar sin
version, SHA-256 och tid. Inget schema, produktdata eller PostGIS-objekt skapas
eller ändras. Baslinjen får inte återanvända en befintlig, oregistrerad tabell.

Verktyget använder en transaktion för hela körningen. Identitet måste vara databas
och roll seaparser. Transaktionsbundet advisory try-lock (73210412) avvisar samtidig
körning, även statuskontroll. Alla körningar måste använda detta verktyg; låset
hindrar inte manuell SQL. Ändrade checksummor och okända tillämpade versioner
avvisas före skrivning. Redan tillämpade migrationer hoppas över utan UPDATE.
Status använder read-only-transaktion och skapar inte historiktabellen.
Timeout begränsar SQL till 30 s och klienten till 40 s; fel ger rollback.

Framtida SQL ska stödja transaktioner och granskas före körning. Transaktionsstyrning,
CREATE INDEX CONCURRENTLY och psql-metakommandon får inte användas i filerna.
Automatisk downgrade saknas. Återställning kräver separat godkännande.
Användaren godkände endast första migrationen i utvecklingsdatabasen 2026-10-12.
