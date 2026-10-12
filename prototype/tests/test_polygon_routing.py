"""Analytic geometry references and full time-dependent route integration."""
from datetime import datetime, timedelta, timezone
from math import hypot
import unittest
from prototype.auto_routing import generate_routes, SearchPolicy
from prototype.environment import Conditions, SyntheticEnvironment
from prototype.model import Vector, KNOT
from prototype.polygon import Polygon
from prototype.routes import compare_routes

START = datetime(2026,1,1,tzinfo=timezone.utc)
A, B = Vector(0,0), Vector(100,0)

def box(margin=0, **kwargs):
    return Polygon('island',(Vector(40,-10),Vector(60,-10),Vector(60,10),Vector(40,10)),margin,**kwargs)

class PolygonReferenceTests(unittest.TestCase):
    def test_crossing_and_closed_boundary(self):
        polygon=box()
        for a,b in ((A,B),(Vector(40,10),Vector(60,10)),(Vector(40,10),Vector(40,10)),
                    (Vector(45,0),Vector(45,0)),(Vector(60,10),Vector(70,20))):
            self.assertTrue(polygon.intersects(a,b))
            self.assertTrue(polygon.intersects(b,a))
        self.assertFalse(polygon.intersects(Vector(0,11),Vector(100,11)))

    def test_euclidean_margin_parallel_and_three_four_five_corner(self):
        polygon=box(5)
        self.assertTrue(polygon.intersects(Vector(0,15),Vector(100,15)))
        self.assertFalse(polygon.intersects(Vector(0,15.000001),Vector(100,15.000001)))
        self.assertTrue(polygon.intersects(Vector(37,-14),Vector(37,-14)))
        self.assertFalse(polygon.intersects(Vector(36,-14),Vector(36,-14)))
        # Entire crossing is caught though both endpoints are outside the margin.
        self.assertTrue(polygon.intersects(Vector(0,12),Vector(100,12)))

    def test_diagonal_distance_reference(self):
        triangle=Polygon('triangle',(Vector(0,0),Vector(10,0),Vector(0,10)),1)
        # Distance from x+y=10 to x+y=11 is 1/sqrt(2), to 12 is sqrt(2).
        self.assertTrue(triangle.intersects(Vector(4,7),Vector(7,4)))
        self.assertFalse(triangle.intersects(Vector(4,8),Vector(8,4)))

    def test_concave_notch_and_winding(self):
        vertices=(Vector(0,0),Vector(6,0),Vector(6,6),Vector(4,6),Vector(4,2),
                  Vector(2,2),Vector(2,6),Vector(0,6))
        for sequence in (vertices,vertices[::-1]):
            polygon=Polygon('notch',sequence)
            self.assertFalse(polygon.intersects(Vector(3,3),Vector(3,7)))
            self.assertTrue(polygon.intersects(Vector(-1,4),Vector(7,4)))

    def test_invalid_and_mutable_inputs(self):
        for vertices in ((Vector(0,0),Vector(2,2),Vector(0,2),Vector(2,0)),
                         (Vector(0,0),Vector(1,0),Vector(2,0))):
            with self.assertRaises(ValueError):
                Polygon('bad',vertices)
        mutable=list(box().vertices); polygon=Polygon('frozen',mutable)
        mutable[0]=Vector(1000,1000)
        self.assertTrue(polygon.intersects(A,B))
        with self.assertRaises(ValueError):
            box(-1)
        with self.assertRaises(ValueError):
            box(quality='trusted')

    def test_information_layer_is_not_hard_ban(self):
        self.assertFalse(box(restriction='information',quality='unknown').intersects(A,B))
        self.assertTrue(box(quality='unknown').intersects(A,B))

class AutomaticRoutingTests(unittest.TestCase):
    def test_free_direct_path(self):
        result=generate_routes(A,B,())
        self.assertEqual(result.status,'candidates_found')
        self.assertEqual(result.lengths_m,(100,))
        self.assertEqual(result.candidates[0].waypoints,())
        self.assertFalse(result.truncated)

    def test_obstacle_detour_matches_analytic_length_and_all_edges_clear(self):
        polygon=box(2)
        result=generate_routes(A,B,(polygon,),SearchPolicy(clearance_m=1,max_candidates=8))
        self.assertGreater(len(result.candidates),1)
        self.assertAlmostEqual(result.lengths_m[0],2*hypot(37,13)+26,places=10)
        for candidate in result.candidates:
            points=(A,*candidate.waypoints,B)
            self.assertTrue(all(not polygon.intersects(a,b) for a,b in zip(points,points[1:])))
        comparison=compare_routes(SyntheticEnvironment(lambda p,t: Conditions(Vector(0,0))),
                                  START,B,result.candidates,obstacles=(polygon,),speed_knots=1/KNOT,
                                  step_seconds=100,tolerance_m=1e-6)
        self.assertAlmostEqual(comparison.fastest.travel_seconds,result.lengths_m[0],delta=1e-5)
        for route in comparison.candidates:
            for leg in route.legs:
                for step in leg.steps:
                    self.assertFalse(polygon.intersects(step.start.position,step.end_position))

    def test_endpoint_and_search_limits_are_explicit(self):
        self.assertEqual(generate_routes(Vector(50,0),B,(box(),)).status,'endpoint_blocked')
        for policy in (SearchPolicy(max_nodes=2),SearchPolicy(max_expansions=1),SearchPolicy(max_waypoints=1)):
            result=generate_routes(A,B,(box(),),policy)
            self.assertTrue(result.truncated)
            self.assertEqual(result.candidates,())
        with self.assertRaises(ValueError):
            SearchPolicy(clearance_m=0)
        with self.assertRaises(ValueError):
            SearchPolicy(max_expansions=100001)

    def test_obstacle_generator_consumption_is_bounded(self):
        count = 0
        def obstacles():
            nonlocal count
            while True:
                count += 1
                yield box()
        with self.assertRaises(ValueError):
            generate_routes(A,B,obstacles())
        self.assertEqual(count,65)

    def test_multiple_obstacles_and_repeatability(self):
        second=Polygon('second',(Vector(70,-5),Vector(80,-5),Vector(80,8),Vector(70,8)))
        result=generate_routes(A,B,(box(),second),SearchPolicy(max_candidates=4))
        self.assertEqual(result,generate_routes(A,B,(box(),second),SearchPolicy(max_candidates=4)))
        self.assertTrue(result.candidates)
        for candidate in result.candidates:
            points=(A,*candidate.waypoints,B)
            for a,b in zip(points,points[1:]):
                self.assertFalse(box().intersects(a,b) or second.intersects(a,b))

    def test_longer_geometry_can_be_faster_with_timed_current(self):
        polygon=Polygon('offset',(Vector(40,-15),Vector(60,-15),Vector(60,10),Vector(40,10)))
        generated=generate_routes(A,B,(polygon,),SearchPolicy(max_candidates=12,clearance_m=2))
        switch=START+timedelta(seconds=15)
        env=SyntheticEnvironment(lambda p,t: Conditions(Vector(.7 if p.north < -1 and t >= switch else 0,0)))
        comparison=compare_routes(env,START,B,generated.candidates,obstacles=(polygon,),
                                  speed_knots=1/KNOT,step_seconds=1,tolerance_m=1e-5)
        shortest=generated.candidates[0]
        self.assertNotEqual(comparison.fastest.candidate,shortest)
        index=generated.candidates.index(comparison.fastest.candidate)
        self.assertGreater(generated.lengths_m[index],generated.lengths_m[0])
        for leg in comparison.fastest.legs[1:]:
            self.assertGreater(leg.steps[0].start.time,START)
