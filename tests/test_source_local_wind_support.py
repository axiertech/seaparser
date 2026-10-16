"""Source-sphere affine paths: whole-disk proof, independent references and gates."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from math import asin, atan2, cos, degrees, hypot, radians, sin
from pathlib import Path
import unittest

from pyproj import CRS, Transformer

from application.native_wind_support import SourceLocalSegment, inspect_source_local_segment
from infrastructure.native_wind import NATIVE_PROJECTION
from infrastructure.native_wind_geometry import (
    Interval, SOURCE_LOCAL_DEFINITION, SOURCE_LOCAL_FRAME, SOURCE_LOCAL_ORIGIN,
    enclose_source_local_segment, sqrt_interval,
)
from scripts.native_wind_segment import inspect_file
from scripts.regional_forecast import load_native_wind

ROOT=Path(__file__).resolve().parents[1]
D=Decimal


def local_segment(**changes):
    return replace(SourceLocalSegment(D(-300),D(-200),D(400),D(300),
        datetime(2026,10,13,12,20,tzinfo=timezone.utc),
        datetime(2026,10,13,14,40,tzinfo=timezone.utc),SOURCE_LOCAL_FRAME),**changes)


def spherical_cartesian_reference(east,north):
    """Independent vector great-circle formula from the tangent basis."""
    latitude,longitude=map(lambda v:radians(float(v)),SOURCE_LOCAL_ORIGIN)
    origin=(cos(latitude)*cos(longitude),cos(latitude)*sin(longitude),sin(latitude))
    e=(-sin(longitude),cos(longitude),0)
    n=(-sin(latitude)*cos(longitude),-sin(latitude)*sin(longitude),cos(latitude))
    radius=hypot(east,north)
    if not radius:
        return float(SOURCE_LOCAL_ORIGIN[0]),float(SOURCE_LOCAL_ORIGIN[1])
    c=radius/6371000
    point=[cos(c)*o+sin(c)*(east*ev+north*nv)/radius for o,ev,nv in zip(origin,e,n)]
    return degrees(asin(point[2])),degrees(atan2(point[1],point[0]))


class SourceLocalWindSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wind=load_native_wind(ROOT/'fixtures')

    def test_integer_square_comparisons_bound_exact_and_irrational_roots(self):
        self.assertEqual(sqrt_interval(Interval(25,25)),Interval(5,5))
        self.assertEqual(sqrt_interval(Interval(0,0)),Interval(0,0))
        root=sqrt_interval(Interval(2,2))
        self.assertLess(root.low**2,2)
        self.assertGreater(root.high**2,2)
        self.assertLessEqual(root.high-root.low,Fraction(1,10**30))
        r=sqrt_interval(Interval(Fraction(1,3),Fraction(7,3)))
        self.assertLessEqual(r.low**2,Fraction(1,3))
        self.assertGreaterEqual(r.high**2,Fraction(7,3))
        with self.assertRaises(ValueError):
            sqrt_interval(Interval(-1,1))

    def test_origin_and_known_three_four_five_radius(self):
        origin=enclose_source_local_segment((0,0),(0,0),NATIVE_PROJECTION)
        self.assertEqual(origin[2],Interval.point(SOURCE_LOCAL_ORIGIN[0]))
        self.assertEqual(origin[3],Interval.point(SOURCE_LOCAL_ORIGIN[1]))
        self.assertEqual(origin[4],Interval(0,0))
        example=enclose_source_local_segment((-300,-200),(400,300),NATIVE_PROJECTION)
        self.assertEqual(example[4],Interval(500,500))
        self.assertEqual(example[5],250000)
        # Exact origin-to-north distance r on a sphere gives delta latitude r/R.
        north_lat=spherical_cartesian_reference(0,500)[0]
        self.assertAlmostEqual(float(example[2].high),north_lat,places=10)

    def test_cardinal_and_diagonal_disk_points_match_independent_sphere_and_proj(self):
        # Sampling is a numerical regression, NOT the containment proof. That
        # proof is the metric inequality and interval image of the entire disk.
        x,y,lat,lon,_,_=enclose_source_local_segment((1000,0),(-1000,0),NATIVE_PROJECTION)
        local=CRS.from_proj4(SOURCE_LOCAL_DEFINITION)
        native=CRS.from_proj4(NATIVE_PROJECTION)
        inverse=Transformer.from_crs(local,local.geodetic_crs,always_xy=True)
        forward=Transformer.from_crs(native.geodetic_crs,native,always_xy=True)
        for east,north in [(0,0),(1000,0),(-1000,0),(0,1000),(0,-1000),(600,800),(-800,600)]:
            with self.subTest(east=east,north=north):
                phi,lam=spherical_cartesian_reference(east,north)
                library_lon,library_lat=inverse.transform(east,north,errcheck=True)
                self.assertAlmostEqual(phi,library_lat,places=10)
                self.assertAlmostEqual(lam,library_lon,places=10)
                self.assertLessEqual(float(lat.low)-1e-10,phi)
                self.assertGreaterEqual(float(lat.high)+1e-10,phi)
                self.assertLessEqual(float(lon.low)-1e-10,lam)
                self.assertGreaterEqual(float(lon.high)+1e-10,lam)
                px,py=forward.transform(lam,phi,errcheck=True)
                self.assertLessEqual(float(x.low)-1e-6,px)
                self.assertGreaterEqual(float(x.high)+1e-6,px)
                self.assertLessEqual(float(y.low)-1e-6,py)
                self.assertGreaterEqual(float(y.high)+1e-6,py)

    def test_affine_segment_interior_and_decimal_context_are_not_sampled_or_rounded_away(self):
        # Opposite endpoints give a long segment through the origin. Norm squared
        # at every rational fraction is <= the known maximum endpoint norm².
        a,b=(Fraction(-800),Fraction(-600)),(Fraction(800),Fraction(600))
        expected=enclose_source_local_segment(a,b,NATIVE_PROJECTION)
        for t in (Fraction(1,7),Fraction(1,2),Fraction(8,9)):
            p=tuple((1-t)*v+t*w for v,w in zip(a,b))
            self.assertLessEqual(sum(v*v for v in p),expected[5])
            self.assertEqual(enclose_source_local_segment(p,p,NATIVE_PROJECTION)[5],sum(v*v for v in p))
        with localcontext() as context:
            context.prec=4
            self.assertEqual(enclose_source_local_segment(a,b,NATIVE_PROJECTION),expected)

    def test_known_twelve_boxes_and_all_36_nodes_reuse_source_snapshot(self):
        r=inspect_source_local_segment(self.wind,local_segment())
        self.assertEqual(r['adjacent_node_boxes'],[[k,j,i] for k in (0,1,2) for j in (2,3) for i in (2,3)])
        self.assertEqual(len(r['raw_nodes']),36)
        self.assertEqual({tuple(n['index']) for n in r['raw_nodes']},
                         {(k,j,i) for k in range(4) for j in (2,3,4) for i in (2,3,4)})
        self.assertTrue(r['raw_inventory_complete'])
        self.assertEqual(r['segment']['start_east_m'],'-300')
        self.assertEqual(r['segment']['end_north_m'],'300')
        self.assertEqual(r['source_hashes'],dict(self.wind.source_hashes))
        self.assertEqual(r['source_local_geometry']['local_definition'],SOURCE_LOCAL_DEFINITION)
        self.assertTrue(r['source_local_geometry']['local_to_source_sphere_enclosure_verified'])
        self.assertFalse(r['source_local_geometry']['wgs84_route_binding_verified'])
        self.assertFalse(r['local_route_geometry_binding_verified'])
        self.assertFalse(r['physical_source_support_qualified'])
        self.assertIsNone(r['source_to_wgs84_datum_error_m'])
        self.assertIsNone(r['source_coordinate_serialization_error_m'])
        self.assertIsNone(r['provider_wind_validity_mask'])
        self.assertIsNone(r['wind_safety_envelope'])
        self.assertFalse(r['provider_interpolation_stencil_verified'])
        self.assertIsNone(r['mean_window_placement'])
        self.assertEqual(r['routing_status'],'data_unavailable')
        self.assertIsNone(r['fastest_candidate'])
        self.assertIsNone(r['comfortable_candidate'])

    def test_same_enclosing_disk_does_not_erase_actual_path_from_report_hash(self):
        a=local_segment(start_east_m=D(300),start_north_m=D(400),end_east_m=D(-300),end_north_m=D(-400))
        b=replace(a,start_east_m=D(-300),start_north_m=D(-400),end_east_m=D(300),end_north_m=D(400))
        ra,rb=(inspect_source_local_segment(self.wind,s) for s in (a,b))
        self.assertEqual(ra['source_local_geometry'],rb['source_local_geometry'])
        self.assertEqual(ra['projected_enclosure_m'],rb['projected_enclosure_m'])
        self.assertNotEqual(ra['report_sha256'],rb['report_sha256'])
        self.assertEqual(ra['source_input_sha256'],rb['source_input_sha256'])

    def test_budget_missing_corner_and_nominal_time_failure_remain_fail_closed(self):
        r=inspect_source_local_segment(self.wind,local_segment(),max_cells=11)
        self.assertEqual(r['intersecting_box_count'],12)
        self.assertFalse(r['raw_inventory_complete'])
        self.assertEqual(r['adjacent_node_boxes'],[])
        self.assertEqual(r['raw_nodes'],[])
        raw=[[[v for v in row] for row in plane] for plane in self.wind.speed_m_s]
        raw[0][2][2]=None
        changed=replace(self.wind,speed_m_s=tuple(tuple(tuple(row) for row in plane) for plane in raw))
        r=inspect_source_local_segment(changed,local_segment())
        self.assertFalse(r['raw_inventory_complete'])
        self.assertIn('missing_or_nonfinite_raw_node',r['inventory_failures'])
        r=inspect_source_local_segment(self.wind,local_segment(end_time=datetime(2026,10,13,17,tzinfo=timezone.utc)))
        self.assertFalse(r['nominal_time_box_inside'])
        self.assertEqual(r['raw_nodes'],[])

    def test_wgs84_relabelling_and_unreviewed_radius_never_pass(self):
        for frame in ('EPSG:4326','WGS84-AEQD','met-source-sphere-angular-linear-v1',''):
            with self.assertRaises(ValueError):
                inspect_source_local_segment(self.wind,local_segment(coordinate_frame=frame))
        for east,north in [(D(1000),D('0.0000000001')),(D('1000.0000000001'),D(0))]:
            with self.assertRaises(ValueError):
                inspect_source_local_segment(self.wind,local_segment(end_east_m=east,end_north_m=north))
        for changes in ({'start_east_m':True},{'start_east_m':300.0},{'start_time':datetime(2026,10,13,12)}):
            with self.assertRaises(ValueError):
                inspect_source_local_segment(self.wind,local_segment(**changes))

    def test_cli_preserves_previous_angular_report_and_new_local_coordinates(self):
        r=inspect_file(ROOT/'fixtures',ROOT/'fixtures/met-source-local-segment.json')
        self.assertEqual(r,inspect_source_local_segment(self.wind,local_segment()))
        old=inspect_file(ROOT/'fixtures',ROOT/'fixtures/met-source-sphere-segment.json')
        frozen=json.loads((ROOT/'artifacts/native-wind-segment-review/report.json').read_text())
        self.assertEqual(old,frozen)
