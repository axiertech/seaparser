"""Hand-calculated polar, frame and course-compensation references."""
import json
import math
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from prototype.model import ConstantBoat, CourseUnavailable, KNOT, Vector, velocity
from prototype.environment import Conditions, SyntheticEnvironment, wind_from, water_relative_wind
from prototype.polar import SYNTHETIC_POLAR, SailPolar
from prototype.sailing import PolarBoat
from prototype.calculation import sail_to_target, simulate
from prototype.routes import compare_routes, RouteCandidate
from prototype.obstacles import Rectangle
from prototype.presentation import export_voyage

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def weather(current=Vector(0, 0), strength=10, from_degrees=0, **kwargs):
    return Conditions(current, wind=wind_from(strength * KNOT, from_degrees),
                      wind_reference='water', **kwargs)


def voyage(conditions, target=Vector(100, 0), **kwargs):
    field = conditions if callable(conditions) else lambda p, t: conditions
    return sail_to_target(SyntheticEnvironment(field), START, target,
                          boat=kwargs.pop('boat', PolarBoat()), **kwargs)


class PolarTests(unittest.TestCase):
    def test_values_and_bilinear_interpolation(self):
        polar = SYNTHETIC_POLAR
        # Hand-selected grid cells, not copied from interpolation code.
        for wind, angle, knots in ((0, 90, 0), (10, 45, 3), (10, 90, 5),
                                   (20, 180, 4.5), (10, 75, 4.5),
                                   (15, 60, 5), (15, 75, 5.5), (5, 90, 2.5)):
            self.assertAlmostEqual(polar.speed_m_s(wind, angle) / KNOT, knots, delta=1e-12)
        self.assertTrue(polar.estimated)
        self.assertEqual(polar.version, '1')
        self.assertIn('uppskattad testdata', polar.source)

    def test_grid_edges_no_extrapolation_and_validation(self):
        for args in ((-1, 90), (20.000001, 90), (10, 44.999), (10, 180.001),
                     (float('nan'), 90), (10, float('inf'))):
            with self.subTest(args=args), self.assertRaises(ValueError):
                SYNTHETIC_POLAR.speed_m_s(*args)
        for changes in ({'wind_knots': (0, 10, 10)}, {'angles_degrees': (0, 180)},
                        {'boat_knots': ((1,),)}, {'version': ''}, {'estimated': False}):
            with self.assertRaises(ValueError):
                replace(SYNTHETIC_POLAR, **changes)
        # Exact wind/angle upper edges remain usable after vector conversion.
        water, _ = PolarBoat(heading=180).evaluate(Vector(0, 0), START, weather(strength=20))
        self.assertAlmostEqual(water.speed / KNOT, 4.5, delta=1e-12)

    def test_from_direction_differs_from_current_to_direction(self):
        north_wind = wind_from(10, 0)
        east_wind = wind_from(10, 90)
        self.assertAlmostEqual(north_wind.north, -10)
        self.assertAlmostEqual(east_wind.east, -10)
        self.assertAlmostEqual(velocity(10, 0).north, 10)  # current TO north
        for args in ((-1, 0), (10, float('nan'))):
            with self.assertRaises(ValueError):
                wind_from(*args)

    def test_ground_to_water_frame_conversion(self):
        # Ground air TO south at 4 m/s; water TO east at 3 m/s.
        condition = Conditions(Vector(3, 0), wind=Vector(0, -4))
        relative = water_relative_wind(condition)
        self.assertEqual(relative, Vector(-3, -4))
        self.assertEqual(relative.speed, 5)
        self.assertAlmostEqual((relative.course + 180) % 360, 36.869897645844)
        self.assertEqual(water_relative_wind(replace(condition, wind_reference='water')), Vector(0, -4))
        with self.assertRaises(ValueError):
            replace(condition, wind_reference='apparent')

    def test_359_1_wrap_and_symmetric_tacks(self):
        for bearing in (359, 1):
            water, _ = PolarBoat(heading=180).evaluate(Vector(0, 0), START,
                                                     weather(from_degrees=bearing))
            self.assertAlmostEqual(water.speed / KNOT, 3 + 1 / 60, delta=1e-10)
            with self.assertRaises(CourseUnavailable):
                PolarBoat(heading=0).evaluate(Vector(0, 0), START, weather(from_degrees=bearing))
        for heading in (60, 300):
            water, _ = PolarBoat(heading=heading).evaluate(Vector(0, 0), START, weather())
            self.assertAlmostEqual(water.speed / KNOT, 4, delta=1e-12)

    def test_no_go_boundary_and_no_automatic_tacking(self):
        for heading in (0, 44.999, 315.001):
            with self.assertRaises(CourseUnavailable):
                PolarBoat(heading=heading).evaluate(Vector(0, 0), START, weather())
        for heading in (45, 315):
            water, _ = PolarBoat(heading=heading).evaluate(Vector(0, 0), START, weather())
            self.assertAlmostEqual(water.speed / KNOT, 3, delta=1e-12)
        result = voyage(weather(), target=Vector(0, 100))
        self.assertEqual(result.status, 'infeasible')
        self.assertIsNone(result.travel_seconds)
        self.assertIn('kryssplanering saknas', result.reason)

    def test_missing_calm_invalid_or_out_of_range_wind(self):
        for condition in (Conditions(Vector(0, 0)), weather(strength=21),
                          replace(weather(), wind=Vector(float('nan'), 0))):
            result = voyage(condition)
            self.assertEqual(result.status, 'data_unavailable')
            self.assertIsNone(result.travel_seconds)
        self.assertEqual(voyage(weather(strength=0)).status, 'infeasible')

    def test_zero_current_reference_and_traceability_in_export(self):
        result = voyage(weather(), target=Vector(1852, 0))
        self.assertEqual(result.status, 'arrived')
        self.assertAlmostEqual(result.travel_seconds, 720, delta=.01)  # 1 NM at 5 kt
        data = json.loads(export_voyage(result))
        self.assertIn(SYNTHETIC_POLAR.identifier, data['assumptions'][0])
        self.assertIn('Ingen uppmätt båtprestanda', data['assumptions'][0])
        self.assertEqual(data['steps'][0]['start']['wind_reference'], 'water')
        self.assertEqual(data['steps'][0]['start']['wind']['north'], -10 * KNOT)

    def test_heading_dependent_compensation_against_vector_reference(self):
        # At heading 120°, TWA=120°, polar STW=4.5 kt.
        # C_N=+2.25 kt cancels 4.5*cos(120°); C_E=.3 kt adds progress.
        current = Vector(.3 * KNOT, 2.25 * KNOT)
        expected_knots = .3 + 4.5 * math.sqrt(3) / 2
        for frame in ('water', 'ground'):
            condition = weather(current)
            if frame == 'ground':
                condition = replace(condition, wind=condition.wind + current, wind_reference='ground')
            for step in (120, 60):
                result = voyage(condition, target=Vector(1852, 0), step_seconds=step)
                self.assertEqual(result.status, 'arrived')
                self.assertAlmostEqual(result.travel_seconds, 3600 / expected_knots, delta=.01)
                sample = result.steps[0].midpoint
                self.assertAlmostEqual(sample.water.course, 120, delta=1e-7)
                self.assertAlmostEqual(sample.water.speed / KNOT, 4.5, delta=1e-9)
                self.assertAlmostEqual(sample.ground.north, 0, delta=1e-9)
                # A falsely reused 5 kt compensation gives a materially different speed.
                self.assertGreater(abs(sample.ground.speed / KNOT - (.3 + math.sqrt(25 - 2.25**2))), .1)

    def test_tangential_root_and_stronger_cross_current(self):
        flat = SailPolar('flat-test', '1', 'estimated test fixture',
                         (0, 10), (45, 180), ((0, 0), (5, 5)))
        current = Vector(2, 5 * KNOT)
        result = voyage(weather(current, from_degrees=90), boat=PolarBoat(flat))
        self.assertEqual(result.status, 'arrived')
        self.assertAlmostEqual(result.travel_seconds, 50, delta=.01)
        self.assertAlmostEqual(result.steps[0].start.water.course, 180, delta=1e-7)
        failed = voyage(weather(Vector(2, 5 * KNOT + 1e-6), from_degrees=90), boat=PolarBoat(flat))
        self.assertEqual(failed.status, 'infeasible')

    def test_swappable_boat_in_route_comparison(self):
        env = SyntheticEnvironment(lambda p, t: weather())
        candidates = [RouteCandidate('direct')]
        for boat, seconds in ((ConstantBoat(speed_knots=5, leeway=0), 720), (PolarBoat(), 720)):
            result = compare_routes(env, START, Vector(1852, 0), candidates, boat=boat)
            self.assertAlmostEqual(result.fastest.travel_seconds, seconds, delta=.01)
        blocked_angle = compare_routes(env, START, Vector(0, 100), candidates, boat=PolarBoat())
        self.assertEqual(blocked_angle.status, 'no_feasible_route')

    def test_obstacles_and_forecast_boundaries_with_polar(self):
        boundary = START + timedelta(seconds=45)
        condition = weather(valid_until=boundary)
        result = voyage(condition, target=Vector(1000, 0))
        self.assertEqual(result.status, 'data_unavailable')
        self.assertEqual(result.elapsed_seconds, 45)
        self.assertAlmostEqual(result.end_position.east, 5 * KNOT * 45, delta=1e-7)
        box = Rectangle('test', 40, -1, 60, 1)
        result = voyage(weather(), obstacles=[box], step_seconds=120)
        self.assertEqual(result.status, 'blocked')
        self.assertIsNone(result.travel_seconds)
        with self.assertRaisesRegex(ValueError, 'Strömdata saknas'):
            simulate(PolarBoat(), SyntheticEnvironment(lambda p, t: condition), START, 60)

    def test_time_and_position_dependent_wind_is_requeried(self):
        calls = []
        def field(p, t):
            calls.append((p, t))
            strength = 10 + p.east / 100 + (t - START).total_seconds() / 100
            return weather(strength=strength)
        result = voyage(field, target=Vector(100, 0), step_seconds=5)
        self.assertEqual(result.status, 'arrived')
        self.assertGreater(result.steps[-1].midpoint.water.speed, result.steps[0].start.water.speed)
        self.assertTrue(any(p.east > 0 and t > START for p, t in calls))

    def test_space_time_wind_against_analytic_motion_reference(self):
        def field(p, t):
            return weather(strength=10 + p.east / 100 + (t - START).total_seconds() / 100)
        # At TWA90: STW=5K+.2K*(x+t)/100, so x'=a*x+a*t+5K.
        # x(t)=(5K+1)*expm1(a*t)/a-t, a=.2K/100.
        a = .2 * KNOT / 100
        expected = (5 * KNOT + 1) * math.expm1(a * 30) / a - 30
        errors = []
        for step in (5, 2.5):
            steps = simulate(PolarBoat(), SyntheticEnvironment(field), START, 30, step_seconds=step)
            errors.append(abs(steps[-1].end_position.east - expected))
        self.assertLess(errors[1], errors[0] / 3)
        self.assertLess(errors[0], .001)

    def test_custom_performance_does_not_require_route_changes(self):
        class OtherBoat:
            assumptions = ('Synthetic independent performance fixture',)
            def evaluate(self, position, time, weather):
                return Vector(2, 0), self.assumptions
            def compensate(self, direction, position, time, weather, min_progress_m_s):
                return direction.scaled(2), self.assumptions
        env = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0)))
        result = compare_routes(env, START, Vector(100, 0), [RouteCandidate('direct')], boat=OtherBoat(), speed_knots=0)
        self.assertEqual(result.fastest.travel_seconds, 50)
        self.assertEqual(result.fastest.legs[0].assumptions, OtherBoat.assumptions)

    def test_no_go_applies_to_steering_not_ground_course(self):
        # Ground progress can point into wind if current carries a boat which
        # sails at an allowed 180° TWA. No forbidden heading or tack is used.
        result = voyage(weather(Vector(0, 5 * KNOT)), target=Vector(0, 1852))
        self.assertEqual(result.status, 'arrived')
        self.assertAlmostEqual(result.travel_seconds, 1800, delta=.01)
        self.assertAlmostEqual(result.steps[0].start.water.course, 180, delta=1e-7)
        self.assertAlmostEqual(result.steps[0].start.ground.course, 0, delta=1e-7)

    def test_compensation_at_allowed_angle_boundary_and_opposing_current(self):
        current = Vector(0, -3 * math.sqrt(2) / 2 * KNOT)
        flat = SailPolar('boundary-test', '1', 'estimated fixture',
                         (0, 10), (45, 180), ((0, 0), (3, 3)))
        result = voyage(weather(current), boat=PolarBoat(flat))
        self.assertEqual(result.status, 'arrived')
        self.assertAlmostEqual(result.steps[0].start.water.course, 45, delta=1e-7)
        self.assertAlmostEqual(result.steps[0].start.water.speed / KNOT, 3, delta=1e-9)
        # The varying synthetic polar has two forward roots for this current;
        # its faster interior solution must beat the valid 45° boundary solution.
        faster = voyage(weather(current))
        self.assertGreater(faster.steps[0].start.water.east, 3 * math.sqrt(2) / 2 * KNOT)
        feasible = voyage(weather(Vector(-4 * KNOT, 0)))
        self.assertEqual(feasible.status, 'arrived')
        self.assertAlmostEqual(feasible.travel_seconds, 100 / KNOT, delta=.01)
        self.assertEqual(voyage(weather(Vector(-6 * KNOT, 0))).status, 'infeasible')

    def test_compensated_ground_direction_wraps_359_1(self):
        for bearing, knots in ((359, 5 - 1 / 30), (1, 5 - 1 / 60)):
            result = voyage(weather(from_degrees=270), target=velocity(100, bearing))
            self.assertEqual(result.status, 'arrived')
            self.assertAlmostEqual(result.travel_seconds, 100 / (knots * KNOT), delta=.01)
            self.assertAlmostEqual(result.steps[0].start.water.course, bearing, delta=1e-7)

    def test_forecast_wind_turn_stops_at_boundary_without_tacking(self):
        boundary = START + timedelta(seconds=45)
        def field(p, t):
            return weather(from_degrees=0 if t < boundary else 90,
                           valid_from=START if t < boundary else boundary,
                           valid_until=boundary if t < boundary else START + timedelta(seconds=120))
        result = voyage(field, target=Vector(1000, 0), step_seconds=60)
        self.assertEqual(result.status, 'infeasible')
        self.assertIsNone(result.travel_seconds)
        self.assertEqual(result.elapsed_seconds, 45)
        self.assertEqual(result.steps[-1].end_time, boundary)
        self.assertAlmostEqual(result.end_position.east, 5 * KNOT * 45, delta=1e-7)
