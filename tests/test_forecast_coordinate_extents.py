"""Coordinate number overlap never certifies datums or continuous support."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit_coordinate_extents

ROOT = Path(__file__).resolve().parents[1] / 'fixtures'


class ForecastCoordinateExtentsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.marine = Path(temporary.name) / 'marine'
        shutil.copytree(ROOT / 'vinga-copernicus', self.marine)

    def audit(self):
        return audit_coordinate_extents(ROOT / 'met-nordic-metadata', ROOT / 'met-nordic-wind-sample', self.marine)

    def test_known_extents_and_distinct_marine_grids_remain_unqualified(self):
        report = self.audit()
        self.assertEqual(report['met_extents'], {'min_latitude': 57.60443, 'max_latitude': 57.669865,
                                                'min_longitude': 11.558033, 'max_longitude': 11.664452})
        self.assertFalse(report['marine_grids_identical'])
        for product in report['marine_products'].values():
            self.assertEqual(product['node_count'], 4)
            self.assertTrue(product['coordinate_numbers_inside_met_extents'])
        self.assertEqual(len(report['met_source_hashes']), 5)
        self.assertEqual(len(report['marine_source_hashes']), 3)
        self.assertFalse(report['datum_equivalence_verified'])
        self.assertFalse(report['whole_cell_coverage_verified'])
        self.assertIsNone(report['issued_at'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertIn('cross_product_model_run_compatibility_unverified', report['blockers'])

    def test_changed_marine_bytes_fail_before_coordinate_comparison(self):
        path = self.marine / 'waves.nc'
        data = path.read_bytes()
        path.write_bytes(bytes([data[0] ^ 1]) + data[1:])
        with self.assertRaisesRegex(ValueError, 'file hash mismatch'):
            self.audit()

    def test_marine_read_budget_is_enforced_before_decoder(self):
        (self.marine / 'current.nc').write_bytes(b'x' * 512_001)
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            self.audit()

    def test_malformed_marine_manifest_fails_closed(self):
        (self.marine / 'manifest.json').write_text(json.dumps({'files': [None] * 3}))
        with self.assertRaisesRegex(ValueError, 'marine source manifest'):
            self.audit()
