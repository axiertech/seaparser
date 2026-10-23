"""Application scenario acceptance and provenance integrity, offline only."""
import json
import math
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import timedelta
from unittest.mock import patch

from application.planning import ALGORITHM_VERSION, boat_for_model, digest, resolve_boat_model, run_plan
from infrastructure.synthetic_forecast import synthetic_snapshot
from prototype.model import KNOT, Vector
from prototype.routes import RouteCandidate
from prototype.sailing import PolarBoat
from prototype.weather import WeatherPolicy
from scripts.plan_synthetic import demo_request


class PlanningTests(unittest.TestCase):
    def test_polar_scenario_independent_duration_comfort_and_departure_objectives(self):
        report = json.loads(run_plan(demo_request()))
        comparison = report['comparison']
        first = comparison['departures'][0]['routes']
        self.assertEqual(first['fastest_candidate'], 'direct')
        self.assertEqual(first['comfortable_candidate'], 'north')
        routes = {r['candidate']['name']: r for r in first['candidates']}
        # At 4 m/s wind, test polar gives 2 m/s at90deg,1.2 at45,1.6 at135.
        exact = 20*math.sqrt(2)/1.2 + 60/2 + 20*math.sqrt(2)/1.6
        self.assertEqual(routes['direct']['travel_seconds'], 50)
        self.assertAlmostEqual(routes['north']['travel_seconds'], exact, delta=.01)
        self.assertLess(routes['north']['comfort_exposure'], routes['direct']['comfort_exposure'])
        self.assertIsNone(comparison['selected'])
        self.assertNotEqual(comparison['shortest_travel']['departure_time'],
                            comparison['earliest_arrival']['departure_time'])
        self.assertEqual(report['manifest']['algorithm_version'], ALGORITHM_VERSION)
        self.assertTrue(report['manifest']['boat_data_estimated'])

    def test_blocked_scenario_and_later_infeasibility_remain_explicit(self):
        comparison = json.loads(run_plan(demo_request(blocked_direct=True)))['comparison']
        first, later = (row['routes'] for row in comparison['departures'])
        self.assertEqual(first['candidates'][0]['status'], 'blocked')
        self.assertEqual(first['comfortable_candidate'], 'north')
        self.assertIn(first['fastest_candidate'], ('north', 'south'))
        self.assertEqual(later['status'], 'no_feasible_route')
        self.assertIsNone(later['fastest_candidate'])
        self.assertTrue(all(r['reason'] for r in later['candidates']))

    def test_reports_repeat_byte_for_byte_without_fetching(self):
        request = demo_request()
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('urllib.request.urlopen', side_effect=AssertionError('HTTP')):
            a, b = run_plan(request), run_plan(request)
        self.assertEqual(a, b)
        manifest = json.loads(a)['manifest']
        self.assertEqual(len(manifest['input_sha256']), 64)
        self.assertEqual(manifest['dataset_sha256'], digest(asdict(request.dataset)))

    def test_provenance_changes_with_every_material_input(self):
        original = demo_request()
        baseline = json.loads(run_plan(original))['manifest']
        product = original.dataset.products[1]
        values = tuple(tuple(tuple((.1, 0) for node in row) for row in plane) for plane in product.values)
        changed_data = replace(original.dataset, products=(original.dataset.products[0],
                                                           replace(product, values=values), original.dataset.products[2]))
        variants = [replace(original, dataset=changed_data), replace(original, boat=replace(original.boat, heading=80)),
                    replace(original, step_seconds=5), replace(original, weather_policy=WeatherPolicy(6, 1)),
                    replace(original, target=Vector(90, 0)), replace(original, selection_criterion='earliest_arrival'),
                    replace(original, planning_time=original.planning_time+timedelta(seconds=1)),
                    replace(original, departures=original.departures[:1]),
                    replace(original, candidates=original.candidates[:1])]
        for request in variants:
            manifest = json.loads(run_plan(request))['manifest']
            self.assertNotEqual(manifest['input_sha256'], baseline['input_sha256'])
        changed_manifest = json.loads(run_plan(variants[0]))['manifest']
        self.assertEqual(changed_manifest['dataset_id'], baseline['dataset_id'])
        self.assertEqual(changed_manifest['dataset_version'], baseline['dataset_version'])
        self.assertNotEqual(changed_manifest['dataset_sha256'], baseline['dataset_sha256'])
        self.assertNotEqual(json.loads(run_plan(variants[1]))['manifest']['boat_sha256'], baseline['boat_sha256'])

    def test_request_copies_sequences_and_rejects_unfrozen_inputs(self):
        original = demo_request()
        times, candidates = list(original.departures), list(original.candidates)
        request = replace(original, departures=times, candidates=candidates)
        times.clear()
        candidates.append(RouteCandidate('extra'))
        self.assertEqual(request.departures, original.departures)
        self.assertEqual(request.candidates, original.candidates)
        with self.assertRaises(FrozenInstanceError):
            request.step_seconds = 20
        with self.assertRaises(ValueError):
            replace(original, dataset=lambda: synthetic_snapshot())
        with self.assertRaises(ValueError):
            replace(original, weather_policy=None)
        with self.assertRaises(ValueError):
            replace(original, departures=iter(original.departures), max_departures=1)
        with self.assertRaises(ValueError):
            replace(original, candidates=iter(original.candidates), max_candidates=2)

    def test_cli_is_repeatable_and_rejects_bad_step_without_traceback(self):
        command = [sys.executable, '-B', '-m', 'scripts.plan_synthetic', '--boat', 'constant']
        a = subprocess.run(command, capture_output=True, text=True, check=True)
        b = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(a.stdout, b.stdout)
        first = json.loads(a.stdout)['comparison']['departures'][0]['routes']
        self.assertEqual(first['candidates'][0]['travel_seconds'], 100)
        self.assertEqual(first['comfortable_candidate'], 'north')
        invalid = subprocess.run(command+['--step-seconds', 'nan'], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertFalse(invalid.stdout)
        self.assertNotIn('Traceback', invalid.stderr)

    def test_motorboat_planning(self):
        """A motorboat profile yields a different route duration than the sailboat."""
        sailboat_request = demo_request()
        motorboat_request = replace(sailboat_request, boat_model='motorboat',
                                    boat=boat_for_model('motorboat'))
        sailboat = json.loads(run_plan(sailboat_request))
        motorboat = json.loads(run_plan(motorboat_request))
        sail_routes = {r['candidate']['name']: r for r in
                       sailboat['comparison']['departures'][0]['routes']['candidates']}
        motor_routes = {r['candidate']['name']: r for r in
                        motorboat['comparison']['departures'][0]['routes']['candidates']}
        self.assertEqual(sailboat['manifest']['boat']['boat_model'], 'sailboat')
        self.assertEqual(motorboat['manifest']['boat']['boat_model'], 'motorboat')
        self.assertNotEqual(sailboat['manifest']['boat_sha256'],
                            motorboat['manifest']['boat_sha256'])
        self.assertNotEqual(sail_routes['direct']['travel_seconds'],
                            motor_routes['direct']['travel_seconds'])
        # Estimated constant motorboat speed 12 knots (~6.17 m/s) over the 100 m direct leg.
        self.assertAlmostEqual(motor_routes['direct']['travel_seconds'], 100/(12*KNOT), delta=.01)
        self.assertEqual(type(boat_for_model('motorboat')).__name__, 'ConstantBoat')
        with self.assertRaises(ValueError):
            replace(sailboat_request, boat_model='submarine')

    def test_motorboat_profile_is_marked_as_estimated(self):
        """The estimated motorboat profile is explicitly flagged in the manifest."""
        manifest = json.loads(run_plan(replace(demo_request(), boat_model='motorboat',
                                               boat=boat_for_model('motorboat'))))['manifest']
        self.assertTrue(manifest['boat_data_estimated'])
        self.assertTrue(manifest['boat']['estimated'])
        self.assertIn('uppskattad', manifest['boat']['estimation_note'].lower())
        self.assertTrue(manifest['boat']['assumptions'])
        self.assertEqual(manifest['schema_version'], 2)

    def test_boat_model_must_match_boat_profile(self):
        """A boat_model that contradicts the boat profile is rejected, not silently relabelled."""
        with self.assertRaises(ValueError):
            replace(demo_request(), boat_model='motorboat')
        # A profile-only request derives its label from the profile.
        derived = replace(demo_request(), boat=boat_for_model('motorboat'))
        self.assertEqual(derived.boat_model, 'motorboat')

    def test_resolve_boat_model(self):
        """resolve_boat_model derives or validates the model name against the profile."""
        self.assertEqual(resolve_boat_model('motorboat', boat_for_model('motorboat')), 'motorboat')
        self.assertEqual(resolve_boat_model(None, PolarBoat()), 'sailboat')
        self.assertEqual(resolve_boat_model(None, boat_for_model('motorboat')), 'motorboat')
        with self.assertRaises(ValueError):
            resolve_boat_model('motorboat', PolarBoat())
        with self.assertRaises(ValueError):
            resolve_boat_model('sailboat', boat_for_model('motorboat'))
        with self.assertRaises(ValueError):
            resolve_boat_model('submarine', PolarBoat())

    def test_algorithm_version_is_v4(self):
        """The algorithm version reflects the deduplicated boat_model identity."""
        self.assertEqual(ALGORITHM_VERSION, 'explicit-candidates-midpoint-grid-weather-v4')

    def test_halved_step_comparison_has_documented_tolerances(self):
        reports = [json.loads(run_plan(demo_request(step_seconds=step))) for step in (10, 5)]
        rows = [r['comparison']['departures'][0]['routes'] for r in reports]
        self.assertEqual(rows[0]['fastest_candidate'], rows[1]['fastest_candidate'])
        self.assertEqual(rows[0]['comfortable_candidate'], rows[1]['comfortable_candidate'])
        north = [next(r for r in row['candidates'] if r['candidate']['name']=='north') for row in rows]
        self.assertLess(abs(north[0]['travel_seconds']-north[1]['travel_seconds']), .01)
        self.assertLess(abs(north[0]['comfort_exposure']-north[1]['comfort_exposure']), .5)
