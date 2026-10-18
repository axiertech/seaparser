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
