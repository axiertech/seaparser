"""Conflicting marine manifest identities cannot be resolved by last-key wins."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

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

    def test_invalid_manifest_shapes_fail_before_netcdf_decode(self):
        path = self.directory / 'manifest.json'
        original = json.loads(path.read_text())
        for value in ([], original | {'schema': True}, original | {'files': None},
                      original | {'files': [None, None, None]}):
            with self.subTest(value=type(value).__name__):
                path.write_text(json.dumps(value))
                with patch('scripts.audit_copernicus.inspect_file', side_effect=AssertionError('decode')):
                    with self.assertRaisesRegex(ValueError, 'manifest'):
                        audit_snapshot(self.directory)

    def test_conflicting_file_product_identity_fails_before_decode(self):
        path = self.directory / 'manifest.json'
        original = path.read_text()
        for field, value in (('product', 'current'), ('dataset_id', 'wrong-dataset'),
                             ('version', 'wrong-version'), ('part', 'bathy'),
                             ('service', 'static-arco')):
            with self.subTest(field=field):
                manifest = json.loads(original)
                manifest['files'][0][field] = value
                path.write_text(json.dumps(manifest))
                with patch('scripts.audit_copernicus.inspect_file', side_effect=AssertionError('decode')):
                    with self.assertRaisesRegex(ValueError, 'manifest'):
                        audit_snapshot(self.directory)

    def test_oversized_manifest_fails_before_decode(self):
        path = self.directory / 'manifest.json'
        data = path.read_bytes()
        path.write_bytes(data + b' ' * (512001 - len(data)))
        with patch('scripts.audit_copernicus.inspect_file', side_effect=AssertionError('decode')):
            with self.assertRaisesRegex(ValueError, 'manifest byte budget'):
                audit_snapshot(self.directory)
