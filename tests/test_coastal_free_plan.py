"""Free endpoints use the existing known-voyage engine and hard rejections."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

from application.coastal_plan import plan_coastal
from infrastructure.land import INVERSE
from prototype.weather import WeatherPolicy
from tests import test_coastal_plan


class CoastalFreePlanTests(unittest.TestCase):
    def setup_plan(self,**options):
        env=test_coastal_plan.CoastalCompositionTests().environment(**options)
        config={'max_age_seconds':86400,'planning_time':env.start.isoformat()}
        def position(x):
            lon,lat=INVERSE.transform(x,0)
            return {'longitude':lon,'latitude':lat}
        payload={'start':position(0),'target':position(2000),'departure':env.start.isoformat(),'candidate_limit':2}
        return env,config,payload

    def calculate(self,env,config,payload):
        with patch('application.coastal_plan.load_coastal_weather',return_value=(env,config,{},{})):
            return plan_coastal('unused-test-source',payload)

    def test_free_points_find_actual_voyages_and_match_known_current_time(self):
        env,config,payload=self.setup_plan()
        result=self.calculate(env,config,payload)
        self.assertEqual(result,json.loads(json.dumps(result,allow_nan=False)))
        rows=result['comparison']['candidates']
        self.assertTrue(rows)
        fastest=next(r for r in rows if r['candidate']['name']==result['comparison']['fastest_candidate'])
        self.assertAlmostEqual(fastest['travel_seconds'],2000/(5*1852/3600+1),delta=.01)
        self.assertTrue(all(r['status']=='arrived' for r in rows))
        self.assertTrue(all(r['weather_segment_status']=='not_available' for r in rows))
        self.assertFalse(result['weather_limits_verified'])
        self.assertEqual(result,self.calculate(env,config,payload))
        changed=deepcopy(payload);changed['target']['longitude']+=.0001
        self.assertNotEqual(result['input_sha256'],self.calculate(env,config,changed)['input_sha256'])

    def test_weather_rejection_and_disabled_data_do_not_become_feasible_alternatives(self):
        for options in ({'gap':True},{'policy':WeatherPolicy(30,.1)}):
            env,config,payload=self.setup_plan(**options)
            result=self.calculate(env,config,payload)
            self.assertIsNone(result['comparison']['fastest_candidate'])
            self.assertTrue(all(r['status'] in ('weather_limit','data_unavailable') for r in result['comparison']['candidates']))

    def test_reserve_evidence_is_json_native_and_keeps_source_time_and_connections(self):
        env,config,payload=self.setup_plan(wall=True)
        result=self.calculate(env,config,payload)
        records=[r for segment in result['estimated_segments'] for sample in segment['samples'] for r in sample['estimates']]
        self.assertTrue(records)
        self.assertTrue(all(isinstance(r['source_time'],str) and isinstance(r['connection_waypoints'],list) for r in records))
        self.assertEqual(result,json.loads(json.dumps(result,allow_nan=False)))

    def test_blocked_endpoint_reports_search_failure_without_simulating(self):
        env,config,payload=self.setup_plan()
        env.margin_m=10
        lon,lat=INVERSE.transform(9995,0);payload['start']={'longitude':lon,'latitude':lat}
        with patch('application.coastal_plan.compare_routes',side_effect=AssertionError('No candidate means no voyage')):
            result=self.calculate(env,config,payload)
        self.assertEqual(result['geometry_search']['status'],'endpoint_blocked')
        self.assertEqual(result['comparison']['status'],'not_simulated')
        self.assertEqual(result['estimated_segments'],[])

    def test_invalid_inputs_cannot_replace_settings_or_leave_common_time_support(self):
        env,config,payload=self.setup_plan()
        for change in ({'candidate_limit':True},{'candidate_limit':3},{'max_expansions':1},
                       {'boat_profile':'invented'},{'max_wave_height_m':float('nan')},
                       {'start':{'longitude':True,'latitude':57.633}},
                       {'departure':(env.end+timedelta(seconds=1)).isoformat()},
                       {'departure':env.start.replace(tzinfo=None).isoformat()},{'departure':None}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.calculate(env,config,payload|change)
