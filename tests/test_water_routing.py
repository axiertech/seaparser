import unittest
from prototype.water_routing import generate_water_routes
from prototype.model import Vector
from prototype.polygon import Polygon

class WaterRoutingTests(unittest.TestCase):
    def test_known_land_wall_cannot_be_shortcut_and_search_is_repeatable(self):
        wall=Polygon('wall',(Vector(40,-10),Vector(60,-10),Vector(60,10),Vector(40,10)))
        start,target=Vector(0,0),Vector(100,0);clear=lambda a,b:not wall.intersects(a,b)
        args=dict(spacing_m=10,max_candidates=2)
        result=generate_water_routes(start,target,(-20,-50,120,50),clear,**args)
        self.assertEqual(result,generate_water_routes(start,target,(-20,-50,120,50),clear,**args))
        self.assertTrue(result.candidates)
        for candidate in result.candidates:
            points=(start,*candidate.waypoints,target)
            self.assertTrue(all(clear(a,b) for a,b in zip(points,points[1:])))
            self.assertGreater(sum((b-a).speed for a,b in zip(points,points[1:])),100)
    def test_resource_limit_is_explicit_not_impossibility_claim(self):
        result=generate_water_routes(Vector(0,0),Vector(100,0),(-20,-50,120,50),lambda a,b:True,max_cells=1,spacing_m=10)
        self.assertEqual(result.status,'grid_limit');self.assertTrue(result.truncated);self.assertEqual(result.candidates,())

    def test_outside_endpoints_cannot_bypass_regional_search_bounds(self):
        with self.assertRaisesRegex(ValueError,'within'):
            generate_water_routes(Vector(-100,0),Vector(100,0),(-20,-50,120,50),lambda a,b:True,spacing_m=10)

    def test_search_exhaustion_does_not_report_a_globally_impossible_voyage(self):
        result=generate_water_routes(Vector(0,0),Vector(100,0),(-20,-50,120,50),lambda a,b:True,
                                     spacing_m=10,max_expansions=1)
        self.assertEqual(result.status,'max_expansions');self.assertTrue(result.truncated)
        self.assertEqual(result.limit_reason,'max_expansions');self.assertFalse(result.candidates)

    def test_duplicate_attempts_still_report_the_candidate_search_limit(self):
        result=generate_water_routes(Vector(0,0),Vector(100,0),(-20,-50,120,50),lambda a,b:True,
                                     spacing_m=10,max_candidates=8)
        self.assertTrue(result.candidates);self.assertTrue(result.truncated)
        self.assertLess(len(result.candidates),8)
        self.assertEqual(result.limit_reason,'max_candidates')
