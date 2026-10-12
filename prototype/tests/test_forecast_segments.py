"""Segment coverage references with thin cells missed by ordinary sample points."""
import unittest
from dataclasses import replace
from datetime import timedelta

from prototype.calculation import sail_to_target, simulate
from prototype.forecast import FixedClock, ForecastPolicy
from prototype.forecast_data import DataUnavailable
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.routes import RouteCandidate, compare_routes
from prototype.departures import compare_departures
from prototype.weather import WeatherPolicy
from test_forecast_data import ADAPTER, fixture, START, PLAN, END


def thin_mask(name='current', missing_node=False):
    raw = fixture()
    product = next(p for p in raw['products'] if p['product'] == name)
    node = {'wind': [4, 0], 'current': [0, 90], 'waves': [1, 5, 0]}[name]
    product['east_m'] = [-50, 20, 21, 22, 150]
    product['values'] = [[[node[:] for x in range(5)] for y in range(2)] for t in range(2)]
    if missing_node:
        product['values'][0][0][2] = None
    else:
        product['invalid_cells'] = [[0, 0, 1]]
    return ADAPTER.normalize(raw)


class ForecastSegmentTests(unittest.TestCase):
    def test_thin_invalid_cells_or_missing_support_cannot_be_jumped(self):
        for name in ('current', 'wind', 'waves'):
            for missing in (False, True):
                snapshot = thin_mask(name, missing)
                # Start, midpoint and destination are all valid.
                for x, seconds in ((0, 0), (50, 50), (100, 100)):
                    self.assertIsNotNone(getattr(snapshot.evaluate(Vector(x, 0), START+timedelta(seconds=seconds)), name))
                result = sail_to_target(snapshot, START, Vector(100, 0), speed_knots=1/KNOT,
                                        step_seconds=100, weather_policy=WeatherPolicy(5, 1),
                                        forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN))
                self.assertEqual(result.status, 'data_unavailable')
                self.assertIn(name+': segmentets datastöd', result.reason)
                self.assertFalse(result.steps)
                self.assertEqual(result.end_position, Vector(0, 0))
                self.assertIsNone(result.travel_seconds)

    def test_time_mask_between_start_and_midpoint_rejected(self):
        raw = fixture()
        product = raw['products'][1]
        product['times'] = [START, START+timedelta(seconds=20), START+timedelta(seconds=21), END]
        product['values'] = [[[[0, 90] for x in range(2)] for y in range(2)] for t in range(4)]
        product['invalid_cells'] = [[1, 0, 0]]
        snapshot = ADAPTER.normalize(raw)
        with self.assertRaisesRegex(DataUnavailable, 'current.*ogiltig cell'):
            snapshot.validate_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100))

    def test_diagonal_cell_intersection_and_boundary_contact(self):
        snapshot = thin_mask()
        grid = snapshot.products[1]
        with self.assertRaises(DataUnavailable):
            grid.validate_segment(Vector(0, -30), START, Vector(100, 30), START+timedelta(seconds=100))
        with self.assertRaises(DataUnavailable):
            grid.validate_segment(Vector(20, -30), START, Vector(20, 30), START+timedelta(seconds=100))
        grid.validate_segment(Vector(0, -30), START, Vector(10, 30), START+timedelta(seconds=100))

    def test_closed_spatial_edges_and_exclusive_arrival_time(self):
        snapshot = ADAPTER.normalize(fixture())
        snapshot.validate_segment(Vector(-50, -50), START, Vector(150, 50), END)
        with self.assertRaises(DataUnavailable):
            snapshot.validate_segment(Vector(0, 0), START, Vector(151, 0), END)
        with self.assertRaises(DataUnavailable):
            snapshot.validate_segment(Vector(0, 0), START, Vector(100, 0), END+timedelta(microseconds=1))
        with self.assertRaises(DataUnavailable):
            snapshot.validate_segment(Vector(0, 0), END, Vector(0, 0), END)
        with self.assertRaises(DataUnavailable):
            snapshot.validate_segment(Vector(0, 0), START, Vector(0, 0), START-timedelta(seconds=1))
        # Movement ending at valid_until stays accepted; separate arrival fails.
        result = sail_to_target(snapshot, START, Vector(100, 0), speed_knots=.1/KNOT,
                                step_seconds=1000, weather_policy=WeatherPolicy(5, 1),
                                forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN))
        self.assertTrue(result.destination_reached)
        self.assertEqual(result.elapsed_seconds, 1000)
        self.assertEqual(result.arrival_weather_status, 'data_unavailable')

    def test_simulate_and_all_comparison_options_share_segment_guard(self):
        snapshot = thin_mask()
        with self.assertRaisesRegex(DataUnavailable, 'segmentets datastöd'):
            simulate(ConstantBoat(1/KNOT), snapshot, START, 100, step_seconds=100)
        result = compare_departures(snapshot, [START, START+timedelta(seconds=200)], Vector(100, 0),
                                    [RouteCandidate('direct'), RouteCandidate('via', (Vector(50, 10),))],
                                    clock=FixedClock(PLAN), speed_knots=1/KNOT,
                                    step_seconds=100, weather_policy=WeatherPolicy(5, 1),
                                    forecast_policy=ForecastPolicy(600))
        self.assertEqual(result.status, 'no_feasible_departure')
        for row in result.departures:
            self.assertTrue(all(r.status == 'data_unavailable' for r in row.routes.candidates))
            self.assertIsNone(row.routes.fastest)
            self.assertIsNone(row.routes.comfortable)

    def test_control_budget_rejects_instead_of_skipping_cells(self):
        grid = thin_mask().products[0]
        with self.assertRaises(ValueError):
            grid.validate_segment(Vector(0, 0), START, Vector(100, 0), END, max_intervals=0)
        grid = thin_mask().products[1]
        # Remove mask so exhaustion is the only reason.
        grid = replace(grid, invalid_cells=())
        with self.assertRaisesRegex(DataUnavailable, 'cellkontrollgräns'):
            grid.validate_segment(Vector(0, 0), START, Vector(100, 0), START+timedelta(seconds=100), max_intervals=2)

    def test_valid_segment_results_agree_with_halved_step(self):
        snapshot = ADAPTER.normalize(fixture())
        for step in (100, 50):
            result = compare_routes(snapshot, START, Vector(100, 0), [RouteCandidate('direct')],
                                    speed_knots=1/KNOT, step_seconds=step,
                                    weather_policy=WeatherPolicy(5, 1),
                                    forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN))
            self.assertEqual(result.fastest.travel_seconds, 100)
            self.assertEqual(result.fastest.comfort_exposure, 200)
            self.assertIn('Hela accepterade', result.fastest.legs[0].forecast_support_scope)

    def test_complete_safe_detour_can_win_when_direct_segment_lacks_support(self):
        raw = fixture()
        product = raw['products'][1]
        product['east_m'] = [-50, 20, 21, 150]
        product['north_m'] = [-50, -1, 1, 50]
        product['values'] = [[[[0, 90] for x in range(4)] for y in range(4)] for t in range(2)]
        product['invalid_cells'] = [[0, 1, 1]]
        result = compare_routes(ADAPTER.normalize(raw), START, Vector(100, 0),
                                [RouteCandidate('direct'), RouteCandidate('detour', (Vector(10, 10), Vector(30, 10)))],
                                speed_knots=1/KNOT, step_seconds=100,
                                weather_policy=WeatherPolicy(5, 1),
                                forecast_policy=ForecastPolicy(600), clock=FixedClock(PLAN))
        self.assertEqual(result.candidates[0].status, 'data_unavailable')
        self.assertEqual(result.fastest.candidate.name, 'detour')
        self.assertEqual(result.comfortable.candidate.name, 'detour')
