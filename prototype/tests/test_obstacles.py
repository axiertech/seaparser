import unittest
from datetime import datetime, timezone

from prototype.obstacles import Rectangle, ObstacleCollision
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.calculation import simulate, sail_to_target
from prototype.presentation import export_voyage
import json

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
ZERO = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0)))


class ObstacleTests(unittest.TestCase):
    def test_whole_segment_crossings_and_contacts(self):
        box = Rectangle('ö', 4, -1, 6, 1)
        for a, b in ((Vector(0, 0), Vector(10, 0)),
                     (Vector(5, -3), Vector(5, 3)),
                     (Vector(0, -5), Vector(10, 5)),
                     (Vector(0, 1), Vector(10, 1)),
                     (Vector(3, 2), Vector(5, 0)),
                     (Vector(4, 1), Vector(4, 1)),
                     (Vector(5, 0), Vector(5, 0))):
            with self.subTest(a=a, b=b):
                self.assertTrue(box.intersects(a, b))
                self.assertTrue(box.intersects(b, a))
        for a, b in ((Vector(0, 1.001), Vector(10, 1.001)),
                     (Vector(0, 0), Vector(3.999, 0)),
                     (Vector(7, 0), Vector(7, 0))):
            self.assertFalse(box.intersects(a, b))

    def test_margin_and_validation(self):
        self.assertTrue(Rectangle('marginal', 4, -1, 6, 1, .1).intersects(
            Vector(0, 1.05), Vector(10, 1.05)))
        for bounds in ((4, -1, 4, 1), (4, -1, 6, 1, -1), (float('nan'), -1, 6, 1)):
            with self.assertRaises(ValueError):
                Rectangle('fel', *bounds)

    def test_motion_checks_drifted_whole_segment(self):
        env = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 1)))
        # Integrerat segment (0,0)->(10,10), båda ändpunkter utanför hindret.
        with self.assertRaises(ObstacleCollision):
            simulate(ConstantBoat(speed_knots=1/KNOT, leeway=0), env, START, 10, 10,
                     obstacles=(Rectangle('mitt', 4, 4, 6, 6),))
        # Startkontroll även vid noll varaktighet.
        with self.assertRaises(ObstacleCollision):
            simulate(ConstantBoat(), ZERO, START, 0,
                     obstacles=(Rectangle('start', -1, -1, 1, 1),))

    def test_target_whole_segment_blocked_independent_of_step(self):
        box = Rectangle('smal', 49, -1, 51, 1)
        for dt in (200, 100, 10):
            result = sail_to_target(ZERO, START, Vector(100, 0), speed_knots=1/KNOT,
                                    step_seconds=dt, obstacles=(box,))
            self.assertEqual(result.status, 'blocked')
            self.assertIsNone(result.travel_seconds)
            self.assertLess(result.end_position.east, 49)
            for step in result.steps:
                self.assertFalse(box.intersects(step.start.position, step.end_position))
            self.assertEqual(json.loads(export_voyage(result))['status'], 'blocked')

    def test_start_target_and_tolerance_cannot_bypass_obstacle(self):
        for position, target, box in (
            (Vector(0,0), Vector(100,0), Rectangle('start', -1,-1,1,1)),
            (Vector(0,0), Vector(100,0), Rectangle('mål', 99,-1,101,1)),
            (Vector(0,0), Vector(.005,0), Rectangle('nära mål', .004,-1,.006,1)),
        ):
            result = sail_to_target(ZERO, START, target, position=position, obstacles=(box,))
            self.assertEqual(result.status, 'blocked')
            self.assertFalse(result.steps)

    def test_shortened_arrival_does_not_check_past_target(self):
        result = sail_to_target(ZERO, START, Vector(10,0), speed_knots=1/KNOT,
                                step_seconds=100, obstacles=(Rectangle('bakom',11,-1,12,1),))
        self.assertEqual(result.status, 'arrived')
        self.assertAlmostEqual(result.travel_seconds, 10, delta=.001)

    def test_clear_detour_leg_and_close_target(self):
        result = sail_to_target(ZERO, START, Vector(100,0), position=Vector(0,2),
                                obstacles=(Rectangle('utanför',49,-2,51,-1),))
        self.assertEqual(result.status, 'arrived')
        result = sail_to_target(ZERO, START, Vector(.02,0))
        self.assertEqual(result.status, 'arrived')
        self.assertLessEqual((result.end_position-result.target).speed, .01)

    def test_decreasing_current_reference_and_halved_step(self):
        # c(t)=2-2*t/3600 knop. x/1852=7*u-u², mål 5 => u=(7-sqrt(29))/2.
        import math
        env = SyntheticEnvironment(lambda p,t: Conditions(Vector(
            KNOT*(2-2*(t-START).total_seconds()/3600),0)))
        exact = (7-math.sqrt(29))/2*3600
        times = []
        for dt in (120,60):
            result = sail_to_target(env,START,Vector(5*1852,0),step_seconds=dt)
            self.assertEqual(result.status,'arrived')
            self.assertAlmostEqual(result.travel_seconds,exact,delta=.01)
            times.append(result.travel_seconds)
        self.assertAlmostEqual(*times,delta=.01)
