from hashlib import sha256
from decimal import Decimal
from math import radians, sin
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit, matrix


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
        self.assertEqual(Decimal(report['model_reference']['epoch_seconds']), Decimal(1791849600))
        self.assertIsNone(report['model_reference']['calendar_attribute'])

    def test_changed_time_units_are_rejected_even_with_updated_hash(self):
        self.change_source('met-forecast.das', 'seconds since 1970', 'hours since 1970', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, 'UTC time units'):
            audit(self.directory)

    def test_dds_time_dimension_must_match_ascii(self):
        self.change_source('met-forecast.dds', 'time[time = 59]', 'time[time = 58]', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, 'DDS/ASCII time declarations'):
            audit(self.directory)

    def test_wind_dimension_must_match_reviewed_native_axes(self):
        self.change_source('met-forecast.dds', 'wind_speed_10m[time = 59][y = 2321][x = 1796]',
                           'wind_speed_10m[time = 59][y = 2321][x = 1795]', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, 'wind DDS dimensions'):
            audit(self.directory)

    def test_missing_or_duplicate_reference_is_rejected(self):
        for replacement in ('', 'forecast_reference_time, 1.7918496E9\nforecast_reference_time, 1.7918496E9'):
            with self.subTest(replacement=replacement):
                path = self.directory / 'met-time-coordinates.txt'
                path.write_bytes((FIXTURE / path.name).read_bytes())
                self.change_source(path.name, 'forecast_reference_time, 1.7918496E9', replacement,
                                   refresh_hash=True)
                with self.assertRaisesRegex(ValueError, 'ASCII model reference'):
                    audit(self.directory)

    def test_source_reference_cannot_be_replaced_by_manifest_date(self):
        self.change_source('met-time-coordinates.txt', 'forecast_reference_time, 1.7918496E9',
                           'forecast_reference_time, 1.791846E9', refresh_hash=True)
        with self.assertRaisesRegex(ValueError, 'reviewed source value'):
            audit(self.directory)

    def test_changed_bytes_are_rejected(self):
        self.change_source('native-axes.txt', '-896442.2', '-896441.2')
        with self.assertRaisesRegex(ValueError, 'hash or byte count'):
            audit(self.directory)

    def test_native_convergence_matches_independent_tangent_cone_reference(self):
        # Tangent spherical LCC at 63 degrees: gamma = sin(63)*(longitude-15).
        # 1e-6 degree compares numerical factors only, never a routing tolerance.
        longitude = matrix((self.directory / 'vinga-latlon.txt').read_text(), 'longitude', 8, 7)
        expected = [sin(radians(63)) * (float(lon) - 15) for row in longitude for lon in row]
        report = audit(self.directory)
        convergence = report['native_meridian_convergence']
        self.assertEqual(convergence['node_count'], 56)
        self.assertAlmostEqual(convergence['min_degrees'], min(expected), delta=1e-6)
        self.assertAlmostEqual(convergence['max_degrees'], max(expected), delta=1e-6)
        self.assertGreater(max(expected) - min(expected), .09)
        self.assertLess(max(expected), -2.9)
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIsNone(report['issued_at'])

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
