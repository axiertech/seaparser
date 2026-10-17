"""Real-source development integration and unchanged hard rejection controls."""
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from application.development_weather import load_development_weather,ROOT
from application.geographic_plan import scene,calculate_geographic
from application.planning import canonical
from infrastructure.land import to_geo
from prototype.model import Vector
from prototype.forecast_data import DataUnavailable
from prototype.weather import WeatherPolicy
from presentation.real_route_html import render


class DevelopmentWeatherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset,cls.config,cls.evidence=load_development_weather()
        cls.time=cls.dataset.wind.times[0]

    def test_real_values_and_source_metadata_are_distinct_from_assumptions(self):
        weather=self.dataset.evaluate(Vector(0,0),self.time)
        self.assertAlmostEqual(weather.wind.east,-4.421896792138777,places=10)
        self.assertAlmostEqual(weather.current.east,-.23163306297998,places=10)
        self.assertAlmostEqual(weather.waves.height_m,1.0924112263433168,places=10)
        self.assertTrue(weather.wind_metadata.assumed_fields)
        self.assertIsNone(self.evidence['actual_source_issued_at']['wind'])
        self.assertTrue(all(m['issued_at'] is None for m in self.evidence['verified']['marine_metadata']))
        self.assertEqual(dict(self.dataset.wind.source_hashes),self.evidence['verified']['wind_source_hashes'])

    def test_missing_assumption_cannot_be_silently_accepted(self):
        for change in ('mode','assumption'):
            config=json.loads((ROOT/'settings/development-weather-assumptions.json').read_text())
            if change=='mode':config['mode']='verified'
            else:del config['assumptions']['model_issue_time_unverified']
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'config.json';path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):load_development_weather(path)

    def test_unknown_new_wind_blocker_is_not_covered_by_generic_assumptions(self):
        from unittest.mock import patch,PropertyMock
        from infrastructure.native_wind import NativeWindSample
        with patch.object(NativeWindSample,'planning_blockers',new_callable=PropertyMock,
                          return_value=('new_unreviewed_source_problem',)):
            with self.assertRaisesRegex(ValueError,'Nytt vindproblem'):
                load_development_weather()

    def test_coverage_and_time_are_never_assumed_away(self):
        for start,time in ((Vector(-680,-400),self.time),(Vector(300,-400),self.dataset.wind.times[-1])):
            with self.assertRaises(DataUnavailable):
                self.dataset.validate_segment(start,time,start,time+timedelta(seconds=30))
        self.assertIsNone(self.dataset.evaluate(Vector(0,0),self.dataset.wind.times[-1]).wind)

    def test_missing_marine_node_and_invalid_values_remain_rejected(self):
        wave=next(p for p in self.dataset.marine.products if p.metadata.product=='waves')
        values=[[list(row) for row in plane] for plane in wave.values]
        values[0][0][0]=None
        changed=replace(wave,values=values)
        marine=replace(self.dataset.marine,products=tuple(changed if p is wave else p for p in self.dataset.marine.products))
        dataset=replace(self.dataset,marine=marine)
        with self.assertRaises(DataUnavailable):
            dataset.validate_segment(Vector(300,-400),self.time,Vector(300,-390),self.time+timedelta(seconds=10))
        values[0][0][0]=(float('nan'),1,0,1)
        with self.assertRaises(ValueError):replace(wave,values=values)

    def test_hard_weather_limits_cannot_be_relaxed_by_assumptions(self):
        a,b=Vector(300,-400),Vector(300,-390)
        for policy in (WeatherPolicy(10,3),WeatherPolicy(18,.1)):
            check=self.dataset.certify_weather_segment(a,self.time,b,self.time+timedelta(seconds=10),policy)
            self.assertEqual(check.status,'exceeded')
        passed=self.dataset.certify_weather_segment(a,self.time,b,self.time+timedelta(seconds=10),WeatherPolicy(18,3))
        self.assertEqual(passed.status,'verified')

    def test_real_default_routing_and_graphic_report_are_reproducible(self):
        s=scene();a,b=s['start'],s['target']
        payload=dict(start={'longitude':a[0],'latitude':a[1]},target={'longitude':b[0],'latitude':b[1]},
                     margin_m=10,departure_offsets_seconds=[0,600])
        first=calculate_geographic(payload);second=calculate_geographic(payload)
        self.assertEqual(canonical(first),canonical(second))
        self.assertFalse(first['synthetic'])
        self.assertEqual(len(first['alternatives']),4)
        self.assertTrue(all(r['status']=='arrived' for r in first['alternatives']))
        self.assertTrue(all(r['qualification']=='conditional_on_assumptions' for r in first['alternatives']))
        self.assertEqual(first['planning']['manifest']['boat']['model'],'ConstantBoat')
        self.assertIn('assumed_fields',first['planning']['manifest']['forecast_products'][0])
        self.assertEqual((ROOT/'artifacts/real-route-review/result.json').read_text(),canonical(first)+'\n')
        page=render(first)
        self.assertEqual((ROOT/'artifacts/real-route-review/index.html').read_text(),page)
        self.assertEqual(page.count('class="card"'),4)
        self.assertIn('<polyline',page)
        self.assertIn('Beräknad med uttryckliga antaganden',page)
        self.assertNotIn('https://tile',page)
        changed=calculate_geographic(payload|{'max_wave_height_m':.1})
        self.assertNotEqual(first['input_sha256'],changed['input_sha256'])
        self.assertTrue(all(r['status']=='weather_limit' for r in changed['alternatives']))
