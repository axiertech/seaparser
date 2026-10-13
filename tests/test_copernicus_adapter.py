import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from prototype.forecast import FixedClock, ForecastPolicy
from prototype.forecast_data import DataUnavailable
from prototype.model import Vector
from prototype.routes import RouteCandidate, compare_routes


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / 'fixtures' / 'vinga-copernicus'
FIXTURE = json.loads((FIXTURE_DIR / 'reference.json').read_text())
MANIFEST = json.loads((FIXTURE_DIR / 'manifest.json').read_text())


class CopernicusAdapterTests(unittest.TestCase):
    def setUp(self):
        self.payload = copy.deepcopy(FIXTURE)
        self.snapshot = CopernicusMarineAdapter().normalize(self.payload)

    def test_raw_netcdf_hashes_and_retrieval_times_are_frozen(self):
        by_name = {entry['product']: entry for entry in MANIFEST['files']}
        for metadata in self.snapshot.product_metadata:
            entry = by_name[metadata.product]
            raw = (FIXTURE_DIR / entry['filename']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
            self.assertEqual(metadata.source_sha256, entry['sha256'])
            self.assertIsNotNone(metadata.retrieved_at)
            self.assertIsNone(metadata.issued_at)
            self.assertIn('copernicus.eu', metadata.source_url)
            self.assertIn('license', metadata.license_url)

    def test_actual_cf_fields_normalize_to_known_vectors(self):
        current, waves = self.snapshot.products
        self.assertEqual(current.metadata.product, 'current')
        self.assertEqual(current.metadata.units, ('m/s', 'm/s'))
        self.assertEqual(current.metadata.reference_frame, 'ground-to-true-east-north')
        self.assertEqual(current.metadata.valid_from.isoformat(), '2026-10-13T12:00:00+00:00')
        self.assertEqual(current.metadata.valid_until.isoformat(), '2026-10-13T16:00:00+00:00')
        self.assertEqual(waves.metadata.units, ('m', 's', '1', '1'))
        self.assertEqual(waves.metadata.reference_frame, 'ground-from-true-east-north-tm02')
        self.assertAlmostEqual(current.values[0][0][0][0], -0.2828807234764099, places=8)
        self.assertAlmostEqual(current.values[0][0][0][1], 0.3781495988368988, places=8)
        self.assertAlmostEqual(waves.values[0][0][0][0], 1.2349779605865479, places=7)
        self.assertAlmostEqual(waves.values[0][0][0][1], 2.9598515033721924, places=7)
        self.assertEqual(len(current.times), 5)
        self.assertNotEqual(current.east_m, waves.east_m)
        self.assertNotEqual(current.north_m, waves.north_m)
        midpoint = current.interpolate(Vector(current.east_m[0], current.north_m[0]),
                                       current.times[0] + (current.times[1]-current.times[0])/2)
        self.assertAlmostEqual(midpoint[0], (-0.2828807234764099-0.2522740066051483)/2, places=8)
        self.assertAlmostEqual(midpoint[1], (0.3781495988368988+0.3283383846282959)/2, places=8)

    def test_spatial_and_time_extrapolation_are_rejected(self):
        waves = self.snapshot.products[1]
        start = waves.times[0]
        corner = Vector(waves.east_m[0], waves.north_m[0])
        self.assertAlmostEqual(waves.interpolate(corner, start)[0], 1.2349779605865479)
        for position, time in (
            (Vector(waves.east_m[0] - .01, waves.north_m[0]), start),
            (corner, start.replace(year=2026, month=10, day=13, hour=11, minute=59)),
            (corner, waves.times[-1]),
        ):
            with self.assertRaises(DataUnavailable):
                waves.interpolate(position, time)

    def test_land_mask_gaps_are_preserved_and_mask_grids_must_match(self):
        payload = copy.deepcopy(FIXTURE)
        payload['products']['static']['data']['mask'][0][0] = 0
        snapshot = CopernicusMarineAdapter().normalize(payload)
        waves = snapshot.products[1]
        self.assertIsNone(waves.values[0][0][0])
        interior = Vector((waves.east_m[0] + waves.east_m[1]) / 2,
                          (waves.north_m[0] + waves.north_m[1]) / 2)
        with self.assertRaisesRegex(DataUnavailable, 'Datalucka'):
            waves.interpolate(interior, waves.times[0])
        payload['products']['static']['longitude'][0] += .00001
        with self.assertRaisesRegex(ValueError, 'grid differs'):
            CopernicusMarineAdapter().normalize(payload)

    def test_unknown_issue_time_and_missing_wind_keep_snapshot_unroutable(self):
        self.assertEqual({p.metadata.product for p in self.snapshot.products}, {'current', 'waves'})
        time = self.snapshot.products[0].times[0]
        position = Vector(sum(self.snapshot.products[0].east_m) / 2,
                          sum(self.snapshot.products[0].north_m) / 2)
        conditions = self.snapshot.evaluate(position, time)
        self.assertIsNone(conditions.wind)
        self.assertIsNotNone(conditions.current)
        self.assertIsNotNone(conditions.waves)
        with self.assertRaisesRegex(ValueError, 'utfärdandetid saknas'):
            ForecastPolicy(3600).check(conditions, datetime(2026, 10, 13, 11, tzinfo=timezone.utc))
        comparison = compare_routes(
            self.snapshot, time, position + Vector(10, 0), [RouteCandidate('direct')],
            position=position, forecast_policy=ForecastPolicy(3600), clock=FixedClock(time),
            step_seconds=1, max_seconds=30)
        self.assertEqual(comparison.status, 'no_feasible_route')
        self.assertIsNone(comparison.fastest)
        self.assertEqual(comparison.candidates[0].status, 'data_unavailable')
        with self.assertRaisesRegex(DataUnavailable, 'wind: produkt saknas'):
            self.snapshot.validate_segment(position, time, position, time + (self.snapshot.products[0].times[1]-time))

    def test_input_mutation_cannot_change_normalized_snapshot(self):
        before = self.snapshot.products[0].values[0][0][0]
        self.payload['products']['current']['data']['uo'][0][0][0] = 99
        self.payload['products']['static']['data']['mask'][0][0] = 0
        self.assertEqual(self.snapshot.products[0].values[0][0][0], before)


if __name__ == '__main__':
    unittest.main()
