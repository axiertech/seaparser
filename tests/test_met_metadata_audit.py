from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/met-nordic-metadata'


class METMetadataAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'metadata'
        shutil.copytree(FIXTURE, self.directory)

    def change_source(self, filename, old, new, *, refresh_hash=False):
        path = self.directory / filename
        content = path.read_text()
        self.assertIn(old, content)
        path.write_text(content.replace(old, new, 1))
        if refresh_hash:
            manifest_path = self.directory / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            for entry in manifest['files']:
                if entry['filename'] == filename:
                    data = path.read_bytes()
                    entry.update(bytes=len(data), sha256=sha256(data).hexdigest())
            manifest_path.write_text(json.dumps(manifest))

    def test_independent_provider_coordinates_reproduce_reviewed_geometry(self):
        report = audit(self.directory)
        self.assertEqual(report['source_node_count'], 56)
        self.assertEqual(len(report['source_hashes']), 5)
        self.assertAlmostEqual(report['source_projection_vs_provider_latlon_max_spherical_distance_m'],
                               0.24907657108681355, delta=0.000001)
        self.assertAlmostEqual(report['separable_axis_max_error_lower_bound_m'],
                               184.738574436333, delta=0.000001)
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIsNone(report['issued_at'])

    def test_changed_bytes_are_rejected(self):
        self.change_source('native-axes.txt', '-896442.2', '-896441.2')
        with self.assertRaisesRegex(ValueError, 'hash or byte count'):
            audit(self.directory)

    def test_updated_hash_cannot_hide_wrong_axis_spacing(self):
        self.change_source('native-axes.txt', '-896442.2', '-896441.2', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, '1000 metre'):
            audit(self.directory)

    def test_updated_hash_cannot_change_reviewed_projection(self):
        self.change_source('met-forecast.das', '+R=6.371e+06', '+R=6.378e+06', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, 'native spherical LCC'):
            audit(self.directory)

    def test_manifest_flags_and_manual_dates_cannot_qualify_routing(self):
        path = self.directory / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest.update(issued_at='2026-10-13T00:26:17Z', routing_status='verified', blockers=[])
        path.write_text(json.dumps(manifest))
        report = audit(self.directory)
        self.assertIsNone(report['issued_at'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIn('cross_product_model_run_compatibility_unverified', report['blockers'])
