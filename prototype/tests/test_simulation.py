import json
import math
import unittest
from datetime import datetime, timedelta, timezone

from prototype.calculation import simulate
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.presentation import export

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class SimulationTests(unittest.TestCase):
    def run_field(self, field, step=60, duration=3600, boat=None, allow_missing=False):
        return simulate(boat or ConstantBoat(leeway=0), SyntheticEnvironment(field),
                        START, duration, step, allow_missing_current=allow_missing)

    def test_constant_reference_cases(self):
        # Handräknat: förflyttning i NM efter 1 h = vektor i knop.
        for name, current, expected, speed, course in (
            ("utan ström", Vector(0, 0), Vector(5, 0), 5, 90),
            ("medström", Vector(2, 0), Vector(7, 0), 7, 90),
            ("motström", Vector(-2, 0), Vector(3, 0), 3, 90),
            ("sidoström", Vector(0, 2), Vector(5, 2), math.sqrt(29),
             math.degrees(math.atan2(5, 2))),
        ):
            with self.subTest(name=name):
                steps = self.run_field(lambda p, t: Conditions(current.scaled(KNOT)))
                end = steps[-1]
                self.assertAlmostEqual(end.end_position.east, expected.east * 1852, delta=1e-8)
                self.assertAlmostEqual(end.end_position.north, expected.north * 1852, delta=1e-8)
                self.assertAlmostEqual(end.midpoint.ground.speed / KNOT, speed, delta=.001)
                self.assertAlmostEqual(end.midpoint.ground.course, course, delta=.01)

    def test_time_varying_current(self):
        # c_öst(t) = 2*t/3600 knop; integral över 1 h = 1 NM.
        steps = self.run_field(lambda p, t: Conditions(
            Vector(2 * KNOT * (t - START).total_seconds() / 3600, 0)))
        self.assertAlmostEqual(steps[-1].end_position.east, 6 * 1852, delta=1e-8)
        self.assertNotEqual(steps[0].midpoint.current, steps[-1].midpoint.current)

    def test_position_and_time_midpoint(self):
        calls = []
        def field(p, t):
            calls.append((p, t))
            return Conditions(Vector(p.east / 1000 + (t - START).total_seconds() / 100, 0))
        steps = self.run_field(field, step=10, duration=10)
        # v0=5K; p_half=25K; c_half=25K/1000+0.05.
        expected = 10 * (5 * KNOT + 25 * KNOT / 1000 + .05)
        self.assertAlmostEqual(steps[-1].end_position.east, expected)
        self.assertAlmostEqual(calls[1][0].east, 25 * KNOT)
        self.assertEqual((calls[1][1] - START).total_seconds(), 5)

    def test_spatial_convergence(self):
        # x'=v+x/1000 => x(t)=1000*v*(exp(t/1000)-1).
        exact = 1000 * 5 * KNOT * math.expm1(.1)
        errors = []
        for dt in (20, 10):
            steps = self.run_field(lambda p, t: Conditions(Vector(p.east / 1000, 0)),
                                   step=dt, duration=100)
            errors.append(abs(steps[-1].end_position.east - exact))
        self.assertLess(errors[1], errors[0] / 3)

    def test_missing_partial_invalid_and_zero(self):
        for value in (None, Vector(float("nan"), 0)):
            steps = self.run_field(lambda p, t: Conditions(value, "datalucka"), allow_missing=True)
            data = json.loads(export(steps))
            self.assertEqual(data["current_coverage"], "saknas helt")
            self.assertIn("datalucka", data["steps"][0]["midpoint"]["assumptions"][0])
            self.assertAlmostEqual(steps[-1].end_position.east, 5 * 1852)
        steps = self.run_field(lambda p, t: Conditions(
            Vector(2 * KNOT, 0) if (t - START).total_seconds() < 1800 else None,
            "prognosens slut"), allow_missing=True)
        self.assertEqual(json.loads(export(steps))["current_coverage"], "delvis")
        self.assertAlmostEqual(steps[-1].end_position.east, 6 * 1852)
        zero = self.run_field(lambda p, t: Conditions(Vector(0, 0)))
        self.assertEqual(json.loads(export(zero))["current_coverage"], "full vid uppslag")
        self.assertFalse(zero[0].midpoint.assumptions)

    def test_zero_ground_speed_and_leeway(self):
        steps = self.run_field(lambda p, t: Conditions(Vector(-5 * KNOT, 0)))
        self.assertIsNone(steps[0].midpoint.ground.course)
        for angle in (10, -10):
            steps = self.run_field(lambda p, t: Conditions(Vector(0, 2 * KNOT)),
                                   boat=ConstantBoat(leeway=angle))
            ground = steps[0].midpoint.ground
            self.assertAlmostEqual(ground.east / KNOT, 5 * math.cos(math.radians(angle)))
            self.assertAlmostEqual(ground.north / KNOT, 2 - 5 * math.sin(math.radians(angle)))

    def test_missing_wind_model_separate_assumption(self):
        steps = self.run_field(lambda p, t: Conditions(None), boat=ConstantBoat(), allow_missing=True)
        self.assertEqual(len(steps[0].midpoint.assumptions), 2)

    def test_missing_current_rejected_by_default(self):
        for current in (None, Vector(float("nan"), 0), Vector(0, float("inf"))):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, "Strömdata saknas"):
                self.run_field(lambda p, t: Conditions(current))

    def test_forecast_validity_and_export(self):
        end = START + timedelta(seconds=1800)
        field = lambda p, t: Conditions(Vector(2 * KNOT, 0), source="reference",
                                        version="test-1", valid_from=START, valid_until=end)
        with self.assertRaisesRegex(ValueError, "prognosens slut"):
            self.run_field(field)
        steps = self.run_field(field, allow_missing=True)
        # Giltig medström en halvtimme, sedan explicit nollströmsantagande.
        self.assertAlmostEqual(steps[-1].end_position.east, 6 * 1852, delta=1e-8)
        data = json.loads(export(steps))
        self.assertEqual(data["current_coverage"], "delvis")
        sample = data["steps"][-1]["midpoint"]
        self.assertEqual(sample["valid_until"], end.isoformat())
        self.assertEqual(sample["source"], "reference")
        self.assertEqual(sample["version"], "test-1")
        self.assertIn("prognosens slut", sample["assumptions"][0])
        future = lambda p, t: Conditions(Vector(0, 0), valid_from=START + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "före prognosens giltighetstid"):
            self.run_field(future)

    def test_missing_at_predicted_midpoint(self):
        # Båten når x=5 m vid mittpunkten; bara startuppslaget är täckt.
        field = lambda p, t: Conditions(Vector(0, 0) if p.east < 4 else None, "utanför området")
        with self.assertRaisesRegex(ValueError, "utanför området"):
            self.run_field(field, boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0),
                           duration=10, step=10)

    def test_step_shortened_at_forecast_boundary(self):
        boundary = START + timedelta(seconds=45)
        boat = ConstantBoat(speed_knots=1 / KNOT, leeway=0)
        for midpoint_only in (False, True):
            field = lambda p, t: Conditions(
                Vector(0, 0), valid_until=boundary if t > START or not midpoint_only else None)
            for duration in (40, 45):
                steps = self.run_field(field, boat=boat, duration=duration)
                self.assertAlmostEqual(steps[-1].end_position.east, duration, delta=1e-8)
                self.assertEqual(steps[-1].end_time, START + timedelta(seconds=duration))
            with self.assertRaisesRegex(ValueError, 'prognosens slut'):
                self.run_field(field, boat=boat, duration=60)

    def test_boundary_fallback_is_explicit_and_exported(self):
        boundary = START + timedelta(seconds=45)
        field = lambda p, t: Conditions(Vector(1, 0), valid_until=boundary)
        steps = self.run_field(field, duration=60, allow_missing=True,
                               boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].end_time, boundary)
        self.assertEqual(steps[0].midpoint.current_status, 'valid')
        self.assertEqual(steps[1].start.current_status, 'assumed_zero')
        self.assertEqual(steps[1].midpoint.current_status, 'assumed_zero')
        self.assertIn('prognosens slut', steps[1].midpoint.assumptions[0])
        self.assertAlmostEqual(steps[-1].end_position.east, 105, delta=1e-8)
        self.assertEqual(json.loads(export(steps))['current_coverage'], 'delvis')

    def test_fallback_until_forecast_starts(self):
        boundary = START + timedelta(seconds=45)
        field = lambda p, t: Conditions(Vector(1, 0), valid_from=boundary)
        steps = self.run_field(field, duration=60, allow_missing=True,
                               boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0))
        self.assertEqual(steps[0].end_time, boundary)
        self.assertEqual(steps[0].midpoint.current_status, 'assumed_zero')
        self.assertEqual(steps[1].midpoint.current_status, 'valid')
        self.assertAlmostEqual(steps[-1].end_position.east, 75, delta=1e-8)

    def test_shortened_midpoint_recomputes_time_and_position(self):
        boundary = START + timedelta(seconds=45)
        calls = []
        def field(p, t):
            calls.append((p.east, (t - START).total_seconds()))
            return Conditions(Vector((t - START).total_seconds() / 100, 0),
                              valid_until=boundary if t > START else None)
        steps = self.run_field(field, duration=45, step=60,
                               boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0))
        # x'=1+t/100 => x(45)=45+45²/200. Midpoint x prediction = 22.5 m.
        self.assertAlmostEqual(steps[-1].end_position.east, 55.125, delta=1e-8)
        self.assertIn((22.5, 22.5), calls)
        # A full 60 s request also must recompute the initially sampled 30 s midpoint.
        calls.clear()
        steps = self.run_field(field, duration=60, step=60, allow_missing=True,
                               boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0))
        self.assertEqual(steps[0].end_time, boundary)
        self.assertAlmostEqual(steps[0].end_position.east, 55.125, delta=1e-8)
        self.assertIn((30.0, 30.0), calls)
        self.assertIn((22.5, 22.5), calls)

    def test_changed_forecast_at_boundary_is_used(self):
        boundary = START + timedelta(seconds=45)
        def field(p, t):
            return Conditions(Vector(0 if t < boundary else 2, 0),
                              valid_from=START if t < boundary else boundary,
                              valid_until=boundary if t < boundary else START + timedelta(seconds=120))
        for step in (60, 30):
            with self.subTest(step=step):
                steps = self.run_field(field, duration=60, step=step,
                                       boat=ConstantBoat(speed_knots=1 / KNOT, leeway=0))
                # 1 m/s for 45 s, then 3 m/s for 15 s.
                self.assertAlmostEqual(steps[-1].end_position.east, 90, delta=1e-8)
                self.assertIn(boundary, [s.end_time for s in steps])

    def test_stronger_counter_current_and_drifting_boat(self):
        steps = self.run_field(lambda p, t: Conditions(Vector(-6 * KNOT, 0)))
        self.assertAlmostEqual(steps[-1].end_position.east, -1852, delta=1e-8)
        self.assertAlmostEqual(steps[0].midpoint.ground.course, 270, delta=.01)
        drift = self.run_field(lambda p, t: Conditions(Vector(0, 2 * KNOT)),
                               boat=ConstantBoat(speed_knots=0, leeway=0))
        self.assertAlmostEqual(drift[-1].end_position.north, 3704, delta=1e-8)

    def test_invalid_forecast_validity(self):
        for values in ({"valid_from": START.replace(tzinfo=None)},
                       {"valid_from": START, "valid_until": START}):
            with self.assertRaises(ValueError):
                Conditions(Vector(0, 0), **values)

    def test_boat_evaluated_at_simulated_position_and_time(self):
        class PositionTimeBoat:
            def evaluate(self, position, time, weather):
                return Vector(1 + position.east / 100 + (time - START).total_seconds() / 10, 0), ()
        # Start: v=1 m/s. Mittpunkt: x=5 m, t=5 s, v=1.55 m/s.
        steps = self.run_field(lambda p, t: Conditions(Vector(0, 0)),
                               boat=PositionTimeBoat(), step=10, duration=10)
        self.assertAlmostEqual(steps[-1].end_position.east, 15.5, delta=1e-8)

    def test_repeatability_and_empty_coverage(self):
        field = lambda p, t: Conditions(Vector(0, 2 * KNOT))
        self.assertEqual(export(self.run_field(field)), export(self.run_field(field)))
        self.assertEqual(json.loads(export(self.run_field(field, duration=0)))["current_coverage"],
                         "ej utvärderad")

    def test_invalid_boat_and_position(self):
        for values in ({"speed_knots": -1}, {"heading": float("nan")},
                       {"leeway": float("inf")}):
            with self.assertRaises(ValueError):
                ConstantBoat(**values)
        with self.assertRaisesRegex(ValueError, "startposition"):
            simulate(ConstantBoat(), SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0))),
                     START, 10, position=Vector(float("nan"), 0))

    def test_invalid_parameters_and_final_short_step(self):
        environment = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0)))
        for duration, dt in ((-1, 60), (10, 0), (float("nan"), 60)):
            with self.assertRaises(ValueError):
                simulate(ConstantBoat(), environment, START, duration, dt)
        with self.assertRaises(ValueError):
            simulate(ConstantBoat(), environment, START.replace(tzinfo=None), 10)
        steps = self.run_field(environment.field, duration=65)
        self.assertEqual((steps[-1].end_time - START).total_seconds(), 65)
        self.assertAlmostEqual(steps[-1].end_position.east, 5 * KNOT * 65)


if __name__ == "__main__":
    unittest.main()
