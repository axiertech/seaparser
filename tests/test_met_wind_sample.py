"""Frozen raw MET wind references remain unavailable for planning."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit_wind_sample

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / 'fixtures/met-nordic-metadata'


class METWindSampleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'sample'
        shutil.copytree(ROOT / 'fixtures/met-nordic-wind-sample', self.directory)

    def change(self, old, new, *, refresh_hash=True):
        path = self.directory / 'native-wind-land.txt'
        self.assertIn(old, path.read_text())
        path.write_text(path.read_text().replace(old, new, 1))
        if refresh_hash:
            manifest = self.directory / 'manifest.json'
            entry = json.loads(manifest.read_text())
            data = path.read_bytes()
            entry.update(bytes=len(data), sha256=sha256(data).hexdigest())
            manifest.write_text(json.dumps(entry))

    def test_known_native_sample_and_land_fraction_are_not_routing_proof(self):
        report = audit_wind_sample(self.directory, METADATA)
        self.assertEqual(report['value_ranges']['wind_speed_10m'],
                         {'count': 280, 'min': '11.273894', 'max': '17.250252'})
        self.assertEqual(report['value_ranges']['wind_direction_10m'],
                         {'count': 280, 'min': '142.0', 'max': '160.0'})
        self.assertEqual(report['land_fraction_nonzero_nodes'], 21)
        self.assertFalse(report['land_fraction_is_validity_mask'])
        self.assertIsNone(report['issued_at'])
        self.assertEqual(report['routing_status'], 'data_unavailable')

    def test_changed_source_bytes_fail_hash_check(self):
        self.change('12.970281', '12.970282', refresh_hash=False)
        with self.assertRaisesRegex(ValueError, 'hash, byte count'):
            audit_wind_sample(self.directory, METADATA)

    def test_changed_maps_fail_even_with_new_hash(self):
        self.change('-595322.0', '-595321.0')
        with self.assertRaisesRegex(ValueError, 'native axes'):
            audit_wind_sample(self.directory, METADATA)

    def test_changed_times_fail_even_with_new_hash(self):
        self.change('1.7918928E9', '1.7918929E9')
        with self.assertRaisesRegex(ValueError, 'frozen validity'):
            audit_wind_sample(self.directory, METADATA)

    def test_changed_reference_is_not_issuance(self):
        self.change('forecast_reference_time, 1.7918496E9', 'forecast_reference_time, 1.7918497E9')
        with self.assertRaisesRegex(ValueError, 'model reference'):
            audit_wind_sample(self.directory, METADATA)

    def test_wrong_row_order_fails(self):
        self.change('[0][0], 159.0', '[0][1], 159.0')
        with self.assertRaisesRegex(ValueError, 'Ordered wind sample'):
            audit_wind_sample(self.directory, METADATA)

    def test_negative_wind_fails(self):
        self.change('12.970281', '-12.970281')
        with self.assertRaisesRegex(ValueError, 'physical bounds'):
            audit_wind_sample(self.directory, METADATA)

    def test_payload_dates_and_flags_cannot_lift_blockers(self):
        path = self.directory / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest.update(issued_at='2026-10-13T00:26:17Z', routing_status='verified', blockers=[])
        path.write_text(json.dumps(manifest))
        report = audit_wind_sample(self.directory, METADATA)
        self.assertIsNone(report['issued_at'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIn('cross_product_model_run_compatibility_unverified', report['blockers'])
