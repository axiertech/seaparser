import tempfile
from pathlib import Path
import unittest
from infrastructure.settings import load_database, read_env


class SettingsSafetyTests(unittest.TestCase):
    def test_test_never_reads_private_file(self):
        db = load_database("test", private_path=Path("/nonexistent/private"),
                           variables={"TEST_DB_PASSWORD": "synthetic"})
        self.assertEqual((db.name, db.user), ("seaparser_test", "seaparser_test"))
        self.assertNotIn("synthetic", repr(db))

    def test_no_development_fallback_or_wrong_identity(self):
        for values in ({}, {"DB_PASSWORD": "synthetic"},
                       {"TEST_DB_PASSWORD": "synthetic", "TEST_DB_NAME": "seaparser"},
                       {"TEST_DB_PASSWORD": "synthetic", "TEST_DB_USER": "seaparser"},
                       {"TEST_DB_PASSWORD": "synthetic", "APP_ENV": "development"},
                       {"TEST_DB_PASSWORD": "synthetic", "TEST_DB_PORT": "secret-invalid"}):
            with self.subTest(keys=tuple(values)), self.assertRaises(ValueError) as error:
                load_database("test", variables=values)
            self.assertNotIn("synthetic", str(error.exception))
            self.assertNotIn("secret-invalid", str(error.exception))

    def test_environment_must_be_explicit(self):
        with self.assertRaises(ValueError):
            load_database("production")

    def test_env_is_data_not_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example"
            path.write_text('DB_PASSWORD="$(not-executed)"\nDB_NAME=seaparser\n')
            self.assertEqual(read_env(path)["DB_PASSWORD"], "$(not-executed)")
            path.write_text("DB_PASSWORD=a\nDB_PASSWORD=b\n")
            with self.assertRaises(ValueError):
                read_env(path)
