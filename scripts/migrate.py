"""Versionshanterade SQL-migrationer via psql; explicit miljö och körflagga."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
from infrastructure.settings import ROOT, load_database


def migration_sql():
    statements = ["SELECT pg_advisory_xact_lock(73210412);",
                  "CREATE TABLE IF NOT EXISTS public.seaparser_migrations (version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now());"]
    for path in sorted((ROOT / "migrations").glob("[0-9]*.sql")):
        version = path.stem
        if not all(c.isalnum() or c == "_" for c in version):
            raise ValueError("Ogiltigt migrationsnamn")
        content = path.read_text()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        statements.append(fr"""
SELECT EXISTS (SELECT 1 FROM public.seaparser_migrations WHERE version = '{version}') AS applied \gset
DO $guard$ BEGIN
 IF EXISTS (SELECT 1 FROM public.seaparser_migrations WHERE version = '{version}' AND checksum <> '{digest}') THEN
  RAISE EXCEPTION 'Ändrad tillämpad migration';
 END IF;
END $guard$;
\if :applied
\else
{content}
INSERT INTO public.seaparser_migrations(version, checksum) VALUES ('{version}', '{digest}');
\endif
""")
    return "\n".join(statements)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True, choices=("development", "test"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sql = migration_sql()
    if not args.apply:
        print("Migrationer förberedda; ingen konfiguration läst eller anslutning gjord")
        return
    keys = ("TEST_DB_HOST", "TEST_DB_PORT", "TEST_DB_NAME", "TEST_DB_USER", "TEST_DB_PASSWORD", "APP_ENV")
    variables = {k: os.environ[k] for k in keys if k in os.environ} if args.environment == "test" else None
    try:
        db = load_database(args.environment, variables=variables)
        # Ingen ärvd PGDATABASE, PGSERVICE, PGOPTIONS eller privat URL.
        env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
        env.update(PGHOST=db.host, PGPORT=str(db.port), PGDATABASE=db.name,
                   PGUSER=db.user, PGPASSWORD=db.password, PGCONNECT_TIMEOUT="5")
        guard = f"""DO $identity$ BEGIN
 IF current_database() <> '{db.name}' OR current_user <> '{db.user}' THEN
  RAISE EXCEPTION 'Fel databasidentitet';
 END IF;
END $identity$;
"""
        subprocess.run(["psql", "-X", "--no-password", "--set=ON_ERROR_STOP=1", "--single-transaction", "--file=-"],
                       input=guard + sql, text=True, env=env, capture_output=True, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError):
        raise SystemExit("Migration misslyckades; detaljer dolda för att skydda konfiguration") from None
    print("Migrationer tillämpade och versionskontrollerade")


if __name__ == "__main__":
    main()
