import tempfile
from pathlib import Path
import unittest
from infrastructure.settings import load_database, read_env


class SettingsSafetyTests(unittest.TestCase):
    def test_explicit_values_never_read_private_file(self):
        db = load_database("development", private_path=Path("/nonexistent/private"),
                           variables={"DB_PASSWORD": "synthetic"})
        self.assertEqual((db.name, db.user), ("seaparser", "seaparser"))
        self.assertNotIn("synthetic", repr(db))

    def test_invalid_configuration_hides_values(self):
        for values in ({}, {"TEST_DB_PASSWORD": "synthetic"},
                       {"DB_PASSWORD": "synthetic", "DB_NAME": "wrong"},
                       {"DB_PASSWORD": "synthetic", "DB_USER": "wrong"},
                       {"DB_PASSWORD": "synthetic", "APP_ENV": "production"},
                       {"DB_PASSWORD": "synthetic", "DB_PORT": "secret-invalid"}):
            with self.subTest(keys=tuple(values)), self.assertRaises(ValueError) as error:
                load_database("development", private_path=Path("/nonexistent/private"),
                              variables=values)
            self.assertNotIn("synthetic", str(error.exception))
            self.assertNotIn("secret-invalid", str(error.exception))

    def test_environment_must_be_explicit(self):
        for environment in ("production", "test", ""):
            with self.subTest(environment=environment), self.assertRaises(ValueError):
                load_database(environment, variables={"DB_PASSWORD": "synthetic"})

    def test_env_is_data_not_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example"
            path.write_text('DB_PASSWORD="$(not-executed)"\nDB_NAME=seaparser\n')
            self.assertEqual(read_env(path)["DB_PASSWORD"], "$(not-executed)")
            path.write_text("DB_PASSWORD=a\nDB_PASSWORD=b\n")
            with self.assertRaises(ValueError):
                read_env(path)

    def test_private_file_rejects_legacy_test_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example"
            path.write_text("DB_PASSWORD=synthetic\nTEST_DB_PASSWORD=legacy-private\n")
            with self.assertRaises(ValueError) as error:
                load_database("development", private_path=path)
            self.assertNotIn("synthetic", str(error.exception))
            self.assertNotIn("legacy-private", str(error.exception))
