"""Offline checks of migration safety and bootstrap scope."""
import unittest
from unittest.mock import patch
from scripts.migrate import migration_sql, migrations


class MigrationTests(unittest.TestCase):
    def test_baseline_scope(self):
        files = migrations()
        self.assertEqual([f[0] for f in files], ['0001_baseline'])
        statements = '\n'.join(line for line in files[0][2].splitlines()
                               if not line.startswith('--'))
        self.assertEqual(statements.count(';'), 1)
        self.assertTrue(statements.startswith('CREATE TABLE public.seaparser_migrations'))
        self.assertNotIn('IF NOT EXISTS', statements)

    def test_status_never_writes(self):
        sql = migration_sql(status=True)
        for command in ('CREATE TABLE', 'INSERT INTO', 'UPDATE ', 'DELETE '):
            self.assertNotIn(command, sql)
        self.assertIn('pending', sql)
        self.assertIn('checksum <>', sql)

    def test_identity_lock_and_history_guards_precede_writes(self):
        sql = migration_sql()
        first_write = sql.index('CREATE TABLE')
        for guard in ('current_database()', 'current_user',
                      'pg_try_advisory_xact_lock', 'version NOT IN', 'checksum <>'):
            self.assertLess(sql.index(guard), first_write)

    def test_missing_baseline_rejected(self):
        with patch('scripts.migrate.ROOT') as root:
            root.__truediv__.return_value.glob.return_value = []
            with self.assertRaises(ValueError):
                migrations()
