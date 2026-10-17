"""Bounded development search and known duration/exposure selection cases."""
import json
from pathlib import Path
import unittest
from pydantic import ValidationError
from api.models import PlanInput
from application.geographic_budget import validate_budget
from application.geographic_plan import compare_alternatives

ROOT = Path(__file__).resolve().parents[1]


class GeographicBudgetTests(unittest.TestCase):
    payload = {'profile': 'vinga', 'start': {'latitude': 57.633, 'longitude': 11.605},
               'target': {'latitude': 57.634, 'longitude': 11.605}}

    def test_api_accepts_only_measured_bounded_choices(self):
        for candidates, offsets in ((4, [0,600,3600,10800]), (8, [0,600]), (2, [10800])):
            p = PlanInput(**self.payload, candidate_limit=candidates, departure_offsets_seconds=offsets)
            self.assertLessEqual(p.candidate_limit * len(p.departure_offsets_seconds), 16)
        for change in ({'candidate_limit': 8, 'departure_offsets_seconds': [0,600,3600]},
                       {'candidate_limit': 16}, {'candidate_limit': 3}, {'candidate_limit': 2.0},
                       {'departure_offsets_seconds': [0,0]}, {'departure_offsets_seconds': [1200]},
                       {'departure_offsets_seconds': [-600]}, {'departure_offsets_seconds': [14400]},
                       {'departure_offsets_seconds': [False]},
                       {'profile': 'synthetic', 'departure_offsets_seconds': [3600]},
                       {'profile': 'synthetic', 'candidate_limit': 4}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                PlanInput(**(self.payload | change))
        with self.assertRaises(ValueError): validate_budget('vinga',8,[0,600,3600,10800])
        self.assertEqual(validate_budget('vinga',8,[0,600,3600,10800],offline=True),8)

    def test_global_selection_has_known_tradeoff_and_hard_eligibility(self):
        def route(name, seconds, exposure, **changes):
            return dict(id=name, status='arrived', travel_seconds=seconds, comfort_exposure=exposure,
                        weather_segment_status='verified', arrival_weather_status='passed_at_arrival') | changes
        rows=[route('early-fast',100,90), route('later-comfortable',120,20),
              route('too-slow',401,0), route('unsafe',50,0,status='weather_limit'),
              route('arrival-unknown',60,0,arrival_weather_status='not_checked')]
        result=compare_alternatives(rows,300)
        self.assertEqual(result['fastest_id'],'early-fast')
        self.assertEqual(result['comfortable_id'],'later-comfortable')
        self.assertFalse(result['same_winner'])
        self.assertTrue(compare_alternatives(rows,0)['same_winner'])
        self.assertIsNone(compare_alternatives([],300)['same_winner'])
        tied=[route('first',100,20),route('second',100,20)]
        self.assertEqual(compare_alternatives(tied,300)['comfortable_id'],'first')

    def test_real_expanded_artifact_keeps_source_qualification_and_controls(self):
        r=json.loads((ROOT/'artifacts/real-route-budget/result.json').read_text())
        self.assertEqual(len(r['alternatives']),16)
        self.assertEqual(r['search_budget']['evaluation_limit'],16)
        self.assertTrue(r['geometry_search']['truncated'])
        self.assertEqual(r['geometry_search']['policy']['max_expansions'],1000)
        self.assertEqual(r['planning']['manifest']['parameters']['max_seconds'],1800)
        self.assertEqual(r['weather_provenance']['source_qualification'],'unverified')
        self.assertEqual(r['result_qualification'],'conditional_on_assumptions')
        self.assertTrue(r['alternative_comparison']['same_winner'])
        for row in r['alternatives']:
            self.assertEqual(row['status'],'arrived')
            self.assertEqual(row['weather_segment_status'],'verified')
            self.assertEqual(row['arrival_weather_status'],'passed_at_arrival')
        self.assertTrue(all(v is None for v in r['weather_provenance']['actual_source_issued_at'].values()))
        for p in r['planning']['manifest']['forecast_products']:
            self.assertIn('issued_at',p['assumed_fields'])


    def test_entire_duration_budget_must_fit_before_exclusive_end(self):
        from unittest.mock import patch
        from application.development_weather import load_development_weather
        from application.geographic_plan import calculate_geographic
        dataset,config,evidence=load_development_weather()
        config=config | {'departure':'2026-10-13T15:30:00Z'}
        with patch('application.geographic_plan.load_development_weather',return_value=(dataset,config,evidence)):
            with self.assertRaisesRegex(ValueError,'hela ruttbudgeten'):
                calculate_geographic(self.payload | {'departure_offsets_seconds':[0]})
