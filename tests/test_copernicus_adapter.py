import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest

from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from prototype.forecast import FixedClock, ForecastPolicy
from prototype.forecast_data import DataUnavailable, ForecastDataset, GridProduct
from prototype.calculation import evaluate_conditions
from prototype.model import ConstantBoat, Vector
from prototype.routes import RouteCandidate, compare_routes
from prototype.departures import compare_departures
from prototype.presentation import export_departure_comparison
from prototype.weather import WeatherPolicy


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

    def test_missing_current_component_invalidates_stencil_without_wave_mask_substitution(self):
        for component in ('uo', 'vo'):
            with self.subTest(component=component):
                payload = copy.deepcopy(FIXTURE)
                payload['products']['current']['data'][component][1][0][0] = None
                current, waves = CopernicusMarineAdapter().normalize(payload).products
                self.assertIsNone(current.values[1][0][0])
                self.assertEqual(waves.values, self.snapshot.products[1].values)
                position = Vector(sum(current.east_m)/2, sum(current.north_m)/2)
                with self.assertRaisesRegex(DataUnavailable, 'Datalucka'):
                    current.interpolate(position, current.times[0]+timedelta(minutes=30))
                self.assertIn('model_issue_time_unverified', current.metadata.planning_blockers)

    def test_each_missing_wave_component_preserves_unknown_stencil(self):
        for component in ('VHM0', 'VTM02', 'VMDR'):
            with self.subTest(component=component):
                payload = copy.deepcopy(FIXTURE)
                payload['products']['waves']['data'][component][1][0][0] = None
                current, waves = CopernicusMarineAdapter().normalize(payload).products
                self.assertIsNone(waves.values[1][0][0])
                self.assertEqual(current.values, self.snapshot.products[0].values)
                position = Vector(sum(waves.east_m)/2, sum(waves.north_m)/2)
                with self.assertRaisesRegex(DataUnavailable, 'Datalucka'):
                    waves.interpolate(position, waves.times[0]+timedelta(minutes=30))

    def test_wave_static_mask_never_masks_or_certifies_current(self):
        for mask in (0, None):
            with self.subTest(mask=mask):
                payload = copy.deepcopy(FIXTURE)
                payload['products']['static']['data']['mask'][0][0] = mask
                current, waves = CopernicusMarineAdapter().normalize(payload).products
                self.assertEqual(current.values, self.snapshot.products[0].values)
                self.assertTrue(all(plane[0][0] is None for plane in waves.values))
                position = Vector(sum(current.east_m)/2, sum(current.north_m)/2)
                self.assertEqual(current.interpolate(position, current.times[0]),
                                 self.snapshot.products[0].interpolate(position, current.times[0]))
                self.assertIsNone(current.metadata.issued_at)
                self.assertIn('cross_product_model_run_compatibility_unverified',
                              current.metadata.planning_blockers)

    def test_dates_and_payload_flags_do_not_certify_run_compatibility(self):
        for name in ('current', 'waves'):
            self.payload['products'][name]['issued_at'] = '2026-10-13T11:00:00Z'
        self.payload['run_compatibility_verified'] = True
        self.payload['planning_blockers'] = []
        snapshot = CopernicusMarineAdapter().normalize(self.payload)
        current, waves = snapshot.products
        for product in (current, waves):
            self.assertIsNone(product.metadata.issued_at)
            self.assertIn('model_issue_time_unverified', product.metadata.planning_blockers)
        # Add test wind to isolate the compatibility gate from the missing-wind gate.
        wm = replace(current.metadata, product='wind', dataset_id='test-wind', planning_blockers=())
        values = tuple(tuple(tuple((0., 5.) for _ in current.east_m)
                             for _ in current.north_m) for _ in current.times)
        wind = GridProduct(wm, current.east_m, current.north_m, current.times, values)
        snapshot = ForecastDataset('test-combined', '1', (wind, current, waves))
        time = current.times[0]
        position = Vector(sum(current.east_m)/2, sum(current.north_m)/2)
        weather = snapshot.evaluate(position, time)
        self.assertIsNotNone(weather.wind)
        for policy in (None, ForecastPolicy(7200)):
            result = compare_routes(snapshot, time, position + Vector(10, 0), [RouteCandidate('direct')],
                                    position=position, forecast_policy=policy,
                                    clock=FixedClock(time), step_seconds=1, max_seconds=30)
            self.assertIsNone(result.fastest)
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
            self.assertIn('cross_product_model_run_compatibility_unverified', result.candidates[0].reason)
        with self.assertRaisesRegex(ValueError, 'utfärdandetid saknas'):
            ForecastPolicy(7200).check(weather, time)
        with self.assertRaisesRegex(ValueError, 'compatibility_unverified'):
            evaluate_conditions(ConstantBoat(1), weather, position, time)
        with self.assertRaisesRegex(DataUnavailable, 'compatibility_unverified'):
            current.validate_segment(position, time, position, current.times[1])

    def test_detached_dates_and_run_claims_never_establish_issuance(self):
        for claimed_date in ('2026-10-13T11:00:00Z', '2026-10-13T00:00:00Z',
                             '2024-11-25T00:00:00Z', 'not-a-date', None):
            with self.subTest(claimed_date=claimed_date):
                payload = copy.deepcopy(FIXTURE)
                for name in ('current', 'waves'):
                    raw = payload['products'][name]
                    raw.update(issued_at=claimed_date, model_issue_time=claimed_date,
                               forecast_reference_time=claimed_date, creation_date=claimed_date,
                               last_modified=claimed_date, run_id='claimed-run',
                               run_compatibility_verified=True, planning_blockers=[])
                payload.update(run_compatibility_verified=True, planning_blockers=[])
                snapshot = CopernicusMarineAdapter().normalize(payload)
                for product in snapshot.products:
                    self.assertIsNone(product.metadata.issued_at)
                    self.assertIn('model_issue_time_unverified', product.metadata.planning_blockers)
                    self.assertIn('cross_product_model_run_compatibility_unverified',
                                  product.metadata.planning_blockers)
                    self.assertEqual(product.metadata.version,
                                     FIXTURE['products'][product.metadata.product]['version'])

    def test_departure_objectives_and_export_preserve_marine_provenance_rejection(self):
        for name in ('current', 'waves'):
            self.payload['products'][name].update(issued_at='2026-10-13T11:00:00Z',
                                                   run_compatibility_verified=True, planning_blockers=[])
        current, waves = CopernicusMarineAdapter().normalize(self.payload).products
        time = current.times[0]
        # Synthetic wind isolates marine provenance; it has no marine source identity.
        wm = replace(current.metadata, product='wind', dataset_id='synthetic-negative-test-wind',
                     source='synthetic-negative-test', issued_at=time-timedelta(hours=1),
                     source_sha256=None, source_url=None, license_url=None, retrieved_at=None,
                     planning_blockers=())
        values = tuple(tuple(tuple((0., 5.) for _ in current.east_m)
                             for _ in current.north_m) for _ in current.times)
        wind = GridProduct(wm, current.east_m, current.north_m, current.times, values)
        snapshot = ForecastDataset('negative-test-combined', '1', (wind, current, waves))
        position = Vector(sum(current.east_m)/2, sum(current.north_m)/2)
        routes = (RouteCandidate('direct'), RouteCandidate('via', (position + Vector(5, 1),)))
        for policy in (None, ForecastPolicy(7200)):
            for criterion in (None, 'shortest_travel_time', 'earliest_arrival'):
                with self.subTest(policy=policy, criterion=criterion):
                    result = compare_departures(snapshot, (time, time+timedelta(hours=1)),
                                                position+Vector(10, 0), routes, position=position,
                                                clock=FixedClock(time), forecast_policy=policy,
                                                weather_policy=WeatherPolicy(20, 10),
                                                selection_criterion=criterion, step_seconds=1,
                                                max_seconds=30, max_departures=2, max_candidates=2)
                    exported = json.loads(export_departure_comparison(result))
                    self.assertEqual(exported['status'], 'no_feasible_departure')
                    for key in ('selected', 'shortest_travel', 'earliest_arrival'):
                        self.assertIsNone(exported[key])
                    self.assertEqual(len(exported['departures']), 2)
                    for row in exported['departures']:
                        report = row['routes']
                        self.assertIsNone(report['fastest_candidate'])
                        self.assertIsNone(report['comfortable_candidate'])
                        self.assertEqual(len(report['candidates']), 2)
                        for candidate in report['candidates']:
                            self.assertEqual(candidate['status'], 'data_unavailable')
                            self.assertIn('cross_product_model_run_compatibility_unverified', candidate['reason'])
                            self.assertIn('model_issue_time_unverified', candidate['reason'])
                            self.assertTrue(all(not leg['steps'] for leg in candidate['legs']))
                        marine = [m for m in report['forecast_products'] if m['product'] != 'wind']
                        self.assertEqual(len(marine), 2)
                        for metadata in marine:
                            self.assertIsNone(metadata['issued_at'])
                            self.assertIn('model_issue_time_unverified', metadata['planning_blockers'])
                            self.assertEqual(metadata['source_sha256'],
                                             FIXTURE['products'][metadata['product']]['source_sha256'])

    def test_wave_current_validity_must_match(self):
        self.payload['products']['waves']['times'][-1] = '2026-10-13T17:00:00Z'
        with self.assertRaisesRegex(ValueError, 'validity differs'):
            CopernicusMarineAdapter().normalize(self.payload)

    def test_required_validity_times_cannot_be_unknown(self):
        metadata = self.snapshot.products[0].metadata
        for field in ('valid_from', 'valid_until'):
            with self.assertRaises(ValueError):
                replace(metadata, **{field: None})
        for blockers in ('unknown', ('',), (False,)):
            with self.assertRaises(ValueError):
                replace(metadata, planning_blockers=blockers)


if __name__ == '__main__':
    unittest.main()
