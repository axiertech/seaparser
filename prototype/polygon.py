"""Closed simple polygons in local metres; exact predicates on stored numbers."""
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import isfinite
from .model import Vector


def xy(p):
    if not isinstance(p, Vector) or not all(isfinite(v) for v in (p.east, p.north)):
        raise ValueError('Finita lokala positioner krävs')
    return Fraction(p.east), Fraction(p.north)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on(a, b, p):
    return cross(a,b,p) == 0 and all(min(a[i],b[i]) <= p[i] <= max(a[i],b[i]) for i in (0,1))


def meets(a, b, c, d):
    if any((on(a,b,c), on(a,b,d), on(c,d,a), on(c,d,b))):
        return True
    return (cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0)


def distance_squared(p, a, b):
    delta = (b[0]-a[0], b[1]-a[1])
    length = delta[0]**2+delta[1]**2
    if length == 0:
        return (p[0]-a[0])**2+(p[1]-a[1])**2
    t = max(Fraction(0), min(Fraction(1), ((p[0]-a[0])*delta[0]+(p[1]-a[1])*delta[1])/length))
    return sum((p[i]-a[i]-t*delta[i])**2 for i in (0,1))


def inside(p, vertices):
    result = False
    for a,b in zip(vertices, vertices[1:]+vertices[:1]):
        if on(a,b,p):
            return True
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if p[0] < x:
                result = not result
    return result


@lru_cache(maxsize=256)
def exact_geometry(vertices):
    """Bounded cache of immutable source coordinates; never caches a verdict."""
    points = tuple(xy(p) for p in vertices)
    bounds = tuple((min(p[i] for p in points),max(p[i] for p in points)) for i in (0,1))
    return points,bounds


@dataclass(frozen=True)
class Polygon:
    name: str
    vertices: tuple[Vector, ...]
    margin_m: float = 0
    kind: str = 'land'
    source: str = 'SeaParser synthetic estimated fixture'
    version: str = '1'
    quality: str = 'estimated'
    restriction: str = 'hard'

    def __post_init__(self):
        vertices = tuple(self.vertices)
        if not 3 <= len(vertices) <= 128 or not isfinite(self.margin_m) or self.margin_m < 0:
            raise ValueError('Polygon kräver 3–128 hörn och icke-negativ marginal')
        if (not all(isinstance(s,str) and s.strip() for s in (self.name,self.source,self.version))
                or self.kind not in ('land','island','shoal','depth_area','restriction')
                or self.quality not in ('estimated','verified','unknown')
                or self.restriction not in ('hard','information')):
            raise ValueError('Ogiltiga hindermetadata')
        v = tuple(xy(p) for p in vertices)
        if len(set(v)) != len(v) or sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(v,v[1:]+v[:1])) == 0:
            raise ValueError('Degenererad polygon')
        edges = tuple(zip(v,v[1:]+v[:1]))
        for i,(a,b) in enumerate(edges):
            if cross(v[i-1],a,b) == 0:
                raise ValueError('Kollineära intilliggande kanter stöds inte')
            for j,(c,d) in enumerate(edges):
                if j > i+1 and not (i == 0 and j == len(v)-1) and meets(a,b,c,d):
                    raise ValueError('Självkorsande polygon stöds inte')
        object.__setattr__(self,'vertices',vertices)

    def intersects(self, start, end):
        a,b = xy(start),xy(end)
        if self.restriction == 'information':
            return False
        vertices,bounds = exact_geometry(self.vertices)
        # Exact broad phase: a Euclidean margin is contained in this expanded
        # axis-aligned box. Strict separation proves no contact; equality must
        # continue to the closed-edge and exact-distance predicates below.
        margin = Fraction(self.margin_m)
        if any(max(a[i],b[i]) < bounds[i][0]-margin or
               min(a[i],b[i]) > bounds[i][1]+margin for i in (0,1)):
            return False
        if inside(a,vertices) or inside(b,vertices):
            return True
        margin2 = Fraction(self.margin_m)**2
        for c,d in zip(vertices,vertices[1:]+vertices[:1]):
            if meets(a,b,c,d) or min(distance_squared(a,c,d),distance_squared(b,c,d),
                                   distance_squared(c,a,b),distance_squared(d,a,b)) <= margin2:
                return True
        return False
