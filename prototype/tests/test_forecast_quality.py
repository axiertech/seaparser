"""Independent freshness/arrival references with an injected planning clock."""
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from prototype.environment import Conditions, WaveData, SyntheticEnvironment, wind_from
from prototype.forecast import ForecastPolicy, FixedClock
from prototype.routes import compare_routes, RouteCandidate
from prototype.model import KNOT, Vector
from prototype.weather import WeatherPolicy
from prototype.calculation import sail_to_target, simulate
from prototype.model import ConstantBoat
from prototype.presentation import export_route_comparison

PLAN = datetime(2026, 1, 1, tzinfo=timezone.utc)
START = PLAN + timedelta(hours=2)
END = START + timedelta(hours=1)
WEATHER = WeatherPolicy(5, 1)
AGE = ForecastPolicy(max_age_seconds=600)
DIRECT = RouteCandidate('direct')


def fresh():
    issued = PLAN - timedelta(seconds=100)
    return Conditions(Vector(0, 0), wind=wind_from(4, 0), valid_from=START, valid_until=END,
                      issued_at=issued, waves=WaveData(1, 5, 0, START, END, issued_at=issued))


def compare(field, **kwargs):
    env = SyntheticEnvironment(field if callable(field) else lambda p, t: field)
    return compare_routes(env, START, kwargs.pop('target', Vector(100, 0)),
                          kwargs.pop('candidates', [DIRECT]), speed_knots=1 / KNOT,
                          weather_policy=WEATHER, forecast_policy=AGE,
                          clock=kwargs.pop('clock', FixedClock(PLAN)), **kwargs)


