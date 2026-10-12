"""Independent interpolation, metadata isolation and frozen adapter fixtures."""
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from math import cos, radians

from infrastructure.forecast_adapter import SyntheticFixtureAdapter
from prototype.departures import compare_departures
from prototype.forecast import FixedClock, ForecastPolicy
from prototype.forecast_data import DataUnavailable, ForecastDataset, GridProduct
from prototype.forecast_metadata import Coverage
from prototype.model import KNOT, Vector
from prototype.presentation import export_departure_comparison
from prototype.routes import RouteCandidate, compare_routes
from prototype.weather import WeatherPolicy

PLAN = datetime(2026, 1, 1, tzinfo=timezone.utc)
START = PLAN + timedelta(hours=2)
END = START + timedelta(seconds=1000)
ADAPTER = SyntheticFixtureAdapter()


def fixture(version='1'):
    products = []
    for name, node in [('wind', [4, 0]), ('current', [0, 90]), ('waves', [1, 5, 0])]:
        products.append(dict(product=name, dataset_id=name+'-cycle', version=version,
            source='estimated-synthetic-'+name, issued_at=PLAN-timedelta(seconds=100),
            valid_from=START, valid_until=END,
            coverage=dict(min_east_m=-50, min_north_m=-50, max_east_m=150, max_north_m=50,
                          origin_latitude=58, origin_longitude=11),
            east_m=[-50, 150], north_m=[-50, 50], times=[START, END],
            units=['m', 's', 'deg'] if name == 'waves' else ['m/s', 'deg'],
            reference_frame='ground-from-true-north-tm02' if name == 'waves' else (
                'ground-from-true-north' if name == 'wind' else 'ground-to-true-north'),
            values=[[[list(node) for x in range(2)] for y in range(2)] for t in range(2)],
            invalid_cells=[]))
    return dict(dataset_id='synthetic-bundle', version=version, products=products)


def plan(snapshot, **options):
    return compare_routes(snapshot, START, options.pop('target', Vector(100, 0)),
                          [RouteCandidate('direct')], speed_knots=1/KNOT,
                          weather_policy=WeatherPolicy(5, 1), forecast_policy=ForecastPolicy(600),
                          clock=FixedClock(PLAN), **options)


