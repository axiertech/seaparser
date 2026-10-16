"""Ambiguous JSON identities must fail, even when the last value looks correct."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit, audit_wind_sample

ROOT = Path(__file__).resolve().parents[1] / 'fixtures'


class METManifestIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for name in ('met-nordic-metadata', 'met-nordic-wind-sample'):
            shutil.copytree(ROOT / name, self.directory / name)

    def test_metadata_duplicate_root_and_file_hash_are_rejected(self):
        path = self.directory / 'met-nordic-metadata/manifest.json'
        original = path.read_text()
        for old, new in (('"schema": 1', '"schema": 0, "schema": 1'),
                         ('"sha256": "', '"sha256": "wrong-first-value", "sha256": "')):
            with self.subTest(field=old):
                path.write_text(original.replace(old, new, 1))
                with self.assertRaisesRegex(ValueError, 'Duplicate manifest key'):
                    audit(path.parent)

    def test_wind_duplicate_identity_and_nested_subset_are_rejected(self):
        path = self.directory / 'met-nordic-wind-sample/manifest.json'
        original = path.read_text()
        for old, new in (('"sha256": "', '"sha256": "wrong-first-value", "sha256": "'),
                         ('"x_first": 692', '"x_first": 0, "x_first": 692')):
            with self.subTest(field=old):
                path.write_text(original.replace(old, new, 1))
                with self.assertRaisesRegex(ValueError, 'Duplicate manifest key'):
                    audit_wind_sample(path.parent, self.directory / 'met-nordic-metadata')
