"""Materialized, immutable coastal water geometry. No I/O during route queries.

The existing WGS84-AEQD frame is retained. Source coastline is an estimated
barrier model, not proof of depth, navigability or source completeness.
"""
from hashlib import sha256
from math import isfinite

from shapely import from_wkb,LineString,Point,STRtree
from shapely.prepared import prep

GUARD_M=1e-6


class CoastalWater:
    def __init__(self,data,source_sha256):
        self.sha256=sha256(data).hexdigest();self.source_sha256=source_sha256
        self.geometry=from_wkb(data)
        if self.geometry.is_empty or not self.geometry.is_valid or self.geometry.geom_type not in ('Polygon','MultiPolygon'):
            raise ValueError('Valid materialized water polygons required')
        self.prepared=prep(self.geometry)
        boundary=self.geometry.boundary;parts=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
        # Short indexed pieces make exact closed margin checks local, rather
        # than rescanning every coastline vertex for every integration step.
        self.edges=[]
        for part in parts:
            coordinates=list(part.coords)
            for i in range(0,len(coordinates)-1,64):self.edges.append(LineString(coordinates[i:i+65]))
        self.edge_index=STRtree(self.edges)

    @staticmethod
    def coordinates(point):
        values=(float(point.east),float(point.north))
        if not all(isfinite(v) for v in values):raise ValueError('Finite coastal coordinates required')
        return values

    def clear(self,start,end,margin_m=0):
        """Whole affine segment, including endpoints, excludes closed land/margin."""
        if type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0:raise ValueError('Finite nonnegative margin required')
        a,b=self.coordinates(start),self.coordinates(end);shape=Point(a) if a==b else LineString((a,b))
        return bool(self.prepared.covers(shape) and not len(self.edge_index.query(shape,predicate='dwithin',distance=margin_m+GUARD_M)))

    def candidate_clear(self,start,end,margin_m=0):
        """Use local indexed distance checks, never buffer the entire coastline."""
        return self.clear(start,end,margin_m)
