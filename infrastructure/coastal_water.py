"""Materialized, immutable coastal water geometry. No I/O during route queries.

The existing WGS84-AEQD frame is retained. Source coastline is an estimated
barrier model, not proof of depth, navigability or source completeness.
"""
from hashlib import sha256
from math import isfinite
from dataclasses import dataclass
from functools import lru_cache

from shapely import from_wkb,LineString,Point,STRtree
from shapely.prepared import prep
from prototype.water_routing import generate_water_routes

GUARD_M=1e-6


@dataclass(frozen=True)
class WaterConnection:
    status: str
    points: tuple=()
    distance_m: float | None=None
    expansions: int=0
    spacing_m: float | None=None


class CoastalWater:
    def __init__(self,data,source_sha256):
        self.grids={}
        self.sha256=sha256(data).hexdigest();self.source_sha256=source_sha256
        self.geometry=from_wkb(data)
        if self.geometry.is_empty or not self.geometry.is_valid or self.geometry.geom_type not in ('Polygon','MultiPolygon'):
            raise ValueError('Valid materialized water polygons required')
        self.prepared=prep(self.geometry)
        components=list(self.geometry.geoms) if self.geometry.geom_type=='MultiPolygon' else [self.geometry]
        self.components=STRtree(components)
        self.prepared_components=tuple(prep(component) for component in components)
        boundary=self.geometry.boundary;parts=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
        # Short indexed pieces make exact closed margin checks local, rather
        # than rescanning every coastline vertex for every integration step.
        self.edges=[]
        for part in parts:
            coordinates=list(part.coords)
            for i in range(0,len(coordinates)-1,64):self.edges.append(LineString(coordinates[i:i+65]))
        self.edge_index=STRtree(self.edges)
        # Repeated reserve sources share component membership across queries;
        # the cache belongs only to this immutable water snapshot.
        self._component_ids=lru_cache(maxsize=16384)(self._component_ids)

    @staticmethod
    def coordinates(point):
        values=(float(point.east),float(point.north))
        if not all(isfinite(v) for v in values):raise ValueError('Finite coastal coordinates required')
        return values

    @lru_cache(maxsize=65536)
    def clear(self,start,end,margin_m=0):
        """Whole affine segment, including endpoints, excludes closed land/margin."""
        if type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0:raise ValueError('Finite nonnegative margin required')
        a,b=self.coordinates(start),self.coordinates(end)
        grid=self.grids.get(margin_m)
        if grid is not None:
            answer=grid.lookup(a,b,margin_m)
            if answer is not None:return answer
        shape=Point(a) if a==b else LineString((a,b))
        return bool(self.prepared.covers(shape) and not len(self.edge_index.query(shape,predicate='dwithin',distance=margin_m+GUARD_M)))

    def candidate_clear(self,start,end,margin_m=0):
        """Use local indexed distance checks, never buffer the entire coastline."""
        return self.clear(start,end,margin_m)

    def clear_shapes(self,shapes,margin_m):
        """Vector form of the same prepared covers and closed boundary query."""
        import numpy as np
        import shapely
        if type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0:raise ValueError('Finite nonnegative margin required')
        allowed=shapely.covers(self.geometry,shapes)
        supported=np.flatnonzero(allowed)
        if len(supported):
            hits=self.edge_index.query(shapes[supported],predicate='dwithin',distance=margin_m+GUARD_M)
            if hits.size:allowed[supported[hits[0]]]=False
        return allowed

    def clear_many(self,start,ends,margin_m=0):
        """Batch independent smoothing questions; no approximation or I/O."""
        import numpy as np
        import shapely
        if type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0:raise ValueError('Finite nonnegative margin required')
        a=self.coordinates(start);b=np.array([self.coordinates(p) for p in ends])
        if not len(b):return ()
        shapes=shapely.linestrings(np.stack((np.broadcast_to(a,b.shape),b),axis=1))
        same=np.all(b==a,axis=1)
        if np.any(same):shapes[same]=shapely.points(b[same])
        return tuple(bool(v) for v in self.clear_shapes(shapes,margin_m))

    def connection(self,start,end,*,max_distance_m,spacing_m=250,max_cells=30000,max_expansions=10000,margin_m=0):
        """Find a bounded, explicitly checked water path, never a land shortcut.

        All paths with length <= budget lie inside the midpoint-centred square
        with side length equal to that budget. Grid search may still be incomplete.
        """
        if type(max_distance_m) not in (int,float) or not isfinite(max_distance_m) or max_distance_m<0:
            raise ValueError('Finite nonnegative water distance budget required')
        if (type(spacing_m) not in (int,float) or not isfinite(spacing_m) or spacing_m<=0
                or any(type(v) is not int or v<=0 for v in (max_cells,max_expansions))):
            raise ValueError('Positive water connection search budgets required')
        if type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0:raise ValueError('Finite nonnegative water path margin required')
        self.coordinates(start);self.coordinates(end)
        if (end-start).speed>max_distance_m:return WaterConnection('distance_limit')
        if self.clear(start,end,margin_m):return WaterConnection('found',(start,end),(end-start).speed)
        if not self.clear(start,start,margin_m) or not self.clear(end,end,margin_m):return WaterConnection('endpoint_blocked')
        a=self._component_ids(start)
        b=self._component_ids(end)
        if not a.intersection(b):return WaterConnection('disconnected_water')
        middle=(start+end).scaled(.5);radius=max_distance_m/2
        bounds=(middle.east-radius,middle.north-radius,middle.east+radius,middle.north+radius)
        result=generate_water_routes(start,end,bounds,lambda a,b:self.clear(a,b,margin_m),
            point_clear=lambda p:self.clear(p,p,margin_m),clear_many=lambda p,ends:self.clear_many(p,ends,margin_m),spacing_m=spacing_m,max_cells=max_cells,
            max_expansions=max_expansions,max_candidates=1,max_waypoints=128)
        if not result.candidates:return WaterConnection(result.limit_reason or result.status,expansions=result.expansions,spacing_m=spacing_m)
        points=(start,*result.candidates[0].waypoints,end)
        distance=sum((b-a).speed for a,b in zip(points,points[1:]))
        if distance>max_distance_m:return WaterConnection('distance_limit',expansions=result.expansions,spacing_m=spacing_m)
        return WaterConnection('found',points,distance,result.expansions,spacing_m)

    def _component_ids(self,point):
        shape=Point(self.coordinates(point))
        # P.within(polygon) == polygon.contains(P). Preparing the large polygon
        # keeps the same strict boundary rule while avoiding a vertex scan.
        return frozenset(i for i in self.components.query(shape) if self.prepared_components[i].contains(shape))
