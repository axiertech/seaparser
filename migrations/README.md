# SQL-migrationer

Numrerade SQL-filer är oföränderliga efter tillämpning. Nya ändringar får ny fil.
`python -B -m scripts.migrate --environment test` granskar utan anslutning.
`--apply` kräver godkänd databasåtkomst och psql. Verktyget använder en transaktion,
advisory lock, SHA-256-kontroll och versionshistorik. Första migrationen skapar
bara ett schema. Inga produktdata eller PostGIS-installation ingår.

Varje framtida migration ska granskas för transaktionsstöd; CREATE INDEX
CONCURRENTLY och psql-metakommandon hör inte hemma här. Automatisk downgrade
saknas. Återställning kräver godkänd backup/restore eller korrigerande migration.
Testa omkörning och ändrad checksumma i isolerad databas före serverkörning.
