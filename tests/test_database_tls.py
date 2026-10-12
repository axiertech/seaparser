"""TLS policy and both CLI call sites, without private config or connections."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from infrastructure.settings import load_database, read_env
from infrastructure.postgres import psql_environment
from scripts import migrate, diagnose_database


class DatabaseTLSTests(unittest.TestCase):
    def settings(self, **values):
        return load_database('development', variables={'DB_PASSWORD': 'synthetic', **values})

    def test_secure_default_and_modes(self):
        self.assertEqual(self.settings().sslmode, 'require')
        for mode in ('require', 'verify-ca', 'verify-full'):
            db = self.settings(DB_SSLMODE=mode, DB_SSLROOTCERT='/synthetic/ca.pem')
            env = psql_environment(db)
            self.assertEqual(env['PGSSLMODE'], mode)
            self.assertEqual(env['PGSSLROOTCERT'], '/synthetic/ca.pem')
            self.assertEqual(env['PGGSSENCMODE'], 'disable')

    def test_downgrades_socket_bypass_and_missing_ca_rejected(self):
        for values in ({'DB_SSLMODE': 'disable'}, {'DB_SSLMODE': 'allow'},
                       {'DB_SSLMODE': 'prefer'}, {'DB_SSLMODE': ''},
                       {'DB_SSLMODE': 'verify-full'}, {'DB_SSLMODE': 'verify-ca'},
                       {'DB_HOST': '/tmp'}, {'DB_HOST': '@socket'},
                       {'DB_HOST': 'localhost,/tmp'}, {'DB_SSLROOTCERT': 'relative.pem'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.settings(**values)

    def test_file_reads_tls_keys_as_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example'
            path.write_text('DB_SSLMODE=verify-full\nDB_SSLROOTCERT=/synthetic/ca.pem\n')
            self.assertEqual(read_env(path)['DB_SSLMODE'], 'verify-full')
            self.assertEqual(read_env(path)['DB_SSLROOTCERT'], '/synthetic/ca.pem')

    def test_no_inherited_libpq_overrides(self):
        with patch.dict(os.environ, {'PGSSLMODE': 'disable', 'PGSERVICE': 'other',
                                     'PGDATABASE': 'other', 'PGOPTIONS': 'unsafe'}):
            env = psql_environment(self.settings(), read_only=True)
        self.assertNotIn('PGSERVICE', env)
        self.assertEqual(env['PGSSLMODE'], 'require')
        self.assertEqual(env['PGDATABASE'], 'seaparser')
        self.assertIn('default_transaction_read_only=on', env['PGOPTIONS'])

    def test_database_tools_pass_explicit_tls(self):
        db = self.settings(DB_SSLMODE='verify-full', DB_SSLROOTCERT='/synthetic/ca.pem')
        for flag in ('--apply', '--status'):
            with patch.object(migrate, 'load_database', return_value=db), \
                 patch('sys.argv', ['migrate', '--environment', 'development', flag]), \
                 patch.object(migrate.subprocess, 'run', return_value=SimpleNamespace(stdout='')) as run:
                migrate.main()
                self.assertEqual(run.call_args.kwargs['env']['PGSSLMODE'], 'verify-full')
                self.assertEqual(run.call_args.kwargs['env']['PGSSLROOTCERT'], db.sslrootcert)
        with patch.object(diagnose_database, 'load_database', return_value=db), \
             patch.object(diagnose_database.socket, 'create_connection'), \
             patch.object(diagnose_database.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='')) as run:
            diagnose_database.main()
            env = run.call_args.kwargs['env']
            self.assertEqual(env['PGSSLMODE'], 'verify-full')
            self.assertIn('default_transaction_read_only=on', env['PGOPTIONS'])
