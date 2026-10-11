import json
import math
import unittest
from datetime import datetime, timezone, timedelta

from prototype.calculation import sail_to_target
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.model import KNOT, Vector
from prototype.presentation import export_voyage

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class VoyageTests(unittest.TestCase):
    def voyage(self, current, **kwargs):
        field = current if callable(current) else lambda p, t: Conditions(current.scaled(KNOT))
        return sail_to_target(SyntheticEnvironment(field), START,
                              kwargs.pop('target', Vector(5 * 1852, 0)), **kwargs)

    def test_constant_hand_references_and_halved_step(self):
        # 5 NM / (5, 7, 3, sqrt(21)) knop.
        for current, speed, heading in ((Vector(0, 0), 5, 90),
                                       (Vector(2, 0), 7, 90),
                                       (Vector(-2, 0), 3, 90),
                                       (Vector(0, 2), math.sqrt(21), 113.578178)):
            results = []
            for dt in (120, 60):
                with self.subTest(current=current, dt=dt):
                    result = self.voyage(current, step_seconds=dt)
                    self.assertEqual(result.status, 'arrived')
                    self.assertLessEqual((result.end_position - result.target).speed, .01)
                    self.assertAlmostEqual(result.travel_seconds, 5 / speed * 3600, delta=.01)
                    for step in result.steps:
                        self.assertAlmostEqual(step.midpoint.water.speed / KNOT, 5, delta=1e-9)
                        self.assertAlmostEqual(step.midpoint.water.course, heading, delta=.001)
                        self.assertAlmostEqual(step.midpoint.ground.course, 90, delta=.001)
                    results.append(result.travel_seconds)
            self.assertAlmostEqual(*results, delta=.01)

    def test_infeasible_currents_and_minimum_progress(self):
        for current in (Vector(0, 6), Vector(0, 5), Vector(-5, 0), Vector(-6, 0)):
            result = self.voyage(current)
            self.assertEqual(result.status, 'infeasible')
            self.assertIsNone(result.travel_seconds)
            self.assertEqual(result.elapsed_seconds, 0)
        result = self.voyage(Vector(-4.99, 0), min_progress_m_s=.01)
        self.assertEqual(result.status, 'infeasible')

    def test_linear_time_current_reference(self):
        # x/1852 = 5*u + u², u=t/3600. Mål 5 NM => u=(-5+sqrt(45))/2.
        field = lambda p, t: Conditions(Vector(2 * KNOT * (t - START).total_seconds() / 3600, 0))
        exact = (math.sqrt(45) - 5) / 2 * 3600
        for dt in (120, 60):
            result = self.voyage(field, step_seconds=dt)
            self.assertEqual(result.status, 'arrived')
            self.assertAlmostEqual(result.travel_seconds, exact, delta=.01)
            self.assertNotEqual(result.steps[0].midpoint.current, result.steps[-1].midpoint.current)

    def test_nonlinear_time_current_convergence(self):
        # c=2*u² knop => x/1852=5*u+2*u³/3; välj mål vid exakt t=3600 s.
        field = lambda p, t: Conditions(Vector(
            2 * KNOT * ((t - START).total_seconds() / 3600) ** 2, 0))
        errors = []
        for dt in (240, 120):
            result = self.voyage(field, step_seconds=dt, target=Vector((5 + 2 / 3) * 1852, 0))
            self.assertEqual(result.status, 'arrived')
            errors.append(abs(result.travel_seconds - 3600))
        self.assertLess(errors[1], errors[0] / 3)
        self.assertLess(errors[1], .2)

    def test_limits_and_already_at_target(self):
        result = self.voyage(Vector(0, 0), max_seconds=65)
        self.assertEqual(result.status, 'limit_reached')
        self.assertEqual(result.elapsed_seconds, 65)
        self.assertIsNone(result.travel_seconds)
        result = self.voyage(Vector(0, 0), max_steps=2)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.status, 'limit_reached')
        result = self.voyage(Vector(0, 0), target=Vector(.005, 0))
        self.assertEqual(result.travel_seconds, 0)
        self.assertFalse(result.steps)

    def test_data_and_midpoint_failure(self):
        for field in (lambda p, t: Conditions(None),
                      lambda p, t: Conditions(Vector(0, 0), valid_until=START),
                      lambda p, t: Conditions(Vector(float('nan'), 0))):
            result = self.voyage(field)
            self.assertEqual(result.status, 'data_unavailable')
            self.assertIsNone(result.travel_seconds)
        field = lambda p, t: Conditions(Vector(0, (6 * KNOT if t > START else 0)))
        self.assertEqual(self.voyage(field).status, 'infeasible')

    def test_arbitrary_direction_export_and_determinism(self):
        result = self.voyage(Vector(0, 0), position=Vector(100, 200), target=Vector(-2900, 4200))
        self.assertAlmostEqual(result.travel_seconds, 5000 / (5 * KNOT), delta=.01)
        self.assertLessEqual((result.end_position - result.target).speed, .01)
        data = json.loads(export_voyage(result))
        self.assertEqual(data['status'], 'arrived')
        self.assertIn('steering_degrees', data['steps'][0])
        self.assertTrue(data['assumptions'])
        self.assertEqual(export_voyage(self.voyage(Vector(0, 2))),
                         export_voyage(self.voyage(Vector(0, 2))))

    def test_validation(self):
        for args in ({'speed_knots': 0}, {'step_seconds': 0}, {'max_seconds': -1},
                     {'tolerance_m': 0}, {'min_progress_m_s': -1}, {'max_steps': 0},
                     {'target': Vector(float('inf'), 0)}):
            with self.assertRaises(ValueError):
                self.voyage(Vector(0, 0), **args)
        with self.assertRaises(ValueError):
            sail_to_target(SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0))),
                           START.replace(tzinfo=None), Vector(100, 0))
