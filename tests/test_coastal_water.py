import unittest
from shapely import LineString,box,to_wkb
from scripts.build_coastal_water import water_faces
from infrastructure.coastal_water import CoastalWater
from prototype.model import Vector

class CoastalWaterTests(unittest.TestCase):
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
