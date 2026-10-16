"""Whole nonlinear enclosures: exact identities and independent geometric references."""
from decimal import Decimal, localcontext
from fractions import Fraction
from math import atan, atan2, cos, degrees, hypot, pi, radians, sin, tan
import unittest

from pyproj import CRS, Transformer

from infrastructure.native_wind import NATIVE_PROJECTION
from infrastructure.native_wind_geometry import (
    Interval, cos_interval, enclose_source_box, exp_interval, log_interval,
    pi_interval, sin_interval,
)

D=Decimal


class NativeWindGeometryTests(unittest.TestCase):
    def contains(self, bound, value):
        self.assertLessEqual(bound.low,value)
        self.assertGreaterEqual(bound.high,value)

    def test_exact_transcendental_identities_and_pi_reference(self):
        p=pi_interval()
        self.assertLess(p.low,Fraction(D('3.141592653589793238462643383279')))
        self.assertGreater(p.high,Fraction(D('3.141592653589793238462643383280')))
        self.assertLess(p.high-p.low,Fraction(1,10**27))
        self.contains(sin_interval(p/6),Fraction(1,2))
        self.contains(cos_interval(p/3),Fraction(1,2))
        self.contains(exp_interval(log_interval(Interval.point(2))),Fraction(2))
        self.contains(exp_interval(log_interval(Interval.point(Fraction(1,2)))),Fraction(1,2))
        self.contains(log_interval(Interval.point(1)),0)
        self.assertEqual(sin_interval(Interval(0,0)),Interval(0,0))

    def test_outward_rational_operations_and_domain_guards(self):
        a=Interval(Fraction(1,3),Fraction(2,3))
        self.contains(a/3,Fraction(1,9))
        self.contains(a/3,Fraction(2,9))
        self.contains(a*Interval(-2,-1),Fraction(-4,3))
        self.contains(a*Interval(-2,-1),Fraction(-1,3))
        with self.assertRaises(ValueError):
            a/Interval(-1,1)
        with self.assertRaises(ValueError):
            sin_interval(Interval(0,2))
        with self.assertRaises(ValueError):
            log_interval(Interval.point(3))
        with self.assertRaises(ValueError):
            exp_interval(Interval.point(2))

    def test_exact_source_origin_and_symmetry(self):
        x,y=enclose_source_box((63,63),(15,15),NATIVE_PROJECTION)
        self.contains(x,0)
        self.contains(y,0)
        self.assertLess(y.high-y.low,Fraction(1,10**18))
        left=enclose_source_box((63,63),(14,14),NATIVE_PROJECTION)
        right=enclose_source_box((63,63),(16,16),NATIVE_PROJECTION)
        self.assertEqual(left[0],-right[0])
        self.assertEqual(left[1],right[1])

    def test_interior_curve_bulge_is_not_hidden_by_two_endpoint_samples(self):
        # A source-sphere latitude arc crosses the central meridian. Both end
        # points are >390 m north of its middle (the exact natural origin).
        start=enclose_source_box((63,63),(14,14),NATIVE_PROJECTION)
        end=enclose_source_box((63,63),(16,16),NATIVE_PROJECTION)
        self.assertGreater(min(start[1].low,end[1].low),390)
        whole=enclose_source_box((63,63),(14,16),NATIVE_PROJECTION)
        self.contains(whole[1],0)
        self.assertLessEqual(whole[0].low,start[0].low)
        self.assertGreaterEqual(whole[0].high,end[0].high)
        # This exact interior witness disproves endpoint-only AABB containment.

    def test_known_native_points_against_independent_inverse_cone_and_proj(self):
        radius=6371000
        parallel=radians(63)
        n=sin(parallel)
        rho0=radius*cos(parallel)/n
        t0=tan(pi/4+parallel/2)
        crs=CRS.from_proj4(NATIVE_PROJECTION)
        forward=Transformer.from_crs(crs.geodetic_crs,crs,always_xy=True)
        for x,y in [(-205442.2,-595322),(-202442.2,-592322),(-199442.2,-588322)]:
            with self.subTest(x=x,y=y):
                # Closed-form inverse using independent binary math functions.
                rho=hypot(x,rho0-y)
                longitude=15+degrees(atan2(x,rho0-y)/n)
                latitude=degrees(2*atan(t0*(rho0/rho)**(1/n))-pi/2)
                bx,by=enclose_source_box((D(str(latitude)),)*2,(D(str(longitude)),)*2,NATIVE_PROJECTION)
                px,py=forward.transform(longitude,latitude,errcheck=True)
                for bound,known,library in [(bx,x,px),(by,y,py)]:
                    # Numerical-reference tolerance ONLY: the rational enclosure
                    # itself includes no 1 micrometre guessed routing tolerance.
                    self.assertLess(abs(float((bound.low+bound.high)/2)-known),1e-6)
                    self.assertLess(abs(float((bound.low+bound.high)/2)-library),1e-6)
                    self.assertLess(bound.high-bound.low,Fraction(1,10**16))

    def test_encloses_interior_points_without_using_samples_as_the_proof(self):
        lat=(D('57.62'),D('57.65'))
        lon=(D('11.58'),D('11.63'))
        whole=enclose_source_box(lat,lon,NATIVE_PROJECTION)
        for latitude,longitude in [('57.621','11.629'),('57.641','11.582'),('57.633','11.605')]:
            point=enclose_source_box((D(latitude),)*2,(D(longitude),)*2,NATIVE_PROJECTION)
            for bound,inner in zip(whole,point):
                self.assertLessEqual(bound.low,inner.low)
                self.assertGreaterEqual(bound.high,inner.high)

    def test_decimal_context_cannot_change_geometric_enclosure(self):
        args=((D('57.63'),D('57.64')),(D('11.60'),D('11.61')),NATIVE_PROJECTION)
        expected=enclose_source_box(*args)
        with localcontext() as context:
            context.prec=4
            self.assertEqual(enclose_source_box(*args),expected)

    def test_unknown_projection_and_out_of_region_boxes_are_rejected(self):
        for lat,lon,projection in [((57,58),(11,12),'EPSG:4326'),
                                    ((49,58),(11,12),NATIVE_PROJECTION),
                                    ((58,57),(11,12),NATIVE_PROJECTION),
                                    ((57,58),(4,12),NATIVE_PROJECTION)]:
            with self.assertRaises(ValueError):
                enclose_source_box(lat,lon,projection)
