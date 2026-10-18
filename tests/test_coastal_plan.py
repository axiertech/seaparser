"""Known voyages and hard rejection cases for the explicit estimate composition."""
from dataclasses import replace
from pathlib import Path
import json
import unittest

from pyproj import Geod
from shapely import box,to_wkb
from infrastructure.coastal_water import CoastalWater
from infrastructure.coastal_forecast import CoastalForecast,CoastalObstacle
from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from infrastructure.marine_reserve import NativeWindWithReserve,ReservePolicy,configured_reserve_policies
from infrastructure.motion_frame import RegionalAeqdMotionFrame,AeqdMotionFrame
from infrastructure.land import FORWARD,INVERSE
from prototype.forecast_metadata import ProductMetadata
from prototype.forecast import FixedClock,ForecastPolicy
from prototype.model import Vector,ConstantBoat
from prototype.routes import RouteCandidate,compare_routes
from prototype.presentation import export_route_comparison
from prototype.weather import WeatherPolicy
from scripts.regional_forecast import load_native_wind

ROOT=Path(__file__).resolve().parents[1]


class CoastalCompositionTests(unittest.TestCase):
    def environment(self,*,policy=None,wall=False,gap=False):
        payload=json.loads((ROOT/'fixtures/vinga-copernicus/reference.json').read_text())
        for product,fields in (('current',{'uo':1.,'vo':0.}),('waves',{'VHM0':.5,'VTM02':5.,'VMDR':0.})):
            for name,value in fields.items():
                payload['products'][product]['data'][name]=[[[None if gap and product=='current' else value for _ in row] for row in plane] for plane in payload['products'][product]['data'][name]]
        geometry=box(-10000,-10000,10000,10000)
        if wall:geometry=geometry.difference(box(45,-500,55,500))
        water=CoastalWater(to_wkb(geometry),'unit-test-water')
        policies=configured_reserve_policies(json.loads((ROOT/'settings/vinga-uddevalla-reserve.json').read_text()))
        current,waves=CopernicusMarineAdapter().normalize_coastal(payload,water,policies,bounds=(11.5,57.5,11.7,57.7))
        sample=load_native_wind(ROOT/'fixtures');wind=NativeWindWithReserve(sample,water,policies['wind'])
        issued=sample.times[0]
        wm=ProductMetadata('wind','unit-test-native','1','Frozen native test wind',issued,sample.times[0],sample.times[-1],
            current.metadata.coverage,('m/s','m/s'),'ground-to-true-east-north',assumed_fields=('issued_at',))
        metadata=(wm,*(replace(p.metadata,issued_at=issued,planning_blockers=(),assumed_fields=('issued_at',)) for p in (current,waves)))
        return CoastalForecast(wind,current,waves,metadata,water,policy or WeatherPolicy(30,2),margin_m=0)

    def voyage(self,environment):
        start=environment.start
        return compare_routes(environment,start,Vector(100,0),(RouteCandidate('known'),),position=Vector(0,0),
            boat=ConstantBoat(5),obstacles=(CoastalObstacle(environment.water,0),),weather_policy=environment.policy,
            forecast_policy=ForecastPolicy(86400),clock=FixedClock(start),step_seconds=10,max_seconds=1000)

    def test_known_current_voyage_uses_existing_engine_without_claiming_verified_weather(self):
        env=self.environment();result=self.voyage(env);route=result.fastest
        self.assertIsNotNone(route);self.assertEqual(route.status,'arrived')
        expected=100/(5*1852/3600+1)
        self.assertAlmostEqual(route.travel_seconds,expected,delta=.001)
        self.assertAlmostEqual(route.comfort_exposure,.5*expected,delta=.005)
        self.assertEqual(route.weather_segment_status,'not_available')
        self.assertTrue(all(env.water.clear(s.start.position,s.end_position) for leg in route.legs for s in leg.steps))

    def test_repeating_a_voyage_with_cached_queries_preserves_the_entire_report(self):
        env=self.environment()
        first=export_route_comparison(self.voyage(env))
        self.assertEqual(first,export_route_comparison(self.voyage(env)))

    def test_land_weather_and_missing_current_remain_hard_rejections(self):
        for env,status in ((self.environment(wall=True),'blocked'),
                           (self.environment(policy=WeatherPolicy(30,.1)),'weather_limit'),
                           (self.environment(gap=True),'data_unavailable')):
            with self.subTest(status=status):
                result=self.voyage(env);self.assertIsNone(result.fastest)
                self.assertEqual(result.candidates[0].status,status)

    def test_coastal_adapter_retains_unknown_source_issuance_and_copies_values(self):
        env=self.environment()
        self.assertIsNone(env.current.metadata.issued_at)
        self.assertIn('current_native_wet_mask_unverified',env.current.metadata.planning_blockers)
        self.assertFalse(env.current.values.flags.writeable)

    def test_regional_motion_matches_independent_ellipsoidal_displacements(self):
        frame=RegionalAeqdMotionFrame();geod=Geod(ellps='WGS84')
        for p in (Vector(0,0),Vector(30000,30000),Vector(0,80000),Vector(30000,110000)):
            lon,lat=INVERSE.transform(p.east,p.north)
            for v in (Vector(1,0),Vector(0,1),Vector(3,-4)):
                a=geod.fwd(lon,lat,v.course,v.speed*.5);b=geod.fwd(lon,lat,v.course+180,v.speed*.5)
                ax,ay=FORWARD.transform(*a[:2]);bx,by=FORWARD.transform(*b[:2]);rate=frame.position_rate(p,v)
                self.assertAlmostEqual(rate.east,ax-bx,delta=2e-6);self.assertAlmostEqual(rate.north,ay-by,delta=2e-6)
        with self.assertRaises(ValueError):AeqdMotionFrame(120000)
        with self.assertRaises(ValueError):frame.position_rate(Vector(120001,0),Vector(1,0))

    def test_regional_native_enclosure_is_checked_against_dense_reference_positions(self):
        env=self.environment()
        for p in (Vector(0,0),Vector(30000,30000),Vector(0,80000),Vector(30000,110000)):
            for delta in (Vector(200,0),Vector(0,200),Vector(200,200)):
                x,y=env.wind.native._xy(*INVERSE.transform(p.east,p.north));guard=delta.speed+2
                for i in range(-50,51):
                    q=p+delta.scaled(i/100);a,b=env.wind.native._xy(*INVERSE.transform(q.east,q.north))
                    self.assertLessEqual(abs(a-x),guard);self.assertLessEqual(abs(b-y),guard)
