"""Explicit departure objectives, shared clock/data and per-departure constraints."""
import json
import unittest
from dataclasses import replace
from datetime import timedelta, timezone
from prototype.departures import compare_departures
from prototype.environment import SyntheticEnvironment
from prototype.forecast import FixedClock
from prototype.model import Vector
from prototype.presentation import export_departure_comparison
from prototype.routes import RouteCandidate
from test_forecast_quality import PLAN, START, AGE, WEATHER, fresh
from prototype.model import ConstantBoat, KNOT

DIRECT = RouteCandidate('direct')
DETOUR = RouteCandidate('detour', (Vector(0, 20), Vector(100, 20)))
LATER = START + timedelta(seconds=200)


def compare(field, times=(START, LATER), candidates=(DIRECT, DETOUR), **options):
    return compare_departures(SyntheticEnvironment(field), iter(times), Vector(100, 0),
                              iter(candidates), clock=options.pop('clock', FixedClock(PLAN)),
                              boat=options.pop('boat', ConstantBoat(1 / KNOT)),
                              weather_policy=WEATHER, forecast_policy=AGE,
                              step_seconds=2, **options)


class DepartureTests(unittest.TestCase):
    def test_duration_and_arrival_are_distinct_with_explicit_selection(self):
        def field(p, t):
            return replace(fresh(), current=Vector(.5 if t >= LATER else 0, 0))
        result = compare(field)
        self.assertEqual(result.status, 'compared')
        self.assertIsNone(result.selected)
        self.assertEqual(result.shortest_travel.departure_time, LATER)
        self.assertEqual(result.earliest_arrival.departure_time, START)
        self.assertAlmostEqual(result.shortest_travel.travel_seconds, 100 / 1.5, places=5)
        self.assertEqual(result.earliest_arrival.travel_seconds, 100)
        self.assertGreater(result.shortest_travel.arrival_time, result.earliest_arrival.arrival_time)
        for criterion, departure in [('shortest_travel_time', LATER), ('earliest_arrival', START)]:
            self.assertEqual(compare(field, selection_criterion=criterion).selected.departure_time, departure)

    def test_weather_changes_route_and_preserves_failure_evidence(self):
        def field(p, t):
            unsafe = t >= LATER and 40 <= p.east <= 60 and p.north < 1
            record = fresh()
            return replace(record, waves=replace(record.waves, height_m=1.1 if unsafe else .2))
        result = compare(field)
        self.assertEqual(result.departures[0].routes.fastest.candidate, DIRECT)
        self.assertEqual(result.departures[1].routes.fastest.candidate, DETOUR)
        failed = result.departures[1].routes.candidates[0]
        self.assertEqual(failed.status, 'weather_limit')
        self.assertTrue(failed.reason)
        self.assertIsNone(failed.arrival_time)
        payload = json.loads(export_departure_comparison(result))
        self.assertEqual(payload['departures'][1]['routes']['candidates'][0]['reason'], failed.reason)
        self.assertIn('comfort_exposure', payload['departures'][0]['routes']['candidates'][0])

    def test_comfort_cap_is_relative_to_same_departure(self):
        def field(p, t):
            record = fresh()
            return replace(record, current=Vector(0, 0) if t < LATER else Vector(.5, 0),
                           waves=replace(record.waves, height_m=1 / (1 + max(0, p.north) / 10)))
        result = compare(field, max_comfort_extra_seconds=40)
        self.assertEqual(result.departures[0].routes.comfortable.candidate, DETOUR)
        # The later direct route is faster than either early route; it must not
        # disqualify the early comfortable route through a global duration cap.
        self.assertLess(result.departures[1].routes.fastest.travel_seconds, 100)
        for row in result.departures:
            self.assertLessEqual(row.routes.comfortable.travel_seconds,
                                 row.routes.fastest.travel_seconds + 40)

    def test_no_feasible_departure_has_no_selection(self):
        def field(p, t):
            return replace(fresh(), wind=Vector(6, 0))
        result = compare(field, selection_criterion='earliest_arrival')
        self.assertEqual(result.status, 'no_feasible_departure')
        self.assertIsNone(result.selected)
        self.assertIsNone(result.shortest_travel)
        self.assertIsNone(result.earliest_arrival)
        for row in result.departures:
            self.assertIsNone(row.routes.fastest)
            self.assertIsNone(row.routes.comfortable)
            self.assertTrue(all(r.status == 'weather_limit' and r.reason for r in row.routes.candidates))

    def test_planning_clock_once_and_same_boat_forecast_for_every_route(self):
        class CountingClock:
            calls = 0
            def now(self):
                self.calls += 1
                return PLAN + timedelta(hours=self.calls - 1)
        clock = CountingClock()
        record = fresh()
        boat = ConstantBoat(1 / KNOT)
        result = compare(lambda p, t: record, clock=clock, boat=boat)
        self.assertEqual(clock.calls, 1)
        self.assertEqual(result.planning_time, PLAN)
        for row in result.departures:
            self.assertEqual(row.routes.planning_time, PLAN)
            self.assertEqual(row.routes.weather_policy, WEATHER)
            self.assertEqual(row.routes.forecast_policy, AGE)
            self.assertIsNotNone(row.routes.fastest)
            for route in row.routes.candidates:
                for leg in route.legs:
                    self.assertEqual(leg.planning_time, PLAN)

    def test_bounded_unique_explicit_inputs_and_ties(self):
        field = lambda p, t: fresh()
        for times in ((), (START, START.astimezone(timezone(timedelta(hours=1)))), (START, LATER, LATER + timedelta(seconds=1))):
            with self.assertRaises(ValueError):
                compare(field, times=times, max_departures=2)
        for limit in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                compare(field, max_departures=limit)
        with self.assertRaises(ValueError):
            compare(field, selection_criterion='best')
        with self.assertRaises(ValueError):
            compare(field, max_candidates=1)
        result = compare(field, times=(LATER, START))
        self.assertEqual(result.shortest_travel.departure_time, LATER)
        self.assertEqual(result.earliest_arrival.departure_time, START)

    def test_one_shot_obstacles_remain_active_for_all_departures(self):
        from prototype.obstacles import Rectangle
        result = compare(lambda p, t: fresh(), candidates=(DIRECT,),
                         obstacles=iter((Rectangle('box', 40, -10, 60, 10),)))
        self.assertEqual(result.status, 'no_feasible_departure')
        self.assertTrue(all(row.routes.candidates[0].status == 'blocked'
                            for row in result.departures))

    def test_missing_clock_and_naive_departure_rejected(self):
        with self.assertRaises(ValueError):
            compare(lambda p, t: fresh(), clock=None)
        with self.assertRaises(ValueError):
            compare(lambda p, t: fresh(), times=(START.replace(tzinfo=None),))
