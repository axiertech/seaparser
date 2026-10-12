"""Conservative continuous certificates, actual witnesses and explicit uncertainty."""
import json
import math
import unittest
from dataclasses import replace
from datetime import timedelta

from prototype.calculation import sail_to_target, simulate
from prototype.departures import compare_departures
from prototype.forecast import FixedClock, ForecastPolicy
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.presentation import export_departure_comparison
from prototype.routes import RouteCandidate
from prototype.segment_weather import SegmentWeatherUnverified, SegmentWeatherExceeded
from prototype.weather import WeatherPolicy
from test_forecast_data import ADAPTER, fixture, START, PLAN

POLICY = WeatherPolicy(5, 1)


def voyage(snapshot, **options):
    return sail_to_target(snapshot, START, Vector(100, 0), speed_knots=1/KNOT, step_seconds=100,
                          weather_policy=options.pop('weather_policy', POLICY),
                          forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN), **options)


def peak(name, temporal=False):
    raw = fixture()
    product = next(p for p in raw['products'] if p['product']==name)
    if temporal:
        product['times'] = [START, START+timedelta(seconds=20), START+timedelta(seconds=21),
                            START+timedelta(seconds=22), START+timedelta(seconds=1000)]
        product['values'] = [[[[6 if k==2 else 4, 0] if name=='wind' else [2 if k==2 else 1, 5, 0]
                              for x in range(2)] for y in range(2)] for k in range(5)]
    else:
        product['east_m'] = [-50, 20, 21, 22, 150]
        product['values'] = [[[[6 if x==2 else 4, 0] if name=='wind' else [2 if x==2 else 1, 5, 0]
                              for x in range(5)] for y in range(2)] for t in range(2)]
    return ADAPTER.normalize(raw)


