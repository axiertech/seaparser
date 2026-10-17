"""Independent ellipsoidal geodesic references for physical/projected motion."""
from dataclasses import replace
from pathlib import Path
import unittest
from pyproj import Geod
from application.development_weather import load_development_weather,ROOT
from infrastructure.motion_frame import AeqdMotionFrame
from infrastructure.land import FORWARD,INVERSE
from prototype.model import Vector


class MotionFrameTests(unittest.TestCase):
    def test_physical_differential_matches_independent_geodesic_displacements(self):
        frame=AeqdMotionFrame(900);geod=Geod(ellps='WGS84')
        for p in (Vector(0,0),Vector(500,350),Vector(-600,-600),Vector(0,900)):
            lon,lat=INVERSE.transform(p.east,p.north)
            for velocity in (Vector(1,0),Vector(0,1),Vector(3,-4)):
                with self.subTest(position=p,velocity=velocity):
                    # Centred +/-0.5-second physical motion, using ellipsoidal geodesics.
                    a=geod.fwd(lon,lat,velocity.course,velocity.speed*.5)
                    b=geod.fwd(lon,lat,velocity.course+180,velocity.speed*.5)
                    ax,ay=FORWARD.transform(*a[:2]);bx,by=FORWARD.transform(*b[:2])
                    rate=frame.position_rate(p,velocity)
                    self.assertAlmostEqual(rate.east,ax-bx,delta=2e-7)
                    self.assertAlmostEqual(rate.north,ay-by,delta=2e-7)
                    local=Vector(.3,.7);physical=frame.physical_direction(p,local)
                    mapped=frame.position_rate(p,physical)
                    self.assertAlmostEqual(mapped.east*local.north-mapped.north*local.east,0,delta=1e-12)
                    self.assertAlmostEqual(physical.speed,1)

    def test_invalid_domain_and_nonfinite_vectors_rejected(self):
        f=AeqdMotionFrame(900)
        for position,velocity in ((Vector(900.01,0),Vector(1,0)),
                                  (Vector(float('nan'),0),Vector(1,0)),
                                  (Vector(0,0),Vector(float('inf'),0))):
            with self.assertRaises(ValueError):f.position_rate(position,velocity)
        with self.assertRaises(ValueError):f.physical_direction(Vector(0,0),Vector(0,0))

    def test_projected_composition_retains_raw_weather_and_rejects_wrong_units(self):
        projected,config,evidence=load_development_weather(ROOT/'settings/development-weather-projected-assumptions.json')
        from infrastructure.development_forecast import DevelopmentForecast
        old=DevelopmentForecast(projected.dataset_id,projected.version,projected.wind,projected.marine,
                                projected.wind_metadata,projected.assumptions,projected.support_radius_m)
        for p in (Vector(0,0),Vector(500,350)):
            self.assertEqual(projected.evaluate(p,projected.wind.times[0]),old.evaluate(p,old.wind.times[0]))
        self.assertEqual(evidence['source_qualification'],'unverified')
        self.assertEqual(evidence['motion_frame'],'wgs84-aeqd-proj-differential-v1')
        with self.assertRaises(ValueError):
            replace(projected,wind_metadata=replace(projected.wind_metadata,units=('knots','knots')))

    def test_graphic_review_is_reproducible_and_carries_motion_identity(self):
        import json
        from scripts.export_real_routes import build
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            result=build(Path(directory),candidates=4,departures=(0,600,3600,10800),motion_frame=True)
            self.assertEqual((Path(directory)/'result.json').read_bytes(),
                             (ROOT/'artifacts/motion-route-review/result.json').read_bytes())
            self.assertEqual((Path(directory)/'index.html').read_bytes(),
                             (ROOT/'artifacts/motion-route-review/index.html').read_bytes())
        self.assertEqual(len(result['obstacles']['features']),24)
        self.assertEqual(len(result['alternatives']),16)
        self.assertTrue(all(a['status']=='arrived' for a in result['alternatives']))
        self.assertEqual(result['geometry_search']['node_count'],21)
        settings=result['planning']['manifest']['algorithm_settings']['motion_frame']
        self.assertEqual(settings['velocity_frame'],'physical-true-east-north')
        self.assertEqual(settings['position_frame'],'vinga-wgs84-aeqd-metres')
        self.assertEqual(result['weather_provenance']['source_qualification'],'unverified')
        self.assertEqual(result['result_qualification'],'conditional_on_assumptions')
