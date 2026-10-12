"""Transactional, checksum-verified migrations; no private values in output."""
import argparse
import hashlib
import re
import subprocess
from infrastructure.settings import ROOT, load_database

LOCK = 73210412
FIRST = "0001_baseline"


def migrations():
    result = []
    for path in sorted((ROOT / "migrations").glob("[0-9]*.sql")):
        if not re.fullmatch(r"[0-9]{4}_[a-z0-9_]+", path.stem):
            raise ValueError("Ogiltigt migrationsnamn")
        data = path.read_bytes()
        result.append((path.stem, hashlib.sha256(data).hexdigest(), data.decode()))
    if not result or result[0][0] != FIRST:
        raise ValueError("Första migrationen saknas")
    return result


def migration_sql(*, status=False):
    files = migrations()
    sql = [fr"""SET LOCAL statement_timeout = '30s';
DO $guard$ BEGIN
 IF current_database() <> 'seaparser' OR current_user <> 'seaparser' THEN
  RAISE EXCEPTION 'Fel databasidentitet';
 END IF;
 IF NOT pg_try_advisory_xact_lock({LOCK}) THEN
  RAISE EXCEPTION 'Migration pågår redan';
 END IF;
END $guard$;
SELECT to_regclass('public.seaparser_migrations') IS NOT NULL AS tracked \gset
\if :tracked
"""]
    # Unknown versions and modified applied files must fail before any write.
    sql.append("DO $guard$ BEGIN IF NOT EXISTS (SELECT 1 FROM public.seaparser_migrations WHERE version = '0001_baseline') THEN RAISE EXCEPTION 'Baslinje saknas i befintlig historik'; END IF; END $guard$;")
    known = ",".join(f"'{version}'" for version, _, _ in files)
    sql.append(f"""DO $guard$ BEGIN
 IF EXISTS (SELECT 1 FROM public.seaparser_migrations WHERE version NOT IN ({known})) THEN
  RAISE EXCEPTION 'Okänd tillämpad migration';
 END IF;
END $guard$;""")
    for version, digest, _ in files:
        sql.append(f"""DO $guard$ BEGIN
 IF EXISTS (SELECT 1 FROM public.seaparser_migrations
 WHERE version = '{version}' AND checksum <> '{digest}') THEN
  RAISE EXCEPTION 'Ändrad tillämpad migration';
 END IF;
END $guard$;""")
    sql.append("\\else")
    if not status:
        sql.append(files[0][2])
    sql.append("\\endif")
    for version, digest, content in files:
        sql.append("SELECT to_regclass('public.seaparser_migrations') IS NOT NULL AS tracked \\gset\n\\if :tracked")
        sql.append(f"SELECT EXISTS (SELECT 1 FROM public.seaparser_migrations WHERE version = '{version}') AS applied \\gset\n\\else\n\\set applied false\n\\endif\n\\if :applied")
        sql.append(f"SELECT '{version}', 'applied', checksum, applied_at FROM public.seaparser_migrations WHERE version = '{version}';")
        sql.append("\\else")
        if status:
            sql.append(f"SELECT '{version}', 'pending';")
        else:
            if version != FIRST:
                sql.append(content)
            sql.append(f"INSERT INTO public.seaparser_migrations(version, checksum) VALUES ('{version}', '{digest}');")
            sql.append(f"SELECT '{version}', 'applied', checksum, applied_at FROM public.seaparser_migrations WHERE version = '{version}';")
        sql.append("\\endif")
    return "\n".join(sql)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True, choices=("development",))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--status", action="store_true")
    args = parser.parse_args()
    try:
        sql = migration_sql(status=args.status)
        if not (args.apply or args.status):
            for version, digest, _ in migrations():
                print(f"{version} {digest}")
            print("Plan verifierad; ingen konfiguration läst eller anslutning gjord")
            return
        db = load_database(args.environment)
        env = {"PATH": "/usr/bin:/bin", "PGHOST": db.host,
               "PGPORT": str(db.port), "PGDATABASE": db.name, "PGUSER": db.user,
               "PGPASSWORD": db.password, "PGCONNECT_TIMEOUT": "5"}
        if args.status:
            env["PGOPTIONS"] = "-c default_transaction_read_only=on"
        result = subprocess.run(
            ["psql", "-X", "-w", "-qAt", "--set=ON_ERROR_STOP=1",
             "--single-transaction", "--file=-"], input=sql, text=True,
            env=env, capture_output=True, check=True, timeout=40)
        print(result.stdout.replace(db.password, "[dolt]"), end="")
    except (OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit("Migrationskontroll misslyckades; privata detaljer dolda") from None


if __name__ == "__main__":
    main()
