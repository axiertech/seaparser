"""Known native interpolation and whole-segment support without a new adapter."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from fractions import Fraction
from math import hypot
from pathlib import Path
import unittest

from infrastructure.copernicus_adapter import CopernicusMarineAdapter,PROJECTION_TOLERANCE_M
from infrastructure.native_marine import disk_geographic_bounds,NativeMarineProduct,NativeMarineDataset,ORIGIN,MIN_CURVATURE_RADIUS_M
from infrastructure.land import FORWARD
from prototype.forecast_data import DataUnavailable
from prototype.model import Vector
from prototype.weather import WeatherPolicy
from scripts.freeze_copernicus_reference import freeze_native_with_audit

ROOT=Path(__file__).resolve().parents[1]


class NativeMarineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload,cls.report=freeze_native_with_audit(ROOT/'fixtures/vinga-expanded-20261017',radius_m=2000)

    def setUp(self):
        self.dataset=CopernicusMarineAdapter().normalize(self.payload,native_radius_m=2000)
        self.time=self.dataset.products[0].times[0]

    def constant(self):
        products=[]
        for p in self.dataset.products:
            node=(.3,-.4) if p.metadata.product=='current' else (1.,6.,0.,1.)
            values=tuple(tuple(tuple(node for _ in p.longitude) for _ in p.latitude) for _ in p.times)
            products.append(replace(p,values=values))
        return replace(self.dataset,products=tuple(products))

    def test_wgs84_curvature_lower_bound_and_guarded_disk(self):
        from pyproj import Geod
        a=Fraction(6378137);f=1/Fraction('298.257223563');e2=f*(2-f)
        self.assertGreater(a*(1-e2),MIN_CURVATURE_RADIUS_M)
        geod=Geod(ellps='WGS84')
        for radius in (1,900,2000,5000):
            west,south,east,north=disk_geographic_bounds(radius)
            for bearing in range(360):
                lon,lat,_=geod.fwd(ORIGIN[1],ORIGIN[0],bearing,radius)
                self.assertTrue(west<lon<east and south<lat<north)
                x,y=FORWARD.transform(lon,lat)
                self.assertAlmostEqual(hypot(x,y),radius,places=7)
        for radius in (0,-1,True,float('nan'),5001):
            with self.assertRaises(ValueError):disk_geographic_bounds(radius)

    def test_constant_native_values_at_changing_positions_and_time(self):
        dataset=self.constant()
        for position in (Vector(0,0),Vector(-1999,0),Vector(0,1999),Vector(1200,1200)):
            for time in (self.time,self.time+timedelta(minutes=30),self.time+timedelta(hours=10,minutes=59)):
                weather=dataset.evaluate(position,time)
                self.assertEqual(weather.current,Vector(.3,-.4))
                self.assertEqual(weather.waves.height_m,1)
                self.assertEqual(weather.waves.period_seconds,6)
                self.assertEqual(weather.waves.from_degrees,0)
        dataset.validate_segment(Vector(-1999,0),self.time,Vector(1999,0),self.time+timedelta(hours=10))
        self.assertEqual(dataset.certify_waves_segment(Vector(-1999,0),self.time,Vector(1999,0),
            self.time+timedelta(hours=10),WeatherPolicy(18,1)).status,'verified')

    def test_native_linear_field_matches_independent_geographic_reference(self):
        dataset=self.constant();products=[]
        for p in dataset.products:
            if p.metadata.product=='current':
                values=tuple(tuple(tuple((2*(lon-ORIGIN[1])+3*(lat-ORIGIN[0])+k/10,-.4)
                    for lon in p.longitude) for lat in p.latitude) for k in range(len(p.times)))
                p=replace(p,values=values)
            products.append(p)
        dataset=replace(dataset,products=tuple(products))
        lon,lat=11.615,57.64;x,y=FORWARD.transform(lon,lat)
        value=dataset.evaluate(Vector(x,y),self.time+timedelta(minutes=30)).current
        self.assertAlmostEqual(value.east,2*(lon-ORIGIN[1])+3*(lat-ORIGIN[0])+.05,places=12)
        self.assertEqual(value.north,-.4)

    def test_gap_in_global_support_cannot_be_hopped_over_by_a_segment(self):
        dataset=self.constant();p=dataset.products[0]
        values=[[list(row) for row in plane] for plane in p.values];values[0][0][0]=None
        changed=replace(p,values=values);dataset=replace(dataset,products=(changed,dataset.products[1]))
        # The local point has all eight interpolation nodes; it still cannot prove the segment envelope.
        self.assertIsNotNone(dataset.evaluate(Vector(0,0),self.time).current)
        with self.assertRaises(DataUnavailable):dataset.validate_segment(Vector(-10,0),self.time,Vector(10,0),self.time+timedelta(seconds=1))
        dataset.validate_segment(Vector(-10,0),self.time+timedelta(hours=2),Vector(10,0),self.time+timedelta(hours=3))

    def test_hard_hs_bound_is_not_an_observation_and_cannot_be_outweighed(self):
        dataset=self.constant();waves=dataset.products[1]
        values=[[list(row) for row in plane] for plane in waves.values]
        values[0][-1][-1]=(30.,6.,0.,1.)
        changed=replace(waves,values=values);dataset=replace(dataset,products=(dataset.products[0],changed))
        check=dataset.certify_waves_segment(Vector(0,0),self.time,Vector(10,0),self.time+timedelta(seconds=10),WeatherPolicy(18,3))
        self.assertEqual(check.status,'unverified');self.assertIsNone(check.witness)
        check=self.constant().certify_waves_segment(Vector(0,0),self.time,Vector(10,0),self.time+timedelta(seconds=10),WeatherPolicy(18,.5))
        self.assertEqual(check.status,'exceeded');self.assertIsNotNone(check.witness)

    def test_own_axes_masks_time_and_source_gates_are_retained(self):
        current,waves=self.dataset.products
        self.assertNotEqual(current.longitude,waves.longitude)
        for p in self.dataset.products:
            self.assertIsNone(p.metadata.issued_at)
            self.assertIn('model_issue_time_unverified',p.metadata.planning_blockers)
            self.assertIn('marine_time_support_unverified',p.metadata.planning_blockers)
            self.assertEqual(p.metadata.assumed_fields,())
            with self.assertRaises(DataUnavailable):p.interpolate(Vector(0,0),p.times[-1])
            with self.assertRaises(DataUnavailable):p.interpolate(Vector(2001,0),self.time)
        payload=deepcopy(self.payload);payload['products']['static']['data']['mask'][0][0]=0
        changed=CopernicusMarineAdapter().normalize(payload,native_radius_m=2000)
        self.assertIsNotNone(changed.products[0].values[0][0][0])
        self.assertIsNone(changed.products[1].values[0][0][0])
        with self.assertRaises(DataUnavailable):changed.validate_segment(Vector(0,0),self.time,Vector(10,0),self.time+timedelta(seconds=1))
        with self.assertRaises(DataUnavailable):CopernicusMarineAdapter().normalize(self.payload,native_radius_m=5000)
        with self.assertRaises(ValueError):CopernicusMarineAdapter().normalize(self.payload)
        self.assertEqual(PROJECTION_TOLERANCE_M,1)


class NativeCompositionTests(unittest.TestCase):
    def test_named_assumptions_keep_unknown_sources_and_whole_route_controls(self):
        from application.development_weather import load_development_weather
        from application.planning import canonical
        from scripts.native_marine_review import build
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as temp:
            report,result=build(Path(temp))
            self.assertEqual(canonical(report)+'\n',(ROOT/'artifacts/native-marine-review/report.json').read_text())
            self.assertEqual(result['geometry_search']['status'],'endpoint_blocked')
            self.assertIsNone(result['planning'])
            self.assertEqual(result['alternatives'],[])
            page=(Path(temp)/'index.html').read_text()
            self.assertIn('17 oktober 2026',page)
            self.assertIn('Ingen färd beräknad',page)
            self.assertNotIn('class="card"',page)
            self.assertEqual(report['land']['closed_hulls'],24)
            self.assertEqual(report['specified_route']['result_qualification'],'conditional_on_assumptions')
            plan=json.loads((Path(temp)/'specified-route.json').read_text())
            rows=plan['comparison']['departures'][0]['routes']['candidates']
            self.assertEqual(rows[0]['status'],'arrived')
            self.assertEqual(rows[0]['weather_segment_status'],'verified')
            self.assertEqual(rows[0]['arrival_weather_status'],'passed_at_arrival')
            self.assertGreater(rows[0]['travel_seconds'],0)
            self.assertLess(rows[0]['travel_seconds'],1800)
        dataset,config,evidence=load_development_weather(ROOT/'settings/development-weather-native-assumptions.json')
        self.assertEqual(dataset.support_radius_m,900)
        self.assertIsNone(evidence['actual_source_issued_at']['waves'])
        self.assertTrue(all(m['issued_at'] is None for m in evidence['verified']['marine_metadata']))
        for p in dataset.product_metadata:self.assertIn('issued_at',p.assumed_fields)
        failed=dataset.certify_weather_segment(Vector(500,0),dataset.wind.times[0],Vector(500,10),
            dataset.wind.times[0]+timedelta(seconds=10),WeatherPolicy(18,.01))
        self.assertEqual(failed.status,'exceeded')
