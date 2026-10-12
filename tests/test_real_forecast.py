import copy
from datetime import timedelta
import json
from math import sin,cos,radians
from pathlib import Path
import unittest
from application.real_forecast_reference import inspect_reference,plan_reference
from infrastructure.point_forecast import SnowPointAdapter,MetOceanPointAdapter,timestamp
from prototype.forecast_data import DataUnavailable

ROOT=Path(__file__).resolve().parents[1]


class RealForecastTests(unittest.TestCase):
    def setUp(self):
        self.reference=json.loads((ROOT/'fixtures/vinga-point-forecast-reference.json').read_text())

    def test_real_reference_is_frozen_and_partial_not_zero(self):
        wind,current,waves=inspect_reference(self.reference)
        original=wind.values[0];identity=wind.source_sha256
        self.reference['sources'][0]['payload']['timeSeries'][0]['data']['wind_speed']=100
        self.assertEqual(wind.values[0],original)
        self.assertEqual(wind.source_sha256,identity)
        self.assertEqual(wind.position,(11.609723,57.6395))
        self.assertEqual(current.position,(11.5955,57.626))
        self.assertGreater(waves.values[0][0],0)
        self.assertIsNone(waves.values[0][1])
        self.assertIsNone(current.issued_at)
        self.assertIsNotNone(current.updated_at)
        with self.assertRaises(DataUnavailable):
            waves.interpolate(waves.position,waves.times[0])

    def test_direction_wrap_and_component_interpolation_independent_reference(self):
        source=self.reference['sources'][0];p=source['payload']
        p['timeSeries']=copy.deepcopy(p['timeSeries'][:2])
        for s,bearing in zip(p['timeSeries'],(359,1)):
            s['data']['wind_speed']=4;s['data']['wind_from_direction']=bearing
        wind=SnowPointAdapter().normalize(p,retrieved_at=timestamp(source['retrieved_at']),source_url=source['url'])[0]
        midpoint=wind.times[0]+(wind.times[1]-wind.times[0])/2
        east,north=wind.interpolate(wind.position,midpoint)
        self.assertAlmostEqual(east,0,places=12)
        self.assertAlmostEqual(north,-4*cos(radians(1)),places=12)
        sea=self.reference['sources'][1];p=sea['payload']
        p['properties']['timeseries'][0]['data']['instant']['details']['sea_water_speed']=2
        p['properties']['timeseries'][0]['data']['instant']['details']['sea_water_to_direction']=90
        current=MetOceanPointAdapter().normalize(p,retrieved_at=timestamp(sea['retrieved_at']),source_url=sea['url'])[0]
        self.assertAlmostEqual(current.values[0][0],2)
        self.assertAlmostEqual(current.values[0][1],0,places=12)

    def test_freshness_uses_explicit_planning_time_and_missing_issuance_rejected(self):
        wind,current,_=inspect_reference(self.reference)
        wind.check_age(wind.issued_at+timedelta(seconds=600),600)
        with self.assertRaises(DataUnavailable):wind.check_age(wind.issued_at+timedelta(seconds=601),600)
        with self.assertRaises(DataUnavailable):wind.check_age(wind.issued_at-timedelta(seconds=1),600)
        with self.assertRaises(DataUnavailable):current.check_age(current.updated_at,600)
        source=self.reference['sources'][0];del source['payload']['createdTime']
        with self.assertRaises(ValueError):inspect_reference(self.reference)

    def test_no_spatial_temporal_or_gap_extrapolation(self):
        source=self.reference['sources'][0];wind=inspect_reference(self.reference)[0]
        with self.assertRaises(DataUnavailable):wind.interpolate((11.605,57.633),wind.times[0])
        for time in (wind.times[0]-timedelta(seconds=1),wind.times[-1]):
            with self.assertRaises(DataUnavailable):wind.interpolate(wind.position,time)
        source['payload']['timeSeries'][1]['data']['wind_speed']=None
        wind=inspect_reference(self.reference)[0]
        with self.assertRaises(DataUnavailable):wind.interpolate(wind.position,wind.times[0])
        marine=self.reference['sources'][1];del marine['payload']['properties']['meta']['units']['sea_water_speed']
        with self.assertRaises(ValueError):inspect_reference(self.reference)

    def test_regional_planning_is_explicitly_rejected_and_reproducible(self):
        a=plan_reference(self.reference);b=plan_reference(copy.deepcopy(self.reference))
        self.assertEqual(a,b)
        self.assertEqual(a['status'],'data_unavailable')
        self.assertIsNone(a['fastest_candidate']);self.assertIsNone(a['comfortable_candidate'])
        self.assertIn('regional',a['reason'].lower())
        self.assertEqual(a['depth_status'],'unknown')
