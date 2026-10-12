"""Offline checks of isolation and opt-in behavior; no database subprocess."""
import unittest
from unittest.mock import patch
from scripts import verify_migrations_integration as integration
from scripts.migrate import LOCK


class IntegrationPlanTests(unittest.TestCase):
    def test_plan_does_not_load_config_or_launch_psql(self):
        with patch('sys.argv', ['integration']), \
             patch.object(integration, 'load_database') as config, \
             patch.object(integration.subprocess, 'run') as run, \
             patch.object(integration.subprocess, 'Popen') as popen, patch('builtins.print'):
            integration.main()
        config.assert_not_called()
        run.assert_not_called()
        popen.assert_not_called()

    def test_fixtures_use_only_their_schema_and_lock(self):
        sql = integration.fixture_sql('seaparser_it_abcdef', 92837211, fail=True)
        self.assertNotIn('public.seaparser_migrations', sql)
        self.assertNotIn(str(LOCK), sql)
        self.assertIn('CREATE SCHEMA seaparser_it_abcdef;', sql)
        self.assertIn('fixture_deliberate_failure', sql)
        for command in ('COMMIT', 'DROP ', 'TRUNCATE', 'DELETE ', 'UPDATE '):
            self.assertNotIn(command, sql)

    def test_fixture_rejects_existing_project_schema_or_lock(self):
        for schema, lock in (('public', 123), ('seaparser', 123),
                             ('seaparser_it_foo;DROP', 123), ('seaparser_it_abc', LOCK)):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                integration.fixture_sql(schema, lock)