class SegmentWeatherTests(unittest.TestCase):
    def test_short_spatial_and_temporal_peaks_missed_by_ordinary_samples(self):
        for name in ('wind', 'waves'):
            for temporal in (False, True):
                snapshot = peak(name, temporal)
                for s in (0, 50, 100):
                    POLICY.check(snapshot.evaluate(Vector(s, 0), START+timedelta(seconds=s)), START+timedelta(seconds=s))
                result = voyage(snapshot)
                self.assertEqual(result.status, 'weather_limit')
                self.assertEqual(result.weather_segment_status, 'exceeded')
                self.assertEqual(result.weather_segment_failure.witness.product, name)
                self.assertFalse(result.steps)
                self.assertEqual(result.end_position, Vector(0, 0))
                self.assertEqual(result.comfort_exposure, 0)

    def test_exact_component_norm_and_wave_limit_equality(self):
        snapshot = ADAPTER.normalize(fixture())
        wind = replace(snapshot.products[0], values=[[[[3, 4] for x in range(2)] for y in range(2)] for t in range(2)])
        snapshot = replace(snapshot, products=(wind, *snapshot.products[1:]))
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'verified')
        self.assertTrue(all(b.status=='verified' for b in check.bounds))
        self.assertEqual(next(b.wind_squared_upper for b in check.bounds if b.product=='wind'), '25')
        below = WeatherPolicy(math.nextafter(5, 0), 1)
        self.assertEqual(snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), below).status, 'exceeded')
        self.assertEqual(snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), WeatherPolicy(5, math.nextafter(1, 0))).status, 'exceeded')

    def test_high_off_path_corner_is_uncertainty_not_observed_exceedance(self):
        raw = fixture()
        product = raw['products'][2]
        product['values'] = [[[[.4, 5, 0], [.4, 5, 0]], [[1.1, 5, 0], [1.1, 5, 0]]] for t in range(2)]
        snapshot = ADAPTER.normalize(raw)
        # Along y=0 Hs is constantly .75 <1, but whole-cell maximum is1.1.
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'unverified')
        self.assertIsNone(check.witness)
        self.assertEqual(check.failure_kind, 'bounds_inconclusive')
        result = voyage(snapshot)
        self.assertEqual(result.status, 'weather_unverified')
        self.assertIsNone(result.travel_seconds)
        self.assertFalse(result.steps)

    def test_wind_component_combination_has_interior_maximum(self):
        snapshot = ADAPTER.normalize(fixture())
        product = snapshot.products[0]
        metadata = replace(product.metadata, coverage=replace(product.metadata.coverage, min_east_m=0, max_east_m=100),
                           valid_until=START+timedelta(seconds=100))
        # Along x/100=t/100=s: u=8s(1-s), v=2(1-s).
        # |W|²=(1-s)²(64s²+4), maximum at s=(2+sqrt(2))/8.
        values = [[[[0, 2], [0, 2]] for y in range(2)], [[[8, 0], [0, 0]] for y in range(2)]]
        wind = replace(product, metadata=metadata, east_m=(0, 100),
                       times=(START, START+timedelta(seconds=100)), values=values)
        snapshot = replace(snapshot, products=(wind, *snapshot.products[1:]))
        limit = WeatherPolicy(2.25, 1)
        for s in (0, .5):
            value = wind.interpolate(Vector(100*s, 0), START+timedelta(seconds=100*s))
            self.assertLessEqual(math.hypot(*value), 2.25)
        s = (2+math.sqrt(2))/8
        self.assertGreater(math.hypot(8*s*(1-s), 2*(1-s)), 2.25)
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), limit)
        # A conservative envelope rejects approval even though witnesses miss the peak.
        self.assertEqual(check.status, 'unverified')
        self.assertIsNone(check.witness)
        self.assertEqual(voyage(snapshot, weather_policy=limit).status, 'weather_unverified')

    def test_cells_at_shared_boundary_and_closed_spatial_edge(self):
        snapshot = ADAPTER.normalize(fixture())
        self.assertEqual(snapshot.certify_weather_segment(Vector(-50, -50), START, Vector(150, 50), START+timedelta(seconds=100), POLICY).status, 'verified')
        product = snapshot.products[2]
        # Start exactly on boundary adjoining a high cell: conservatively unverified.
        product = replace(product, east_m=(-50, 0, 150), values=[[[[1.1, 5, 0, 1], [1, 5, 0, 1], [1, 5, 0, 1]] for y in range(2)] for t in range(2)])
        snapshot = replace(snapshot, products=(*snapshot.products[:2], product))
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'unverified')
        self.assertIsNone(check.witness)

    def test_missing_or_invalid_data_never_certified(self):
        raw = fixture(); raw['products'][0]['values'][0][0][0] = None
        check = ADAPTER.normalize(raw).certify_weather_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'unverified')
        self.assertEqual(check.failure_kind, 'data_unavailable')
        result = voyage(ADAPTER.normalize(raw))
        self.assertEqual(result.status, 'data_unavailable')

    def test_unknown_is_excluded_from_both_selections_and_exported(self):
        raw = fixture(); raw['products'][2]['values'] = [[[[.4, 5, 0], [.4, 5, 0]], [[1.1, 5, 0], [1.1, 5, 0]]] for t in range(2)]
        result = compare_departures(ADAPTER.normalize(raw), [START, START+timedelta(seconds=200)], Vector(100, 0),
                                   [RouteCandidate('direct')], clock=FixedClock(PLAN), speed_knots=1/KNOT,
                                   step_seconds=100, weather_policy=POLICY, forecast_policy=ForecastPolicy(600))
        self.assertEqual(result.status, 'no_feasible_departure')
        self.assertTrue(all(row.routes.fastest is None and row.routes.comfortable is None for row in result.departures))
        exported = json.loads(export_departure_comparison(result))
        leg = exported['departures'][0]['routes']['candidates'][0]['legs'][0]
        self.assertEqual(leg['weather_segment_failure']['status'], 'unverified')
        self.assertEqual(leg['weather_segment_failure']['bounds'][-1]['wave_height_upper_m'], 1.1)

    def test_simulate_rejects_exceeded_and_unknown_checks(self):
        with self.assertRaises(SegmentWeatherExceeded):
            simulate(ConstantBoat(1/KNOT), peak('wind'), START, 100, step_seconds=100, weather_policy=POLICY)
        raw = fixture(); raw['products'][2]['values'] = [[[[.4, 5, 0], [.4, 5, 0]], [[1.1, 5, 0], [1.1, 5, 0]]] for t in range(2)]
        with self.assertRaises(SegmentWeatherUnverified):
            simulate(ConstantBoat(1/KNOT), ADAPTER.normalize(raw), START, 100, step_seconds=100, weather_policy=POLICY)

    def test_masked_off_path_box_cell_remains_unverified(self):
        snapshot = ADAPTER.normalize(fixture())
        product = snapshot.products[0]
        product = replace(product, east_m=(-50, 20, 21, 150), north_m=(-50, 0, 20, 50),
                          values=[[[[0, -4] for x in range(4)] for y in range(4)] for t in range(2)],
                          invalid_cells=((0, 2, 1),))
        snapshot = replace(snapshot, products=(product, *snapshot.products[1:]))
        # Actual diagonal passes below mask at x20..21, but the enclosing box touches it.
        snapshot.validate_segment(Vector(0, 0), START, Vector(100, 20), START+timedelta(seconds=100))
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(100, 20), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'unverified')
        self.assertIsNone(check.witness)
        self.assertTrue(any('maskerat' in b.reason for b in check.bounds))

    def test_certificate_budget_cannot_silently_drop_box_cells(self):
        snapshot = ADAPTER.normalize(fixture())
        product = snapshot.products[0]
        metadata = replace(product.metadata, coverage=replace(product.metadata.coverage, min_east_m=0, max_east_m=65,
                                                               min_north_m=0, max_north_m=50))
        product = replace(product, metadata=metadata, east_m=tuple(range(66)), north_m=tuple(i*50/65 for i in range(66)),
                          values=[[[[0, -4] for x in range(66)] for y in range(66)] for t in range(2)])
        snapshot = replace(snapshot, products=(product, *snapshot.products[1:]))
        check = snapshot.certify_weather_segment(Vector(0, 0), START, Vector(65, 50), START+timedelta(seconds=100), POLICY)
        self.assertEqual(check.status, 'unverified')
        self.assertEqual(check.failure_kind, 'bounds_inconclusive')
        self.assertIn('cellgräns', check.reason)

    def test_accepted_steps_export_proof_and_zero_route_has_no_segment(self):
        snapshot = ADAPTER.normalize(fixture())
        result = voyage(snapshot)
        self.assertEqual(result.status, 'arrived')
        self.assertEqual(result.weather_segment_status, 'verified')
        self.assertEqual(result.weather_status, 'passed_segments_and_arrival')
        self.assertTrue(all(s.weather_segment_check.status=='verified' for s in result.steps))
        empty = sail_to_target(snapshot, START, Vector(0, 0), weather_policy=POLICY,
                               forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN))
        self.assertEqual(empty.status, 'arrived')
        self.assertEqual(empty.weather_segment_status, 'not_applicable')
        self.assertEqual(empty.arrival_weather_status, 'passed_at_arrival')
