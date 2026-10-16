"""Conflicting marine manifest identities cannot be resolved by last-key wins."""
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_copernicus import audit_snapshot
from scripts.freeze_copernicus_reference import freeze_with_audit

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/vinga-copernicus'


class MarineManifestIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'marine'
        shutil.copytree(FIXTURE, self.directory)

    def test_audit_rejects_duplicate_schema_and_nested_hash(self):
        path = self.directory / 'manifest.json'
        original = path.read_text()
        for old, new in (('"schema": 1', '"schema": 0, "schema": 1'),
                         ('"sha256": "', '"sha256": "wrong-first-value", "sha256": "')):
            with self.subTest(field=old):
                path.write_text(original.replace(old, new, 1))
                with self.assertRaisesRegex(ValueError, '^Duplicate manifest key$'):
                    audit_snapshot(self.directory)

    def test_freeze_rejects_duplicate_product_identity(self):
        path = self.directory / 'manifest.json'
        original = path.read_text()
        for old, new in (('"product": "waves"', '"product": "current", "product": "waves"'),
                         ('"dataset_id": "', '"dataset_id": "wrong-first-value", "dataset_id": "')):
            with self.subTest(field=old):
                path.write_text(original.replace(old, new, 1))
                with self.assertRaisesRegex(ValueError, '^Duplicate manifest key$'):
                    freeze_with_audit(self.directory)
