"""Independent geometric/time references for the bounded candidate comparison."""
import math
import json
import unittest
from datetime import datetime, timedelta, timezone
from prototype.routes import RouteCandidate, compare_routes
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.model import KNOT, Vector
from prototype.obstacles import Rectangle
from prototype.presentation import export_route_comparison

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
ZERO = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0)))
TARGET = Vector(100, 0)
BOX = Rectangle('synthetic', 40, -10, 60, 10)
DIRECT = RouteCandidate('direct')
NORTH = RouteCandidate('north', (Vector(30, 20), Vector(70, 20)))
SOUTH = RouteCandidate('south', (Vector(30, -30), Vector(70, -30)))


class RouteTests(unittest.TestCase):
    def compare(self, candidates, **kwargs):
        return compare_routes(kwargs.pop('environment', ZERO), kwargs.pop('start', START),
                              kwargs.pop('target', TARGET), candidates,
                              speed_knots=1 / KNOT, **kwargs)

    def test_free_direct_route_matches_distance_over_speed(self):
        result = self.compare([NORTH, DIRECT])
        self.assertEqual(result.status, 'selected')
        self.assertEqual(result.fastest.candidate, DIRECT)
        self.assertAlmostEqual(result.fastest.travel_seconds, 100, delta=1e-6)
        self.assertEqual(result.fastest.arrival_time, START + timedelta(seconds=100))
        self.assertEqual(result.fastest.end_position, TARGET)
        self.assertIn('ingen global optimalitet', result.scope)

    def test_blocked_direct_route_and_safe_detour(self):
        exact = 2 * math.hypot(30, 20) + 40
        for step in (120, 60):
            result = self.compare([DIRECT, SOUTH, NORTH], obstacles=(b for b in [BOX]),
                                  step_seconds=step)
            self.assertEqual(result.candidates[0].status, 'blocked')
            self.assertIsNone(result.candidates[0].travel_seconds)
            self.assertEqual(result.fastest.candidate, NORTH)
            self.assertAlmostEqual(result.fastest.travel_seconds, exact, delta=.03)
            for route in result.candidates[1:]:
                self.assertEqual(route.status, 'arrived')
                for leg in route.legs:
                    for segment in leg.steps:
                        self.assertFalse(BOX.intersects(segment.start.position, segment.end_position))

    def test_no_feasible_candidate(self):
        result = self.compare([DIRECT, RouteCandidate('inside', (Vector(50, 0),))], obstacles=[BOX])
        self.assertEqual(result.status, 'no_feasible_route')
        self.assertIsNone(result.fastest)
        self.assertEqual([r.status for r in result.candidates], ['blocked', 'blocked'])
        self.assertTrue(all(r.travel_seconds is None and r.arrival_time is None for r in result.candidates))

    def test_time_dependent_current_changes_fastest_route(self):
        # Both detours share their first/last straight legs in opposite hemispheres.
        # At t=20 s southern water gains 0.6 m/s eastward current. Without it,
        # geometrically shorter north wins. The current is below boat speed.
        switch = START + timedelta(seconds=20)
        def field(p, t):
            return Conditions(Vector(.6 if p.north < -1 and t >= switch else 0, 0),
                              valid_from=START if t < switch else switch,
                              valid_until=switch if t < switch else START + timedelta(seconds=1000))
        for step in (2, 1):
            still = self.compare([NORTH, SOUTH], obstacles=[BOX], step_seconds=step)
            moving = self.compare([NORTH, SOUTH], obstacles=[BOX], step_seconds=step,
                                  environment=SyntheticEnvironment(field))
            self.assertEqual(still.fastest.candidate, NORTH)
            self.assertEqual(moving.fastest.candidate, SOUTH)
            self.assertTrue(all(r.status == 'arrived' for r in moving.candidates))
            # Geometry in still water: 2*sqrt(30²+30²)+40 > north's 112.11 m.
            self.assertAlmostEqual(still.candidates[1].travel_seconds,
                                   2 * math.hypot(30, 30) + 40, delta=.03)
            self.assertLess(moving.candidates[1].travel_seconds,
                            moving.candidates[0].travel_seconds - 5)

    def test_real_position_and_time_continue_between_legs(self):
        calls = []
        def field(p, t):
            calls.append((p, t))
            return Conditions(Vector((t - START).total_seconds() / 100, 0))
        result = self.compare([RouteCandidate('via', (Vector(30, 0),))],
                              environment=SyntheticEnvironment(field), step_seconds=5)
        route = result.fastest
        first, second = route.legs
        self.assertEqual(second.steps[0].start.time, first.steps[-1].end_time)
        self.assertEqual(second.steps[0].start.position, first.end_position)
        self.assertIn((first.end_position, first.steps[-1].end_time), calls)
        self.assertGreater(second.steps[0].start.current.east, 0)
        # x(t)=t+t²/200 => x=100 at t=100*(sqrt(3)-1), not two reset clocks.
        self.assertAlmostEqual(route.travel_seconds, 100 * (math.sqrt(3) - 1), delta=.03)

    def test_shared_waypoint_keeps_distinct_arrival_times(self):
        common = Vector(40, 0)
        short = RouteCandidate('short', (common,))
        long = RouteCandidate('long', (Vector(0, 10), common))
        switch = START + timedelta(seconds=50)
        def field(p, t):
            # Fastest prefix arrives at common at 40 s; the other after 50 s.
            # Later current prevents eastward progress: candidates must stay separate.
            return Conditions(Vector(-2 if p.east >= 40 and t >= switch else 0, 0),
                              valid_from=START if t < switch else switch,
                              valid_until=switch if t < switch else START + timedelta(seconds=1000))
        result = self.compare([long, short], target=Vector(45, 0), step_seconds=1,
                              environment=SyntheticEnvironment(field))
        self.assertEqual(result.candidates[0].status, 'infeasible')
        self.assertEqual(result.candidates[1].status, 'arrived')
        self.assertEqual(result.fastest.candidate, short)
        self.assertAlmostEqual(result.fastest.travel_seconds, 45, delta=.03)
        self.assertGreater(result.candidates[0].legs[1].steps[-1].end_time,
                           result.candidates[1].legs[0].steps[-1].end_time)

    def test_later_arrival_at_shared_waypoint_must_not_be_pruned(self):
        common = Vector(40, 0)
        early = RouteCandidate('early', (common,))
        later = RouteCandidate('later', (Vector(0, 10), common))
        switch = START + timedelta(seconds=50)
        def field(p, t):
            # Earlier prefix is infeasible downstream before the tide changes;
            # a longer prefix reaches the SAME waypoint after the change.
            return Conditions(Vector(-2 if p.east >= 40 and t < switch else 0, 0),
                              valid_from=START if t < switch else switch,
                              valid_until=switch if t < switch else START + timedelta(seconds=1000))
        result = self.compare([early, later], target=Vector(45, 0), step_seconds=1,
                              environment=SyntheticEnvironment(field))
        self.assertEqual(result.candidates[0].status, 'infeasible')
        self.assertEqual(result.candidates[1].status, 'arrived')
        self.assertEqual(result.fastest.candidate, later)
        self.assertEqual(result.candidates[0].elapsed_seconds, 40)
        self.assertGreater(result.candidates[1].legs[1].steps[-1].end_time, switch)

    def test_forecast_expiration_in_later_leg_is_preserved(self):
        boundary = START + timedelta(seconds=45)
        field = SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0), valid_until=boundary))
        result = self.compare([RouteCandidate('via', (Vector(30, 0),))], environment=field)
        route = result.candidates[0]
        self.assertEqual(route.status, 'data_unavailable')
        self.assertEqual(route.elapsed_seconds, 45)
        self.assertEqual(route.end_position, Vector(45, 0))
        self.assertEqual(route.legs[-1].steps[-1].end_time, boundary)
        self.assertIsNone(route.travel_seconds)
        self.assertIsNone(result.fastest)

    def test_limits_apply_to_whole_route(self):
        via = RouteCandidate('via', (Vector(30, 0), Vector(60, 0)))
        for args in ({'max_seconds': 50}, {'max_steps': 1}):
            result = self.compare([via], **args)
            route = result.candidates[0]
            self.assertEqual(route.status, 'limit_reached')
            self.assertIsNone(result.fastest)
            self.assertLessEqual(route.elapsed_seconds, args.get('max_seconds', 86400))
            self.assertLessEqual(sum(len(leg.steps) for leg in route.legs), args.get('max_steps', 100000))

    def test_invalid_candidate_sets_and_limits_rejected_before_lookup(self):
        def fail(p, t):
            self.fail('Invalid input must not evaluate the environment')
        env = SyntheticEnvironment(fail)
        for candidates, args in (([], {}), ([DIRECT, DIRECT], {}),
                                  ([NORTH], {'max_waypoints': 1}),
                                  ([NORTH, SOUTH], {'max_candidates': 1}),
                                  ([DIRECT], {'max_steps': 0}),
                                  ([DIRECT], {'max_seconds': float('nan')})):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.compare(candidates, environment=env, **args)
        with self.assertRaises(ValueError):
            RouteCandidate('invalid', (Vector(float('nan'), 0),))

    def test_ties_repeated_waypoints_and_determinism(self):
        same = RouteCandidate('same', (Vector(0, 0), Vector(0, 0)))
        one = self.compare([same, DIRECT])
        two = self.compare([same, DIRECT])
        self.assertEqual(one, two)
        self.assertEqual(one.fastest.candidate, same)
        self.assertEqual(one.fastest.travel_seconds, 100)
        self.assertEqual(len(one.fastest.legs), 3)

    def test_export_includes_selection_scope_and_failed_candidates(self):
        result = self.compare([DIRECT, NORTH], obstacles=[BOX])
        data = json.loads(export_route_comparison(result))
        self.assertEqual(data['fastest_candidate'], 'north')
        self.assertIn('ingen global optimalitet', data['scope'])
        self.assertEqual(data['candidates'][0]['status'], 'blocked')
        self.assertIsNone(data['candidates'][0]['travel_seconds'])
        self.assertEqual(data['candidates'][1]['legs'][0]['current_coverage'], 'full vid uppslag')
        failed = self.compare([DIRECT], obstacles=[BOX])
        self.assertIsNone(json.loads(export_route_comparison(failed))['fastest_candidate'])
        self.assertEqual(export_route_comparison(result), export_route_comparison(result))
