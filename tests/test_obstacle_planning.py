"""Frozen forecast/polar/weather integration of automatically generated candidates."""
from dataclasses import replace
import json
import unittest
from application.obstacle_planning import run_obstacle_plan
from prototype.auto_routing import SearchPolicy
from prototype.model import Vector
from prototype.polygon import Polygon
from scripts.plan_synthetic import demo_request

class ObstaclePlanningTests(unittest.TestCase):
    def request(self,scenario='baseline'):
        obstacle=Polygon('fixture',(Vector(40,-5),Vector(60,-5),Vector(60,5),Vector(40,5)),2)
        return replace(demo_request(scenario=scenario),obstacles=(obstacle,))

    def test_frozen_dataset_and_polar_full_route_results(self):
        request=self.request()
        raw=run_obstacle_plan(request,SearchPolicy(max_candidates=4,clearance_m=5))
        self.assertEqual(raw,run_obstacle_plan(request,SearchPolicy(max_candidates=4,clearance_m=5)))
        result=json.loads(raw); plan=result['planning']
        self.assertEqual(plan['manifest']['dataset_version'],request.dataset.version)
        self.assertEqual(plan['manifest']['boat']['model'],'PolarBoat')
        self.assertEqual(len(plan['comparison']['departures']),2)
        arrived=[r for d in plan['comparison']['departures'] for r in d['routes']['candidates'] if r['status']=='arrived']
        self.assertTrue(arrived)
        for route in arrived:
            self.assertEqual(route['weather_segment_status'],'verified')
            self.assertEqual(route['arrival_weather_status'],'passed_at_arrival')
            self.assertIsNotNone(route['comfort_exposure'])
        self.assertIn('Ingen global optimalitet',result['geometry_search']['scope'])

    def test_no_weather_feasible_candidate_and_gaps_preserved(self):
        for scenario,status in (('weather-limit','weather_limit'),('missing-waves','data_unavailable')):
            result=json.loads(run_obstacle_plan(self.request(scenario),SearchPolicy(max_candidates=2)))
            self.assertIsNone(result['planning']['comparison']['shortest_travel'])
            self.assertTrue(all(r['status']==status for d in result['planning']['comparison']['departures']
                                for r in d['routes']['candidates']))

    def test_no_generated_path_is_explicit_and_changes_identity(self):
        request=self.request()
        result=json.loads(run_obstacle_plan(request,SearchPolicy(max_expansions=1)))
        self.assertIsNone(result['planning'])
        self.assertTrue(result['geometry_search']['truncated'])
        self.assertIn('inte bevis',result['limitations'])
        other=json.loads(run_obstacle_plan(request,SearchPolicy(max_candidates=2)))
        self.assertNotEqual(result['input_sha256'],other['input_sha256'])
