"""Opt-in PostgreSQL checks using disposable transactional fixtures only."""
import argparse
import hashlib
import os
import select
import subprocess
import time
import uuid
from unittest.mock import patch
from infrastructure.settings import ROOT, load_database
from infrastructure.postgres import psql_environment
from scripts import migrate

PLAN = """Förberett, inte kört: rollback vid migrationsfel och avvisning av samtidig körning.
Slumpnamngivet testschema och egen låsnyckel; endast testegen historik.
DDL och INSERT körs i BEGIN/ROLLBACK; ingen COMMIT, DROP eller befintlig data.
Fel stänger anslutningen (rollback); separat läskontroll bekräftar städning.
--run kräver separat godkännande; projektets migrationslås/tabell används aldrig."""
COMMAND = ['psql', '-X', '-w', '-qAt', '--set=ON_ERROR_STOP=1', '--file=-']


def fixture_sql(schema, lock, *, fail=False):
    if not schema.startswith('seaparser_it_') or not schema[13:].isalnum():
        raise ValueError('Ogiltigt testnamn')
    if not isinstance(lock, int) or not 0 < lock < 2**63 or lock == migrate.LOCK:
        raise ValueError('Testet kräver en egen låsnyckel')
    baseline = 'CREATE SCHEMA ' + schema + ';\n' + (ROOT / 'migrations/0001_baseline.sql').read_text()
    files = [(migrate.FIRST, hashlib.sha256(baseline.encode()).hexdigest(), baseline)]
    if fail:
        content = """SELECT 'fixture_history_ready' WHERE
 (SELECT count(*) FROM public.seaparser_migrations) = 1;
DO $test$ BEGIN RAISE EXCEPTION 'fixture_deliberate_failure'; END $test$;"""
        files.append(('0002_fixture_failure', hashlib.sha256(content.encode()).hexdigest(), content))
    # Test-only substitution; normal CLI has no schema, lock or directory override.
    with patch.object(migrate, 'migrations', return_value=files), patch.object(migrate, 'LOCK', lock):
        sql = migrate.migration_sql()
    return sql.replace('public.seaparser_migrations', schema + '.seaparser_migrations')


def run_sql(env, sql):
    return subprocess.run(COMMAND, input=sql, env=env, capture_output=True,
                          text=True, timeout=40)


def assert_safe_database(env):
    # DDL event triggers could modify existing objects or cause external effects.
    result = run_sql(env, "BEGIN READ ONLY; SELECT current_database() = 'seaparser' "
                     "AND current_user = 'seaparser' AND NOT EXISTS "
                     "(SELECT 1 FROM pg_event_trigger WHERE evtenabled <> 'D'); ROLLBACK;")
    if result.returncode or result.stdout.strip() != 't':
        raise ValueError('Test kräver seaparser-identitet och frånvaro av aktiva DDL-eventtriggers')


def assert_clean(env, schema):
    result = run_sql(env, "BEGIN READ ONLY;\nSELECT NOT EXISTS (SELECT 1 FROM pg_namespace "
                     f"WHERE nspname = '{schema}');\nROLLBACK;")
    if result.returncode or result.stdout.strip() != 't':
        raise ValueError('Städning av testschema kunde inte verifieras; stoppa och inventera')


def rollback_check(env, schema, lock):
    assert_clean(env, schema)
    result = run_sql(env, 'BEGIN;\n' + fixture_sql(schema, lock, fail=True))
    # Check the specific intended failure, not an arbitrary connection/SQL error.
    if (result.returncode == 0 or 'fixture_history_ready' not in result.stdout.splitlines()
            or 'fixture_deliberate_failure' not in result.stderr):
        raise ValueError('Det avsiktliga migrationsfelet kunde inte verifieras')
    assert_clean(env, schema)


def concurrency_check(env, schema, lock):
    assert_clean(env, schema)
    holder = subprocess.Popen(COMMAND, env=env, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        holder.stdin.write(f"BEGIN;\nSET LOCAL idle_in_transaction_session_timeout = '20s';\n"
                           f"SELECT pg_advisory_xact_lock({lock});\nSELECT 'fixture_lock_ready';\n")
        holder.stdin.flush()
        # One psql result line per read avoids buffered read-ahead losing readiness.
        deadline = time.monotonic() + 10
        ready = False
        buffer = b''
        while time.monotonic() < deadline:
            readable, _, _ = select.select([holder.stdout], [], [], max(0, deadline - time.monotonic()))
            if not readable:
                break
            chunk = os.read(holder.stdout.fileno(), 4096)
            if not chunk:
                break
            buffer += chunk
            if b'fixture_lock_ready\n' in buffer:
                ready = True
                break
        if not ready:
            raise ValueError('Låshållarens beredskap kunde inte verifieras')
        sql = fixture_sql(schema, lock)
        result = run_sql(env, 'BEGIN;\n' + sql + '\nROLLBACK;')
        if result.returncode == 0 or 'Migration pågår redan' not in result.stderr:
            raise ValueError('Samtidig migration avvisades inte av förväntat låsskydd')
        assert_clean(env, schema)
        holder.communicate(input='ROLLBACK;\n', timeout=5)
        if holder.returncode:
            raise ValueError('Låshållaren avslutades inte korrekt')
        # Prove release: the same runner succeeds, then explicitly rolls back.
        result = run_sql(env, 'BEGIN;\n' + sql + '\nROLLBACK;')
        if result.returncode or '|applied|' not in result.stdout:
            raise ValueError('Migration efter låssläpp kunde inte verifieras')
        assert_clean(env, schema)
    finally:
        if holder.poll() is None:
            holder.terminate()
            try:
                holder.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                holder.kill()
                holder.communicate(timeout=5)
        for stream in (holder.stdin, holder.stdout, holder.stderr):
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=PLAN)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print(PLAN)
        return
    try:
        env = psql_environment(load_database('development'))
        assert_safe_database(env)
        for check in (rollback_check, concurrency_check):
            schema = 'seaparser_it_' + uuid.uuid4().hex
            lock = uuid.uuid4().int % (2**63 - 1) + 1
            try:
                check(env, schema, lock)
            finally:
                assert_clean(env, schema)
        print('Två isolerade PostgreSQL-kontroller och städning verifierade')
    except (OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit('Integrationstest misslyckades; privata detaljer dolda. '
                         'Ingen automatisk DROP eller reparation körs.') from None


if __name__ == '__main__':
    main()
