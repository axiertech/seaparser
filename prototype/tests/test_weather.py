"""Hard exclusion and independent synthetic-exposure references, no database."""
import json
import math
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from prototype.environment import Conditions, WaveData, SyntheticEnvironment, wind_from
from prototype.model import KNOT, Vector
from prototype.sailing import PolarBoat
from prototype.routes import compare_routes, RouteCandidate
from prototype.calculation import sail_to_target, simulate
from prototype.model import ConstantBoat
from prototype.weather import WeatherPolicy, WeatherLimitExceeded, synthetic_comfort_rate
from prototype.presentation import export_route_comparison

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(seconds=1000)
DIRECT = RouteCandidate('direct')
DETOUR = RouteCandidate('detour', (Vector(0, 20), Vector(100, 20)))
POLICY = WeatherPolicy(max_wind_m_s=5, max_wave_height_m=1)


def data(height=1, period=5, direction=0, wind=4):
    return Conditions(Vector(0, 0), wind=wind_from(wind, 0), valid_from=START, valid_until=END,
                      waves=WaveData(height, period, direction, START, END))


def compare(field, candidates=(DIRECT, DETOUR), **kwargs):
    env = SyntheticEnvironment(field if callable(field) else lambda p, t: field)
    return compare_routes(env, START, kwargs.pop('target', Vector(100, 0)), candidates,
                          speed_knots=1 / KNOT, weather_policy=kwargs.pop('weather_policy', POLICY), **kwargs)