class ForecastQualityTests(unittest.TestCase):
    def test_old_forecast_rejected_even_with_future_validity(self):
        for wave_only in (False, True):
            old = PLAN - timedelta(seconds=601)
            record = replace(fresh(), waves=replace(fresh().waves, issued_at=old))
            if not wave_only:
                record = replace(record, issued_at=old)
            result = compare(record)
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
            self.assertIn('för gammal vid planeringen', result.candidates[0].reason)
            self.assertIsNone(result.fastest)
            self.assertIsNone(result.comfortable)

    def test_fresh_forecast_age_uses_planning_time_not_future_eta(self):
        record = replace(fresh(), issued_at=PLAN - timedelta(seconds=600),
                         waves=replace(fresh().waves, issued_at=PLAN - timedelta(seconds=600)))
        result = compare(record)
        self.assertEqual(result.fastest.travel_seconds, 100)
        self.assertEqual(result.planning_time, PLAN)
        self.assertEqual(result.fastest.arrival_checked_time, START + timedelta(seconds=100))
        self.assertEqual(result.fastest.arrival_weather_status, 'passed_at_arrival')
        self.assertEqual(result.fastest.legs[0].forecast_status, 'passed_at_samples_and_arrival')
        # At simulated arrival the issue is >2h old, but at planning it is exactly 600s.
        self.assertGreater((result.fastest.arrival_checked_time - record.issued_at).total_seconds(), 600)

    def test_missing_future_or_naive_issue_times_are_rejected(self):
        for record in (replace(fresh(), issued_at=None),
                       replace(fresh(), waves=replace(fresh().waves, issued_at=None)),
                       replace(fresh(), issued_at=PLAN + timedelta(seconds=1))):
            result = compare(record)
            self.assertEqual(result.candidates[0].status, 'data_unavailable')
        with self.assertRaises(ValueError):
            replace(fresh(), issued_at=PLAN.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            replace(fresh().waves, issued_at='not-a-timestamp')

    def test_clock_is_explicit_and_captured_once_for_all_candidates_and_legs(self):
        class CountingClock:
            calls = 0
            def now(self):
                self.calls += 1
                # If queried again the age limit would fail; one snapshot is required.
                return PLAN + timedelta(seconds=1000 * (self.calls - 1))
        clock = CountingClock()
        via = RouteCandidate('via', (Vector(50, 0),))
        result = compare(fresh(), clock=clock, candidates=[via, DIRECT])
        self.assertEqual(clock.calls, 1)
        self.assertTrue(all(r.status == 'arrived' for r in result.candidates))
        for route in result.candidates:
            self.assertTrue(all(leg.planning_time == PLAN for leg in route.legs))
        with self.assertRaisesRegex(ValueError, 'explicit klocka'):
            compare(fresh(), clock=None)
        with self.assertRaises(ValueError):
            FixedClock(PLAN.replace(tzinfo=None))

    def test_actual_arrival_position_and_time_are_queried(self):
        calls = []
        def field(p, t):
            calls.append((p, t))
            return replace(fresh(), current=Vector((t - START).total_seconds() / 100, 0))
        result = compare(field, step_seconds=10)
        route = result.fastest
        self.assertNotEqual(route.end_position, Vector(100, 0))  # Numerical tolerance; do not snap.
        self.assertEqual(calls[-1], (route.end_position, route.arrival_time))
        self.assertEqual(route.arrival_checked_time, route.arrival_time)
        self.assertEqual(route.legs[-1].arrival_observation.current,
                         Vector((route.arrival_time - START).total_seconds() / 100, 0))

    def test_exceeded_weather_or_missing_data_only_at_destination_rejects_route(self):
        for violation in ('wind', 'wave', 'missing', 'old'):
            def field(p, t):
                record = fresh()
                if p.east >= 100:
                    if violation == 'wind':
                        return replace(record, wind=wind_from(6, 0))
                    if violation == 'wave':
                        return replace(record, waves=replace(record.waves, height_m=2))
                    if violation == 'old':
                        return replace(record, issued_at=PLAN - timedelta(seconds=601))
                    return replace(record, waves=None)
                return record
            result = compare(field, step_seconds=60)
            route = result.candidates[0]
            self.assertEqual(route.status, 'weather_limit' if violation in ('wind', 'wave') else 'data_unavailable')
            self.assertTrue(route.destination_reached)
            self.assertEqual(route.elapsed_seconds, 100)
            self.assertEqual(route.end_position, Vector(100, 0))
            self.assertEqual(route.arrival_checked_time, START + timedelta(seconds=100))
            self.assertIn('Ankomstkontroll', route.reason)
            self.assertIsNone(route.travel_seconds)
            self.assertIsNone(route.comfort_exposure)
            self.assertIsNone(result.fastest)
            self.assertIsNone(result.comfortable)

    def test_arrival_exactly_at_validity_end_needs_next_forecast(self):
        boundary = START + timedelta(seconds=100)
        for next_record in (False, True):
            def field(p, t):
                record = fresh()
                if next_record and t >= boundary:
                    return replace(record, valid_from=boundary, version='next',
                                   waves=replace(record.waves, valid_from=boundary, version='next'))
                return replace(record, valid_until=boundary,
                               waves=replace(record.waves, valid_until=boundary))
            result = compare(field)
            route = result.candidates[0]
            self.assertTrue(route.destination_reached)
            self.assertEqual(route.arrival_checked_time, boundary)
            if next_record:
                self.assertEqual(route.status, 'arrived')
                self.assertEqual(route.legs[-1].arrival_observation.version, 'next')
            else:
                self.assertEqual(route.status, 'data_unavailable')
                self.assertIsNone(result.fastest)

    def test_zero_distance_also_checks_issue_time_and_arrival_weather(self):
        result = compare(replace(fresh(), issued_at=None), target=Vector(0, 0))
        route = result.candidates[0]
        self.assertTrue(route.destination_reached)
        self.assertEqual(route.arrival_checked_time, START)
        self.assertEqual(route.status, 'data_unavailable')

    def test_fixed_heading_simulation_uses_same_planning_age(self):
        env = SyntheticEnvironment(lambda p, t: fresh())
        steps = simulate(ConstantBoat(speed_knots=1 / KNOT, leeway=0), env, START, 100,
                         weather_policy=WEATHER, forecast_policy=AGE, clock=FixedClock(PLAN))
        self.assertEqual(steps[-1].end_time, START + timedelta(seconds=100))
        self.assertTrue(all(s.start.planning_time == PLAN and s.start.forecast_checked for s in steps))

    def test_metadata_export_and_legacy_unchecked_age(self):
        result = compare(fresh())
        data = json.loads(export_route_comparison(result))
        self.assertEqual(data['planning_time'], PLAN.isoformat())
        self.assertEqual(data['forecast_policy']['max_age_seconds'], 600)
        leg = data['candidates'][0]['legs'][0]
        self.assertEqual(leg['arrival_weather_status'], 'passed_at_arrival')
        self.assertEqual(leg['arrival_observation']['issued_at'], fresh().issued_at.isoformat())
        self.assertIn('ingen kontinuerlig verifiering', data['weather_verification_scope'])
        self.assertEqual(leg['weather_verification_scope'], data['weather_verification_scope'])
        legacy = sail_to_target(SyntheticEnvironment(lambda p, t: Conditions(Vector(0, 0))),
                                START, Vector(100, 0), speed_knots=1 / KNOT)
        self.assertTrue(legacy.destination_reached)
        self.assertEqual(legacy.arrival_weather_status, 'not_requested')
        self.assertEqual(legacy.forecast_status, 'not_requested')
        self.assertIsNone(legacy.arrival_observation)

    def test_age_configuration_and_timezone_normalization(self):
        for limit in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                ForecastPolicy(limit)
        offset = timezone(timedelta(hours=2))
        normalized = FixedClock(PLAN.astimezone(offset))
        self.assertEqual(normalized.now(), PLAN)
        exact = replace(fresh(), issued_at=PLAN, waves=replace(fresh().waves, issued_at=PLAN))
        ForecastPolicy(0).check(exact, normalized.now())

    def test_destination_failure_removes_candidate_from_both_rankings(self):
        direct = DIRECT
        detour = RouteCandidate('detour', (Vector(0, 20), Vector(100, 20)))
        def field(p, t):
            # Both candidates share destination, but the direct route arrives in
            # a short unsafe window. A later arrival may still be feasible.
            if p.east >= 100 and abs(p.north) < 1 and t < START + timedelta(seconds=110):
                return replace(fresh(), wind=wind_from(6, 0))
            return fresh()
        result = compare(field, candidates=[direct, detour], step_seconds=10,
                         max_comfort_extra_seconds=1000)
        self.assertEqual(result.candidates[0].status, 'weather_limit')
        self.assertTrue(result.candidates[0].destination_reached)
        self.assertEqual(result.fastest.candidate, detour)
        self.assertEqual(result.comfortable.candidate, detour)
        self.assertEqual(result.fastest.forecast_status, 'passed_at_samples_and_arrival')
