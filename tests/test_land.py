import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from infrastructure.land import load_land,hull,FORWARD
from prototype.model import Vector
from prototype.polygon import inside,xy
from scripts.land_preview import build


class LandTests(unittest.TestCase):
    def test_independent_square_hull_contains_concavity(self):
        points=(Vector(0,0),Vector(4,0),Vector(2,1),Vector(4,4),Vector(0,4))
        result=hull(points)
        self.assertEqual(set(result),{Vector(0,0),Vector(4,0),Vector(4,4),Vector(0,4)})
        self.assertTrue(inside(xy(Vector(3,2)),tuple(xy(p) for p in result)))

    def test_snapshot_and_entire_land_segments(self):
        snapshot=load_land(); self.assertEqual(len(snapshot.obstacles),6)
        self.assertEqual(snapshot.depth_status,'unknown')
        for feature,polygon in zip(json.loads(snapshot.source_geojson)['features'],snapshot.obstacles):
            vertices=tuple(xy(p) for p in polygon.vertices)
            for lon,lat in feature['geometry']['coordinates'][0]:
                self.assertTrue(inside(xy(Vector(*FORWARD.transform(lon,lat))),vertices))
            a,b=polygon.vertices[:2]
            self.assertTrue(polygon.intersects(a,b))

    def test_open_ring_rejected_and_input_is_frozen(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'land.json'; data=json.loads(load_land().source_geojson)
            path.write_text(json.dumps(data)); snapshot=load_land(path)
            data['features'][0]['geometry']['coordinates'][0].pop()
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): load_land(path)
            self.assertEqual(len(snapshot.obstacles),6)

    def test_export_is_public_only_and_no_automatic_tiles(self):
        with TemporaryDirectory() as directory:
            output=Path(directory); build(output)
            self.assertEqual({p.name for p in output.iterdir()},{'land.geojson','routing.geojson','land-review.html','land-review.mjs','vinga.html'})
            self.assertEqual(json.loads((output/'land.geojson').read_text())['metadata']['depth'],'unknown')
            self.assertIn("addEventListener('click'",(output/'land-review.mjs').read_text())
            html=(output/'vinga.html').read_text()
            self.assertIn('data-profile="vinga"',html)
            self.assertIn('Ej navigationssäkert',html)
            self.assertIn('ungefärlig vald marginal',html)
            self.assertIn('https://tile.openstreetmap.org',html)
            self.assertIn('strict-origin-when-cross-origin',html)

    def test_geographic_frame_against_independent_geodesic(self):
        from pyproj import Geod
        from math import sin,cos,radians
        geod=Geod(ellps='WGS84')
        for bearing in (0,45,90,180,270):
            lon,lat,_=geod.fwd(11.605,57.633,bearing,1000)
            east,north=FORWARD.transform(lon,lat)
            self.assertAlmostEqual(east,1000*sin(radians(bearing)),places=5)
            self.assertAlmostEqual(north,1000*cos(radians(bearing)),places=5)

    def test_routing_reuses_whole_segment_and_margin_checks(self):
        from prototype.auto_routing import generate_routes,SearchPolicy
        snapshot=load_land(); shape=snapshot.obstacles[0]
        xs=[v.east for v in shape.vertices]; ys=[v.north for v in shape.vertices]
        y=(min(ys)+max(ys))/2
        start=Vector(min(xs)-50,y); target=Vector(max(xs)+50,y)
        self.assertTrue(shape.intersects(start,target))
        report=generate_routes(start,target,(shape,),SearchPolicy(max_candidates=4))
        self.assertTrue(report.candidates)
        for route in report.candidates:
            points=(start,*route.waypoints,target)
            for a,b in zip(points,points[1:]):
                self.assertFalse(shape.intersects(a,b))

    def test_bundle_export_does_not_copy_unrelated_files(self):
        from unittest.mock import patch
        from scripts.land_preview import build_bundle
        copied=[]
        with TemporaryDirectory() as directory:
            output=Path(directory)
            with patch('scripts.land_preview.copyfile',side_effect=lambda source,target: copied.append(target.relative_to(output).as_posix())):
                build_bundle(output)
            # Independent public export contract, including the fixed Leaflet assets.
            expected={'index.html','map.css','main.mjs','map-component.mjs','controller.mjs','client.mjs',
                      'vendor/leaflet.js','vendor/leaflet.css','vendor/leaflet-LICENSE.txt',
                      'vendor/images/marker-shadow.png','vendor/images/marker-icon.png','vendor/images/marker-icon-2x.png',
                      'vendor/images/layers.png','vendor/images/layers-2x.png'}
            self.assertEqual(set(copied),expected)
            self.assertEqual(len(copied),14)
            self.assertFalse(any('config' in name or 'log' in name or name.startswith('.') for name in copied))
