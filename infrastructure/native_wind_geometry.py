"""Whole-box spherical LCC enclosures, with rational outward interval arithmetic.

This is the exact reviewed *source sphere*, not a WGS84 datum transformation.
No projection library, floating-point sampling, wind rotation or interpolation.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from infrastructure.native_wind import NATIVE_PROJECTION

METHOD = 'met-spherical-lcc-rational-box-v1'
SCALE = 10**30
TERMS = 48


def _down(value):
    return Fraction((value * SCALE).__floor__(), SCALE)


def _up(value):
    return Fraction((value * SCALE).__ceil__(), SCALE)


@dataclass(frozen=True)
class Interval:
    low: Fraction
    high: Fraction

    def __post_init__(self):
        object.__setattr__(self, 'low', Fraction(self.low))
        object.__setattr__(self, 'high', Fraction(self.high))
        if self.low > self.high:
            raise ValueError('Reversed interval')

    @classmethod
    def point(cls, value):
        value = Fraction(value)
        return cls(value, value)

    @classmethod
    def outward(cls, low, high):
        return cls(_down(low), _up(high))

    def __add__(self, other):
        other = _interval(other)
        return Interval.outward(self.low + other.low, self.high + other.high)

    __radd__ = __add__

    def __neg__(self):
        return Interval(-self.high, -self.low)

    def __sub__(self, other):
        return self + -_interval(other)

    def __rsub__(self, other):
        return _interval(other) + -self

    def __mul__(self, other):
        other = _interval(other)
        ends = [a*b for a in (self.low, self.high) for b in (other.low, other.high)]
        return Interval.outward(min(ends), max(ends))

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = _interval(other)
        if other.low <= 0 <= other.high:
            raise ValueError('Division interval contains zero')
        return self * Interval.outward(1/other.high, 1/other.low)


def _interval(value):
    return value if isinstance(value, Interval) else Interval.point(value)


def _alternating_atan(x):
    # 0<x<1: alternating remainder lies between adjacent partial sums.
    total = sum(((-1)**k * x**(2*k+1) / (2*k+1) for k in range(TERMS)), Fraction(0))
    adjacent = total + (-1)**TERMS * x**(2*TERMS+1)/(2*TERMS+1)
    return Interval.outward(min(total, adjacent), max(total, adjacent))


@lru_cache(maxsize=1)
def pi_interval():
    # Machin identity; exact rational alternating-series bounds, no decimal pi.
    return 16*_alternating_atan(Fraction(1,5)) - 4*_alternating_atan(Fraction(1,239))


def _trig_point(x, cosine=False):
    if abs(x) > Fraction(3,2):
        raise ValueError('Trigonometric argument outside reviewed interval')
    if x < 0:
        result = _trig_point(-x, cosine)
        return result if cosine else -result
    term, total = (Fraction(1) if cosine else x), Fraction(0)
    for k in range(TERMS):
        total += term
        a = 2*k + (1 if cosine else 2)
        term *= -x*x / (a*(a+1))
    # At this truncation the alternating tail is decreasing for |x|<=1.5.
    return Interval.outward(min(total,total+term), max(total,total+term))


def sin_interval(x):
    # sin is increasing on [-1.5,1.5], a strict subset of [-pi/2,pi/2].
    return Interval(_trig_point(x.low).low, _trig_point(x.high).high)


def cos_interval(x):
    a, b = _trig_point(x.low, True), _trig_point(x.high, True)
    return Interval(min(a.low,b.low), Fraction(1) if x.low <= 0 <= x.high else max(a.high,b.high))


def _log_point(x):
    if not Fraction(1,2) <= x <= 2:
        raise ValueError('Logarithm outside reviewed interval')
    u = (x-1)/(x+1)
    total = 2*sum((u**(2*k+1)/(2*k+1) for k in range(TERMS)), Fraction(0))
    # Bound every omitted denominator below by the first omitted denominator.
    tail = 2*abs(u)**(2*TERMS+1)/((2*TERMS+1)*(1-u*u))
    return Interval.outward(total-tail,total+tail)


def log_interval(x):
    return Interval(_log_point(x.low).low,_log_point(x.high).high)


def _exp_point(x):
    if abs(x) > 1:
        raise ValueError('Exponential outside reviewed interval')
    if x < 0:
        return Interval.point(1)/_exp_point(-x)
    total, term = Fraction(0), Fraction(1)
    for k in range(TERMS):
        total += term
        term *= x/(k+1)
    # Positive tail after x^47/47!: ratios <= x/49 after first omitted term.
    return Interval.outward(total,total+term/(1-x/(TERMS+1)))


def exp_interval(x):
    return Interval(_exp_point(x.low).low,_exp_point(x.high).high)


def _tan(x):
    return sin_interval(x)/cos_interval(x)


@lru_cache(maxsize=1)
def _cone():
    pi = pi_interval()
    parallel = pi*Fraction(63,180)
    n = sin_interval(parallel)
    rho0 = 6371000*cos_interval(parallel)/n
    t0 = _tan(pi/4 + parallel/2)
    return pi, n, rho0, t0


def enclose_source_box(latitude, longitude, projection):
    """Enclose EVERY point in the closed lat/lon rectangle on the source sphere.

    phi in [50,70] deg and lambda in [5,25] deg. Tangent spherical LCC:
    n=sin(63deg), rho0=R*cos(63deg)/n, t0=tan(pi/4+63deg/2),
    rho=rho0*exp(n*log(t0/tan(pi/4+phi/2))), theta=n*(lambda-15deg),
    x=rho*sin(theta), y=rho0-rho*cos(theta).
    Each operation encloses its whole input interval, including series tails.
    No node/edge samples establish containment. Output includes arithmetic error
    but NOT unknown source serialization, geodetic datum or path-binding errors.
    """
    if projection != NATIVE_PROJECTION:
        raise ValueError('Only reviewed MET source-sphere projection supported')
    lat = Interval(*(Fraction(v) for v in latitude))
    lon = Interval(*(Fraction(v) for v in longitude))
    if not (50 <= lat.low <= lat.high <= 70 and 5 <= lon.low <= lon.high <= 25):
        raise ValueError('Source-sphere box outside reviewed mathematical region')
    pi, n, rho0, t0 = _cone()
    phi = lat*pi/180
    theta = n*(lon-15)*pi/180
    rho = rho0*exp_interval(n*log_interval(t0/_tan(pi/4 + phi/2)))
    return rho*sin_interval(theta), rho0-rho*cos_interval(theta)


# Deliberately a SOURCE-SPHERE frame; this is not the existing WGS84 AEQD frame.
SOURCE_LOCAL_FRAME = 'met-source-sphere-aeqd-affine-v1'
SOURCE_LOCAL_DEFINITION = '+proj=aeqd +lat_0=57.633 +lon_0=11.605 +R=6371000 +units=m +no_defs'
SOURCE_LOCAL_ORIGIN = (Fraction(57633,1000), Fraction(2321,200))
SOURCE_LOCAL_MAX_RADIUS_M = 1000
LOCAL_METHOD = 'met-source-sphere-aeqd-disk-lcc-v1'


def sqrt_interval(x):
    """Exact integer-square comparisons bound a nonnegative rational square root."""
    from math import isqrt
    if x.low < 0:
        raise ValueError('Square root interval must be nonnegative')
    def floor_root(value):
        return isqrt(value.numerator*SCALE*SCALE//value.denominator)
    low, high = floor_root(x.low), floor_root(x.high)
    if high*high*x.high.denominator < x.high.numerator*SCALE*SCALE:
        high += 1
    return Interval(Fraction(low,SCALE),Fraction(high,SCALE))


def enclose_source_local_segment(start, end, projection):
    """Enclose the ENTIRE affine segment in source-sphere AEQD, including error.

    ||(1-t)a+t*b|| <= max(||a||,||b||), so all points lie in the AEQD origin disk.
    Spherical AEQD radius r is geodesic distance to its origin. Along any radial
    geodesic of length <=r, |delta phi|<=r/R. In that latitude strip, the sphere's
    metric bounds |d lambda/ds|<=1/(R*min cos(phi)). This bounds longitude for ALL
    points in the disk, without inverse-projection or edge sampling. The whole
    resulting geographic box is passed to the existing rational LCC enclosure.
    There is no WGS84 datum transformation or wind interpolation here.
    """
    if len(start)!=2 or len(end)!=2:
        raise ValueError('Two exact east/north coordinates required per endpoint')
    a,b = (tuple(Fraction(v) for v in point) for point in (start,end))
    radius_squared = max(sum((v*v for v in point),Fraction(0)) for point in (a,b))
    if radius_squared > SOURCE_LOCAL_MAX_RADIUS_M**2:
        raise ValueError('Source-sphere local segment outside reviewed 1000 m disk')
    radius = sqrt_interval(Interval.point(radius_squared))
    pi = pi_interval()
    angular_degrees = (Interval.point(radius.high)/6371000)*180/pi
    latitude0,longitude0 = SOURCE_LOCAL_ORIGIN
    latitude = Interval.point(latitude0)+Interval(-angular_degrees.high,angular_degrees.high)
    cos_strip = cos_interval(latitude*pi/180)
    if cos_strip.low <= 0:
        raise ValueError('Source-sphere disk cannot cross a pole')
    longitude_delta = angular_degrees/cos_strip
    longitude = Interval.point(longitude0)+Interval(-longitude_delta.high,longitude_delta.high)
    x,y = enclose_source_box((latitude.low,latitude.high),(longitude.low,longitude.high),projection)
    return x,y,latitude,longitude,radius,radius_squared
