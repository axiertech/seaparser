import unittest
from shapely import LineString,box,to_wkb
from scripts.build_coastal_water import water_faces,erode_tiled,read_coastlines,validate_erosion
from infrastructure.coastal_water import CoastalWater
from prototype.model import Vector

class CoastalWaterTests(unittest.TestCase):
    def test_sequential_build_stages_admit_only_validated_water_and_reject_corruption(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from hashlib import sha256
        from scripts.build_coastal_water import build
        with TemporaryDirectory() as root:
            directory=Path(root);land=directory/'land';land.mkdir()
            raw=b'<osm><node id="1" lon="11.601" lat="57.601"/><node id="2" lon="11.602" lat="57.601"/><node id="3" lon="11.602" lat="57.602"/><node id="4" lon="11.601" lat="57.602"/><way><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/></way></osm>'
            (land/'coastline.osm').write_bytes(raw)
            (land/'sources.json').write_text(json.dumps({'coastline.osm':{'sha256':sha256(raw).hexdigest(),'bytes':len(raw)}}))
            (directory/'request.json').write_text(json.dumps({'bbox':[11.6,57.6,11.603,57.603]}))
            build(directory,'topology')
            self.assertFalse((land/'water.wkb').exists())
            build(directory,'erode')
            self.assertFalse((land/'water.wkb').exists())
            stage=land/'build-stages/eroded.wkb';original=stage.read_bytes()
            stage.write_bytes(original+b'corrupt')
            with self.assertRaisesRegex(ValueError,'identity/integrity'):build(directory,'validate')
            self.assertFalse((land/'water.wkb').exists())
            stage.write_bytes(original)
            result=build(directory,'validate')
            self.assertEqual(result['source_nodes'],4)
            self.assertEqual(result['water_sha256'],sha256((land/'water.wkb').read_bytes()).hexdigest())
            self.assertEqual(build(directory),result)
            # An existing intermediate is never silently overwritten.
            (land/'water.wkb').unlink();(land/'water.json').unlink()
            with self.assertRaisesRegex(ValueError,'Preserve existing stage'):build(directory,'topology')

    def test_subset_proof_rejects_filled_holes_outside_components_and_boundary_crossings(self):
        from shapely import Polygon
        source=box(0,0,10,10).difference(box(2,2,3,3))
        validate_erosion(source,source.buffer(-.01))
        # Interior witness is wet, but the small off-centre land hole is filled.
        for bad in (box(.01,.01,9.99,9.99),box(11,1,12,2),
                    Polygon([(1,1),(4,1),(2.5,4)]),box(2.4,1,2.6,2.5),
                    source.buffer(-.001),source):
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_erosion(source,bad)

    def test_compact_node_index_preserves_way_order_and_rejects_missing_or_ambiguous_nodes(self):
        from io import BytesIO
        from infrastructure.land import FORWARD
        raw=b'<osm><node id="3" lon="11.7" lat="57.6"/><node id="1" lon="11.6" lat="57.6"/><node id="2" lon="11.6" lat="57.7"/><way><nd ref="2"/><nd ref="1"/><nd ref="3"/></way></osm>'
        lines,nodes,ways=read_coastlines(BytesIO(raw))
        self.assertEqual((nodes,ways),(3,1))
        self.assertEqual(list(lines[0].coords),[FORWARD.transform(*p) for p in ((11.6,57.7),(11.6,57.6),(11.7,57.6))])
        for changed in (raw.replace(b'ref="3"',b'ref="4"'),raw.replace(b'id="3"',b'id="1"'),
                        raw.replace(b'lon="11.7"',b'lon="nan"'),raw.replace(b'<way>',b'<remark>timeout</remark><way>')):
            with self.subTest(changed=changed),self.assertRaises(ValueError):read_coastlines(BytesIO(changed))

    def test_tiled_erosion_preserves_known_area_and_only_closes_sub_guard_channels(self):
        from shapely import unary_union
        geometry,_=erode_tiled(box(0,0,40,40),spacing_m=10)
        self.assertAlmostEqual(geometry.area,(40-.012)**2,places=7)
        for width,connected in ((.02,True),(.01,False)):
            raw=unary_union([box(0,0,10,30),box(20,0,30,30),box(9,15-width/2,21,15+width/2)])
            geometry,_=erode_tiled(raw,spacing_m=10)
            water=CoastalWater(to_wkb(geometry),'known-channel')
            self.assertEqual(water.clear(Vector(5,15),Vector(25,15)),connected)

    def test_noded_face_union_preserves_nested_island_and_lake(self):
        import json
        lines=[LineString([(2,2),(8,2),(8,8),(2,8),(2,2)]),
               LineString([(4,4),(4,6),(6,6),(6,4),(4,4)])]
        events=[]
        geometry,stats=water_faces(lines,box(0,0,10,10),consume_lines=True,progress=events.append)
        self.assertEqual(lines,[])
        self.assertEqual(json.loads(json.dumps(events))[0]['phase'],'erosion')
        water=CoastalWater(to_wkb(geometry),'known-nested-island')
        self.assertEqual(stats['water_faces'],2)
        self.assertAlmostEqual(geometry.area,68,delta=.1)
        self.assertTrue(water.clear(Vector(1,1),Vector(1,9)))
        self.assertTrue(water.clear(Vector(5,4.5),Vector(5,5.5)))
        self.assertFalse(water.clear(Vector(1,5),Vector(5,5)))
        self.assertFalse(water.clear(Vector(3,3),Vector(3,7)))

    def test_tiled_guard_keeps_islands_acute_corners_and_cross_tile_water_connections(self):
        from shapely import Polygon,Point
        # A thin island and sharp peninsula straddle several tile boundaries.
        raw=box(0,0,40,40).difference(Polygon([(12,0),(12.002,0),(12.001,31)]))
        raw=raw.difference(box(19.99,19.99,20.01,20.01))
        tiled,report=erode_tiled(raw,spacing_m=10)
        reference=raw.buffer(-.001,join_style='mitre')
        self.assertTrue(reference.covers(tiled))
        self.assertGreater(tiled.area,raw.area-3)
        water=CoastalWater(to_wkb(tiled),'known-reference')
        self.assertTrue(water.clear(Vector(3,35),Vector(37,35)))
        self.assertFalse(water.clear(Vector(3,20),Vector(37,20)))
        self.assertFalse(water.clear(Vector(15,20),Vector(25,20)))
        # Tile seams in open sea introduce neither land nor extra erosion.
        for x in (9.999,10,10.001,29.999,30,30.001):
            self.assertTrue(tiled.contains(Point(x,35)))
        self.assertEqual(report['erosion_tiles'],16)
        for kwargs in ({'max_tiles':1},{'spacing_m':float('nan')},{'spacing_m':True},{'max_tiles':False}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):erode_tiled(raw,**({'spacing_m':10}|kwargs))

    def test_open_coast_closes_only_at_acquisition_boundary_and_preserves_land_side(self):
        # Directed north: land on the west (left), sea to the east.
        geometry,report=water_faces([LineString([(5,-1),(5,11)])],box(0,0,10,10))
        water=CoastalWater(to_wkb(geometry),'test-source')
        self.assertFalse(water.clear(Vector(4,4),Vector(4,6)))
        self.assertTrue(water.clear(Vector(7,4),Vector(7,6),1))
        self.assertFalse(water.clear(Vector(6,4),Vector(6,6),1))
        self.assertFalse(water.clear(Vector(5,4),Vector(5,6)))
        self.assertEqual(report['water_faces'],1)
    def test_fallback_line_cannot_cross_island_or_peninsula(self):
        island=LineString([(4,4),(6,4),(6,6),(4,6),(4,4)])
        geometry,_=water_faces([island],box(0,0,10,10));water=CoastalWater(to_wkb(geometry),'test')
        self.assertTrue(water.clear(Vector(3,3),Vector(7,3)))
        self.assertFalse(water.clear(Vector(3,5),Vector(7,5)))
        self.assertFalse(water.clear(Vector(5,5),Vector(7,5)))
        self.assertFalse(water.clear(Vector(3,3.5),Vector(7,3.5),.5))
    def test_interior_dangling_coast_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            water_faces([LineString([(5,3),(5,7)])],box(0,0,10,10))

    def test_same_water_component_does_not_allow_fallback_across_a_peninsula(self):
        from shapely import Polygon
        domain=box(0,0,10,10).difference(Polygon([(4,0),(6,0),(6,8),(4,8)]))
        water=CoastalWater(to_wkb(domain),'test')
        self.assertEqual(water.geometry.geom_type,'Polygon')
        self.assertFalse(water.clear(Vector(3,5),Vector(7,5)))
        self.assertTrue(water.clear(Vector(3,9),Vector(7,9)))

    def test_water_path_goes_around_peninsula_with_distance_and_budget_limits(self):
        from shapely import Polygon
        geometry=box(0,0,100,100).difference(Polygon([(40,0),(60,0),(60,80),(40,80)]))
        water=CoastalWater(to_wkb(geometry),'test');a,b=Vector(30,50),Vector(70,50)
        connection=water.connection(a,b,max_distance_m=120,spacing_m=5,margin_m=1)
        self.assertEqual(connection.status,'found');self.assertGreater(connection.distance_m,70)
        self.assertLessEqual(connection.distance_m,120)
        self.assertTrue(all(water.clear(a,b,1) for a,b in zip(connection.points,connection.points[1:])))
        self.assertNotEqual(water.connection(a,b,max_distance_m=50,spacing_m=5).status,'found')
        self.assertEqual(water.connection(a,b,max_distance_m=120,spacing_m=5,max_cells=1).status,'max_cells')
        self.assertEqual(water.connection(a,b,max_distance_m=120,spacing_m=5,max_expansions=1).status,'max_expansions')

    def test_disconnected_water_never_becomes_a_connection(self):
        from shapely import unary_union
        water=CoastalWater(to_wkb(unary_union([box(0,0,40,100),box(60,0,100,100)])),'test')
        self.assertEqual(water.connection(Vector(30,50),Vector(70,50),max_distance_m=1000).status,'disconnected_water')

    def test_prepared_component_membership_excludes_holes_and_closed_boundaries(self):
        from shapely import unary_union
        water=CoastalWater(to_wkb(unary_union([box(0,0,40,100).difference(box(10,10,20,20)),
                                             box(60,0,100,100)])),'test')
        left=water._component_ids(Vector(5,5));right=water._component_ids(Vector(80,50))
        self.assertEqual(len(left),1);self.assertEqual(len(right),1);self.assertFalse(left.intersection(right))
        for point in (Vector(15,15),Vector(10,15),Vector(0,50),Vector(50,50),Vector(100,100)):
            with self.subTest(point=point):self.assertEqual(water._component_ids(point),frozenset())

    def test_cached_components_keep_connection_budget_margin_and_snapshot_rejections(self):
        from unittest.mock import patch
        geometry=box(0,0,100,100).difference(box(40,0,60,80))
        water=CoastalWater(to_wkb(geometry),'test');a,b=Vector(30,50),Vector(70,50)
        options=dict(max_distance_m=120,spacing_m=5,margin_m=1)
        first=water.connection(a,b,**options)
        self.assertEqual(first.status,'found')
        with patch.object(water.components,'query',side_effect=AssertionError('Exact component membership must be reused')):
            self.assertEqual(water.connection(a,b,**options),first)
        for changes,status in (({'max_distance_m':30},'distance_limit'),({'max_cells':1},'max_cells'),
                               ({'max_expansions':1},'max_expansions'),({'margin_m':10},'endpoint_blocked')):
            with self.subTest(changes=changes):
                self.assertEqual(water.connection(a,b,**(options|changes)).status,status)
        closed=CoastalWater(to_wkb(box(0,0,100,100).difference(box(40,0,60,100))),'different-snapshot')
        self.assertEqual(closed.connection(a,b,**options).status,'disconnected_water')
        # Warming the geometry cache must not bypass search argument validation.
        water.connection(a,b,**(options|{'max_cells':1}))
        for changes in ({'max_cells':True},{'margin_m':True},{'spacing_m':False},{'max_distance_m':float('nan')}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                water.connection(a,b,**(options|changes))
