"""Malformed/oversized frozen sources fail closed without outputting inputs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.audit_met_metadata import audit, audit_wind_sample, bounded_read, numbers

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / 'fixtures/met-nordic-metadata'


class METAuditFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_actual_read_budget_rejects_one_extra_byte(self):
        path = self.directory / 'source'
        path.write_bytes(b'x' * 128_000)
        self.assertEqual(len(bounded_read(self.directory, 'source', limit=128_000)), 128_000)
        path.write_bytes(b'x' * 128_001)
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            bounded_read(self.directory, 'source', limit=128_000)

    def test_read_limit_cannot_be_disabled(self):
        for limit in (0, -1, True, 512_001, None):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, 'bounded read limit'):
                bounded_read(self.directory, 'source', limit=limit)

    def test_malformed_nonfinite_and_oversized_numbers_are_rejected(self):
        for token in ('not-a-number', '', 'NaN', 'sNaN', 'Infinity', '-Infinity', '1e999999999',
                      '1e-999999999', '1' * 65):
            with self.subTest(token=token), self.assertRaises(ValueError):
                numbers(token, 1)

    def test_invalid_manifest_shapes_are_rejected(self):
        for content in ([], {'schema': 1, 'files': None}, {'schema': True, 'files': []},
                        {'schema': 1, 'files': [{}] * 5}):
            (self.directory / 'manifest.json').write_text(json.dumps(content))
            with self.subTest(content=content), self.assertRaises(ValueError):
                audit(self.directory)

    def test_missing_subset_is_explicit_failure(self):
        target = self.directory / 'metadata'
        shutil.copytree(METADATA, target)
        manifest = json.loads((target / 'manifest.json').read_text())
        del manifest['coordinate_subset']
        (target / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'coordinate subset'):
            audit(target)

    def test_wind_file_budget_cannot_be_overridden_by_manifest(self):
        target = self.directory / 'wind'
        shutil.copytree(ROOT / 'fixtures/met-nordic-wind-sample', target)
        (target / 'native-wind-land.txt').write_bytes(b'x' * 128_001)
        manifest = json.loads((target / 'manifest.json').read_text())
        manifest['budget']['bytes'] = 1_000_000
        (target / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            audit_wind_sample(target, METADATA)

    def test_cli_missing_source_returns_nonzero_unavailable_json(self):
        result = subprocess.run([sys.executable, '-B', '-m', 'scripts.audit_met_metadata',
                                 str(self.directory / 'sentinel-private-path')],
                                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIsNone(report['issued_at'])
        self.assertEqual(report['error_kind'], 'FileNotFoundError')
        self.assertNotIn('sentinel-private-path', result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