class ForecastDataTests(unittest.TestCase):
    def test_adapter_units_and_distinct_from_to_conventions(self):
        raw = fixture()
        for product in raw['products'][:2]:
            product['units'] = ['kn', 'deg']
            product['values'] = [[[[2, 90] for x in range(2)] for y in range(2)] for t in range(2)]
        weather = ADAPTER.normalize(raw).evaluate(Vector(0, 0), START)
        self.assertAlmostEqual(weather.wind.east, -2*KNOT)
        self.assertAlmostEqual(weather.current.east, 2*KNOT)
        self.assertAlmostEqual(weather.wind.north, 0, delta=1e-12)
        self.assertEqual(weather.wind_metadata.units, ('m/s', 'm/s'))
        self.assertNotEqual(weather.wind_metadata.source, weather.current_metadata.source)
        self.assertEqual(weather.dataset_id, 'synthetic-bundle')

    def test_independent_trilinear_component_reference(self):
        product = ADAPTER.normalize(fixture()).products[1]
        # Affine field u = 1+.002*x+.003*y+.004*t; v = -2+.001*x-.002*y+.001*t.
        values = [[[[1+.002*x+.003*y+.004*t, -2+.001*x-.002*y+.001*t]
                    for x in (-50, 150)] for y in (-50, 50)] for t in (0, 1000)]
        grid = replace(product, values=values)
        u, v = grid.interpolate(Vector(25, 10), START+timedelta(seconds=250))
        self.assertAlmostEqual(u, 2.08, places=12)
        self.assertAlmostEqual(v, -1.745, places=12)
        # Components are interpolated, not speed/bearing.
        grid = replace(product, values=[[[[1, 0], [0, 1]], [[1, 0], [0, 1]]] for t in range(2)])
        self.assertEqual(grid.interpolate(Vector(50, 0), START), (.5, .5))

    def test_direction_wrap_359_1_for_wind_and_waves(self):
        raw = fixture()
        for name in ('wind', 'waves'):
            product = next(p for p in raw['products'] if p['product'] == name)
            left = [4, 359] if name == 'wind' else [1, 5, 359]
            right = [4, 1] if name == 'wind' else [1, 5, 1]
            product['values'] = [[[left[:], right[:]], [left[:], right[:]]] for t in range(2)]
        weather = ADAPTER.normalize(raw).evaluate(Vector(50, 0), START)
        self.assertAlmostEqual(weather.wind.east, 0, delta=1e-12)
        self.assertAlmostEqual(weather.wind.north, -4*cos(radians(1)), places=12)
        self.assertLess(min(weather.waves.from_degrees, 360-weather.waves.from_degrees), 1e-10)

    def test_ambiguous_wave_direction_is_explicit_gap(self):
        raw = fixture()
        raw['products'][2]['values'] = [[[[1, 5, 0], [1, 5, 180]],
                                       [[1, 5, 0], [1, 5, 180]]] for t in range(2)]
        weather = ADAPTER.normalize(raw).evaluate(Vector(50, 0), START)
        self.assertIsNone(weather.waves)
        self.assertIn('odefinierad', weather.reason)
        self.assertIsNotNone(weather.current)

    def test_each_product_gap_preserves_other_products_and_metadata(self):
        for index, name in enumerate(('wind', 'current', 'waves')):
            raw = fixture()
            raw['products'][index]['values'][1][1][1] = None
            snapshot = ADAPTER.normalize(raw)
            weather = snapshot.evaluate(Vector(0, 0), START)
            self.assertIsNone(getattr(weather, name))
            for other in ('wind', 'current', 'waves'):
                if other != name:
                    self.assertIsNotNone(getattr(weather, other))
            self.assertIn(name+': Datalucka', weather.reason)
            self.assertIsNotNone(getattr(weather, name+'_metadata'))
            result = plan(snapshot)
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
            self.assertIsNone(result.fastest)

    def test_invalid_cell_and_shared_boundary_cannot_be_bypassed(self):
        product = ADAPTER.normalize(fixture()).products[1]
        grid = replace(product, east_m=(-50, 50, 150),
                       values=[[[[0, 0], [0, 0], [0, 0]] for y in range(2)] for t in range(2)],
                       invalid_cells=[[0, 0, 1]])
        self.assertEqual(grid.interpolate(Vector(0, 0), START), (0, 0))
        for x in (50, 100, 150):
            with self.assertRaisesRegex(DataUnavailable, 'ogiltig cell'):
                grid.interpolate(Vector(x, 0), START)
        with self.assertRaises(ValueError):
            replace(grid, invalid_cells=((0, 0, 2),))

    def test_spatial_edges_closed_time_end_exclusive_no_extrapolation(self):
        grid = ADAPTER.normalize(fixture()).products[1]
        for x in (-50, 150):
            for y in (-50, 50):
                self.assertEqual(grid.interpolate(Vector(x, y), START), (0, 0))
        for position, time in [(Vector(-50.001, 0), START), (Vector(150.001, 0), START),
                               (Vector(0, -50.001), START), (Vector(0, 50.001), START),
                               (Vector(0, 0), START-timedelta(microseconds=1)),
                               (Vector(0, 0), END), (Vector(0, 0), END+timedelta(seconds=1))]:
            with self.assertRaises(DataUnavailable):
                grid.interpolate(position, time)
        result = plan(ADAPTER.normalize(fixture()), target=Vector(200, 0), step_seconds=10)
        self.assertEqual(result.candidates[0].status, 'data_unavailable')

    def test_unknown_coverage_units_frames_and_issue_time_rejected(self):
        for field, value in [('coverage', None), ('units', ['mph', 'deg']),
                             ('reference_frame', 'magnetic'), ('issued_at', None)]:
            raw = fixture()
            raw['products'][0][field] = value
            with self.assertRaises(ValueError):
                ADAPTER.normalize(raw)
        product = ADAPTER.normalize(fixture()).products[0]
        with self.assertRaises(ValueError):
            replace(product.metadata, coverage=None)
        with self.assertRaises(ValueError):
            replace(product, east_m=(-50, 200))
        with self.assertRaises(ValueError):
            replace(product, times=(END, START))
        with self.assertRaises(ValueError):
            replace(product, values=([[[float('nan'), 0]]],))

    def test_original_nested_inputs_cannot_change_snapshot(self):
        raw = fixture()
        snapshot = ADAPTER.normalize(raw)
        before = snapshot.evaluate(Vector(0, 0), START)
        raw['version'] = 'modified'
        raw['products'][1]['values'][0][0][0][0] = 100
        raw['products'][1]['east_m'][0] = 0
        raw['products'][1]['coverage']['origin_latitude'] = 0
        raw['products'][1]['invalid_cells'].append([0, 0, 0])
        raw['products'].clear()
        self.assertEqual(snapshot.evaluate(Vector(0, 0), START), before)
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 'modified'
        with self.assertRaises(FrozenInstanceError):
            snapshot.products[0].metadata.source = 'modified'
        with self.assertRaises(TypeError):
            snapshot.products[0].values[0][0][0][0] = 3
        # Direct normalized constructor also copies all nested lists.
        values = [[[[0, 0] for x in range(2)] for y in range(2)] for t in range(2)]
        product = replace(snapshot.products[1], values=values)
        values[0][0][0][0] = 200
        self.assertEqual(product.interpolate(Vector(0, 0), START), (0, 0))

    def test_independent_issue_age_and_validity_are_enforced(self):
        for index in range(3):
            raw = fixture()
            raw['products'][index]['issued_at'] = PLAN-timedelta(seconds=601)
            result = plan(ADAPTER.normalize(raw))
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
            self.assertIn('för gammal', result.candidates[0].reason)
        raw = fixture()
        raw['products'][0]['valid_until'] = START+timedelta(seconds=50)
        result = plan(ADAPTER.normalize(raw), step_seconds=60)
        self.assertEqual(result.candidates[0].status, 'data_unavailable')
        self.assertLessEqual(result.candidates[0].elapsed_seconds, 50)
        raw = fixture()
        raw['products'][2]['valid_until'] = START+timedelta(seconds=100)
        result = plan(ADAPTER.normalize(raw))
        self.assertTrue(result.candidates[0].destination_reached)
        self.assertEqual(result.candidates[0].status, 'data_unavailable')
        self.assertIsNone(result.fastest)

    def test_forecast_switch_is_explicit_old_snapshot_stays_old(self):
        old = ADAPTER.normalize(fixture())
        raw = fixture('2')
        raw['products'][1]['values'] = [[[[.5, 90] for x in range(2)] for y in range(2)] for t in range(2)]
        new = ADAPTER.normalize(raw)
        self.assertEqual(plan(old).fastest.travel_seconds, 100)
        self.assertAlmostEqual(plan(new).fastest.travel_seconds, 100/1.5, places=5)
        self.assertEqual(plan(old).dataset_version, '1')
        self.assertEqual(plan(new).dataset_version, '2')
        with self.assertRaises(ValueError):
            ForecastDataset('mixed', '1', old.products+new.products)
        with self.assertRaises(ValueError):
            replace(old, products=(replace(old.products[0], metadata=replace(
                old.products[0].metadata, coverage=replace(old.products[0].metadata.coverage,
                                                         origin_latitude=59))), old.products[1]))

    def test_all_departures_routes_and_export_use_one_frozen_dataset(self):
        raw = fixture()
        snapshot = ADAPTER.normalize(raw)
        # Simulate replacing/mutating provider input after normalization.
        raw['products'][0]['issued_at'] = PLAN+timedelta(days=1)
        result = compare_departures(snapshot, [START, START+timedelta(seconds=200)], Vector(100, 0),
                                   [RouteCandidate('direct'), RouteCandidate('north', (Vector(50, 20),))],
                                   clock=FixedClock(PLAN), speed_knots=1/KNOT,
                                   weather_policy=WeatherPolicy(5, 1), forecast_policy=ForecastPolicy(600))
        for row in result.departures:
            self.assertEqual(row.routes.dataset_id, snapshot.dataset_id)
            self.assertEqual(row.routes.dataset_version, snapshot.version)
            self.assertIsNotNone(row.routes.fastest)
            for route in row.routes.candidates:
                for leg in route.legs:
                    for step in leg.steps:
                        for sample in (step.start, step.midpoint):
                            self.assertEqual(sample.dataset_id, snapshot.dataset_id)
                            self.assertEqual(sample.wind_metadata.source, 'estimated-synthetic-wind')
                            self.assertEqual(sample.current_metadata.source, 'estimated-synthetic-current')
        payload = json.loads(export_departure_comparison(result))
        self.assertEqual(payload['departures'][1]['routes']['dataset_version'], '1')
        observation = payload['departures'][0]['routes']['candidates'][0]['legs'][0]['arrival_observation']
        self.assertEqual(observation['waves_metadata']['dataset_id'], 'waves-cycle')

    def test_absent_product_is_a_gap_not_an_assumed_valid_zero(self):
        raw = fixture()
        raw['products'] = raw['products'][:2]
        snapshot = ADAPTER.normalize(raw)
        weather = snapshot.evaluate(Vector(0, 0), START)
        self.assertIsNone(weather.waves)
        self.assertIn('waves: produkt saknas', weather.reason)
        result = plan(snapshot)
        self.assertEqual(result.candidates[0].status, 'data_unavailable')
        self.assertIsNone(result.fastest)

    def test_independent_geographic_coverage_and_failed_result_manifest(self):
        raw = fixture()
        raw['products'][0]['east_m'][0] = 10
        raw['products'][0]['coverage']['min_east_m'] = 10
        snapshot = ADAPTER.normalize(raw)
        weather = snapshot.evaluate(Vector(0, 0), START)
        self.assertIsNone(weather.wind)
        self.assertIsNotNone(weather.current)
        self.assertIsNotNone(weather.waves)
        self.assertIn('wind: Utanför geografisk', weather.reason)
        result = plan(snapshot)
        self.assertFalse(result.candidates[0].legs[0].steps)
        self.assertEqual(len(result.forecast_products), 3)
        from prototype.presentation import export_route_comparison
        manifest = json.loads(export_route_comparison(result))['forecast_products']
        self.assertEqual(manifest[0]['coverage']['min_east_m'], 10)
        self.assertEqual(manifest[0]['issued_at'], (PLAN-timedelta(seconds=100)).isoformat())

    def test_comparison_never_fetches_or_renormalizes(self):
        from unittest.mock import patch
        snapshot = ADAPTER.normalize(fixture())
        with patch('socket.socket', side_effect=AssertionError('network during planning')), \
             patch('urllib.request.urlopen', side_effect=AssertionError('HTTP during planning')), \
             patch.object(SyntheticFixtureAdapter, 'normalize', side_effect=AssertionError('adapter during planning')):
            result = compare_departures(snapshot, [START, START+timedelta(seconds=200)], Vector(100, 0),
                                        [RouteCandidate('direct')], clock=FixedClock(PLAN),
                                        speed_knots=1/KNOT, weather_policy=WeatherPolicy(5, 1),
                                        forecast_policy=ForecastPolicy(600))
        self.assertTrue(all(row.routes.fastest is not None for row in result.departures))

    def test_constant_interpolation_cannot_cross_exact_hard_limit(self):
        snapshot = ADAPTER.normalize(fixture())
        for seconds in (0, 1, 17, 250, 999):
            for x in (-50, 0, 13.7, 100, 150):
                weather = snapshot.evaluate(Vector(x, 0), START+timedelta(seconds=seconds))
                self.assertEqual(weather.waves.height_m, 1)
                WeatherPolicy(4, 1).check(weather, START+timedelta(seconds=seconds))