class WeatherTests(unittest.TestCase):
    def test_comfort_rate_height_period_relative_direction_and_wrap(self):
        waves = WaveData(2, 5, 0, START, END)
        self.assertEqual(synthetic_comfort_rate(waves, 0), 4)
        self.assertEqual(synthetic_comfort_rate(waves, 90), 8)
        self.assertEqual(synthetic_comfort_rate(replace(waves, period_seconds=10), 90), 2)
        self.assertEqual(synthetic_comfort_rate(replace(waves, height_m=0), 90), 0)
        near_north = WaveData(1, 5, 359, START, END)
        self.assertAlmostEqual(synthetic_comfort_rate(near_north, 1),
                               1 + math.sin(math.radians(2))**2, delta=1e-12)

    def test_fastest_and_comfortable_differ_and_halved_step_agrees(self):
        field = lambda p, t: data(height=1 / (1 + max(0, p.north) / 10))
        exact = 2 * 10 * (1 - 1 / 3) + 100 * 2 / 9  # vertical legs plus eastward leg
        exposures = []
        for step in (2, 1):
            result = compare(field, step_seconds=step, max_comfort_extra_seconds=40)
            self.assertEqual(result.fastest.candidate, DIRECT)
            self.assertEqual(result.comfortable.candidate, DETOUR)
            self.assertEqual(result.fastest.travel_seconds, 100)
            self.assertEqual(result.comfortable.travel_seconds, 140)
            self.assertAlmostEqual(result.fastest.comfort_exposure, 200, delta=1e-8)
            self.assertAlmostEqual(result.comfortable.comfort_exposure, exact, delta=.07)
            self.assertTrue(all(r.weather_status == 'passed_at_samples' for r in result.candidates))
            exposures.append(result.comfortable.comfort_exposure)
        self.assertLess(abs(exposures[0] - exposures[1]), .05)

    def test_extra_time_cap_and_zero_extra_time(self):
        field = lambda p, t: data(height=1 / (1 + max(0, p.north) / 10))
        for cap in (0, 39):
            result = compare(field, max_comfort_extra_seconds=cap)
            self.assertEqual(result.comfortable.candidate, DIRECT)
        for cap in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                compare(field, max_comfort_extra_seconds=cap)

    def test_hard_wave_or_wind_limit_excludes_short_low_exposure_route(self):
        for violation in ('wave', 'wind'):
            def field(p, t):
                unsafe = 40 <= p.east <= 60 and p.north < 1
                # A huge period makes exposure tiny even at the forbidden height.
                return data(height=1.01 if unsafe and violation == 'wave' else .2,
                            period=100000, wind=5.01 if unsafe and violation == 'wind' else 4)
            result = compare(field, step_seconds=10, max_comfort_extra_seconds=10000)
            self.assertEqual(result.candidates[0].status, 'weather_limit')
            self.assertIsNone(result.candidates[0].travel_seconds)
            self.assertIsNone(result.candidates[0].comfort_exposure)
            self.assertEqual(result.fastest.candidate, DETOUR)
            self.assertEqual(result.comfortable.candidate, DETOUR)

    def test_all_unsafe_returns_no_feasible_route_for_both_objectives(self):
        for condition in (data(height=1.000001), data(wind=5.000001)):
            result = compare(condition)
            self.assertEqual(result.status, 'no_feasible_route')
            self.assertIsNone(result.fastest)
            self.assertIsNone(result.comfortable)
            self.assertTrue(all(r.status == 'weather_limit' for r in result.candidates))
        # Equality is allowed; limits are not comfort weights.
        self.assertEqual(compare(data(height=1, wind=5), candidates=[DIRECT]).status, 'selected')

    def test_weather_wind_is_ground_relative_and_polar_wind_is_water_relative(self):
        condition = replace(data(), current=Vector(0, -5), wind=Vector(0, -1), wind_reference='water')
        with self.assertRaises(WeatherLimitExceeded):
            POLICY.check(condition, START)  # W_ground=-1-5=-6 exceeds 5 m/s
        allowed = replace(data(), current=Vector(0, 5))  # W_ground=-4, W_water=-9
        POLICY.check(allowed, START)
        self.assertAlmostEqual(PolarBoat().wind(allowed)[0] * KNOT, 9)
        with self.assertRaises(ValueError):
            WeatherPolicy(5, 1, wind_reference='water')

    def test_missing_invalid_and_unknown_data_are_explicit(self):
        conditions = [replace(data(), current=None), replace(data(), wind=None), replace(data(), waves=None),
                      replace(data(), valid_from=None), replace(data(), valid_until=None)]
        for change in ({'height_m': None}, {'height_m': -1}, {'period_seconds': None},
                       {'period_seconds': 0}, {'from_degrees': None}, {'from_degrees': float('nan')},
                       {'valid_from': None}, {'valid_until': None}):
            conditions.append(replace(data(), waves=replace(data().waves, **change)))
        for condition in conditions:
            with self.subTest(condition=condition):
                result = compare(condition, candidates=[DIRECT])
                self.assertEqual(result.candidates[0].status, 'data_unavailable')
                self.assertIsNone(result.fastest)
                self.assertIsNone(result.comfortable)

    def test_data_gap_at_midpoint_position_and_time_is_not_accepted(self):
        for by_position in (False, True):
            def field(p, t):
                missing = p.east == 10 if by_position else t == START + timedelta(seconds=10)
                return replace(data(), waves=None) if missing else data()
            result = compare(field, candidates=[DIRECT], step_seconds=20)
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
            self.assertEqual(result.candidates[0].elapsed_seconds, 0)
            self.assertEqual(result.candidates[0].end_position, Vector(0, 0))

    def test_wave_expiration_shortens_step_and_stops_at_boundary(self):
        boundary = START + timedelta(seconds=45)
        condition = replace(data(), waves=replace(data().waves, valid_until=boundary))
        result = compare(condition, candidates=[DIRECT], step_seconds=60)
        route = result.candidates[0]
        self.assertEqual(route.status, 'data_unavailable')
        self.assertEqual(route.elapsed_seconds, 45)
        self.assertEqual(route.end_position, Vector(45, 0))
        self.assertEqual(route.legs[0].steps[-1].end_time, boundary)
        # Movement may end at the boundary, but destination weather now needs
        # a NEW valid observation at that instant; the expired record cannot verify it.
        at_boundary = compare(condition, candidates=[DIRECT], target=Vector(45, 0))
        self.assertEqual(at_boundary.status, 'no_feasible_route')
        self.assertTrue(at_boundary.candidates[0].destination_reached)
        self.assertEqual(at_boundary.candidates[0].arrival_weather_status, 'data_unavailable')

    def test_time_varying_exposure_against_integral_reference(self):
        field = lambda p, t: data(height=.5 + .002 * (t - START).total_seconds())
        # Integral_0^100 2*(.5+.002t)^2 dt = 72+2/3 exposure seconds.
        errors = []
        for step in (10, 5):
            result = compare(field, candidates=[DIRECT], step_seconds=step)
            errors.append(abs(result.fastest.comfort_exposure - (72 + 2 / 3)))
        self.assertLess(errors[0], .01)
        self.assertLess(errors[1], errors[0] / 3)

    def test_zero_distance_still_requires_weather_data(self):
        result = compare(replace(data(), wind=None), candidates=[DIRECT], target=Vector(0, 0))
        self.assertEqual(result.candidates[0].status, 'data_unavailable')
        self.assertIsNone(result.fastest)

    def test_legacy_mode_is_explicitly_unchecked(self):
        result = compare(Conditions(Vector(0, 0)), candidates=[DIRECT], weather_policy=None)
        self.assertEqual(result.fastest.weather_status, 'not_requested')
        self.assertIsNone(result.fastest.comfort_exposure)
        self.assertIsNone(result.comfortable)

    def test_policy_and_metric_metadata_exported(self):
        result = compare(data(), candidates=[DIRECT])
        row = json.loads(export_route_comparison(result))
        self.assertEqual(row['weather_policy']['wind_reference'], 'ground')
        self.assertEqual(row['comfortable_candidate'], 'direct')
        self.assertIn('ej validerat', row['comfort_model'])
        self.assertEqual(row['candidates'][0]['legs'][0]['comfort_model'], row['comfort_model'])
        self.assertEqual(row['candidates'][0]['legs'][0]['weather_policy'], row['weather_policy'])
        self.assertEqual(row['candidates'][0]['legs'][0]['steps'][0]['start']['waves']['height_m'], 1)
        self.assertIn('source', row['candidates'][0]['legs'][0]['steps'][0]['start']['waves'])

    def test_invalid_policy_and_wave_interval(self):
        for args in ((-1, 1), (5, -1), (float('nan'), 1), (5, float('inf'))):
            with self.assertRaises(ValueError):
                WeatherPolicy(*args)
        for changes in ({"period_kind": "peak"}, {"direction_reference": "boat"}):
            with self.assertRaises(ValueError):
                replace(data().waves, **changes)
        with self.assertRaises(ValueError):
            WaveData(1, 5, 0, START, START)
        with self.assertRaises(ValueError):
            WaveData(1, 5, 0, START.replace(tzinfo=None), END)

    def test_fixed_heading_simulation_uses_same_hard_limits(self):
        boat = ConstantBoat(speed_knots=1 / KNOT, leeway=0)
        for condition in (data(height=2), data(wind=6)):
            with self.assertRaises(WeatherLimitExceeded):
                simulate(boat, SyntheticEnvironment(lambda p, t: condition), START, 10, weather_policy=POLICY)

    def test_changed_wave_interval_is_requeried_at_boundary(self):
        boundary = START + timedelta(seconds=45)
        def field(p, t):
            waves = WaveData(1 if t < boundary else .5, 5, 0,
                             START if t < boundary else boundary,
                             boundary if t < boundary else END)
            return replace(data(), waves=waves)
        result = compare(field, candidates=[DIRECT], step_seconds=60)
        self.assertEqual(result.fastest.travel_seconds, 100)
        # Beam waves: 2*1²*45 + 2*.5²*55 = 117.5 exposure seconds.
        self.assertAlmostEqual(result.fastest.comfort_exposure, 117.5, delta=1e-8)
        self.assertEqual(result.fastest.legs[0].steps[0].end_time, boundary)

    def test_hard_violation_at_midpoint_discards_step(self):
        for violation in ('wind', 'wave'):
            def field(p, t):
                middle = t == START + timedelta(seconds=10)
                return data(wind=6 if middle and violation == 'wind' else 4,
                            height=2 if middle and violation == 'wave' else 1)
            result = compare(field, candidates=[DIRECT], step_seconds=20)
            self.assertEqual(result.candidates[0].status, 'weather_limit')
            self.assertEqual(result.candidates[0].elapsed_seconds, 0)
            self.assertIsNone(result.fastest)
            self.assertIsNone(result.comfortable)

    def test_weather_policy_disallows_explicit_current_fallback(self):
        env = SyntheticEnvironment(lambda p, t: replace(data(), current=None))
        with self.assertRaisesRegex(ValueError, 'ingen fallback'):
            simulate(ConstantBoat(leeway=0), env, START, 10, allow_missing_current=True,
                     weather_policy=POLICY)
