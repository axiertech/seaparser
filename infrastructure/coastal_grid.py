"""Exact cached predicates for the existing world-anchored water search grid.

Only points and eight-neighbour edges use the lookup. Other segments retain
the original closed whole-geometry predicate. No I/O during route queries.
"""
import base64
from math import ceil,floor,isfinite
from pathlib import Path

import numpy as np
import shapely

from infrastructure.coastal_water import GUARD_M
from infrastructure.land import FRAME
from infrastructure.materialized_cache import MaterializedCache,fingerprint

ROOT=Path(__file__).resolve().parents[1]
DIRECTIONS=((1,0,2),(0,1,4),(1,1,8),(-1,1,16))
EDGE_MASKS={direction:(mask,reverse) for dx,dy,mask in DIRECTIONS
            for direction,reverse in (((dx,dy),False),((-dx,-dy),True))}


class CoastalGrid:
    def __init__(self,data):
        self.spacing=data['spacing_m'];self.margin=data['margin_m']
        self.imin,self.jmin=data['origin'];self.nx,self.ny=data['shape']
        if (type(self.spacing) not in (int,float) or not isfinite(self.spacing) or self.spacing<=0
                or type(self.margin) not in (int,float) or not isfinite(self.margin) or self.margin<0
                or any(type(v) is not int for v in (self.imin,self.jmin,self.nx,self.ny))
                or self.nx<=0 or self.ny<=0):
            raise ValueError('Invalid coastal predicate grid geometry')
        raw=base64.b64decode(data['flags'],validate=True)
        self.flags=np.frombuffer(raw,dtype=np.uint8)
        if (len(self.flags)!=self.nx*self.ny or np.any(self.flags&224)
                or self.nx<=0 or self.ny<=0):raise ValueError('Invalid coastal predicate grid')

    def lookup(self,a,b,margin_m):
        if margin_m!=self.margin:return None
        cells=[]
        for x,y in (a,b):
            i,j=round(x/self.spacing),round(y/self.spacing)
            if i*self.spacing!=x or j*self.spacing!=y:return None
            cells.append((i,j))
        a,b=cells
        return self.point_key_clear(a) if a==b else self.edge_key_clear(a,b)

    def _index(self,key):
        i,j=key[0]-self.imin,key[1]-self.jmin
        return j*self.nx+i if 0<=i<self.nx and 0<=j<self.ny else None

    def point_key_clear(self,key):
        index=self._index(key)
        return None if index is None else bool(self.flags[index]&1)

    def edge_key_clear(self,a,b):
        first,last=self._index(a),self._index(b)
        entry=EDGE_MASKS.get((b[0]-a[0],b[1]-a[1]))
        if first is None or last is None or entry is None:return None
        mask,reverse=entry
        return bool(self.flags[last if reverse else first]&mask)


def build_grid(water,*,spacing_m=250,margin_m=10,max_cells=1000000,chunk_cells=8192):
    if (type(spacing_m) not in (int,float) or not isfinite(spacing_m) or spacing_m<=0
            or type(margin_m) not in (int,float) or not isfinite(margin_m) or margin_m<0
            or any(type(v) is not int or v<=0 for v in (max_cells,chunk_cells))):
        raise ValueError('Finite coastal grid geometry and positive build budgets required')
    w,s,e,n=water.geometry.bounds
    imin,jmin,imax,jmax=ceil(w/spacing_m),ceil(s/spacing_m),floor(e/spacing_m),floor(n/spacing_m)
    nx,ny=imax-imin+1,jmax-jmin+1
    if nx<=0 or ny<=0 or nx*ny>max_cells:raise ValueError('Coastal grid build cell budget exceeded')
    flags=np.zeros(nx*ny,dtype=np.uint8)

    def coordinates(indices):
        return np.column_stack(((indices%nx+imin)*spacing_m,(indices//nx+jmin)*spacing_m))

    def clear(shapes):
        # Identical predicates, including the same closed micrometre guard.
        return water.clear_shapes(shapes,margin_m)

    for start in range(0,nx*ny,chunk_cells):
        indices=np.arange(start,min(start+chunk_cells,nx*ny))
        flags[indices]=clear(shapely.points(coordinates(indices)))
    for dx,dy,mask in DIRECTIONS:
        for start in range(0,nx*ny,chunk_cells):
            indices=np.arange(start,min(start+chunk_cells,nx*ny));x,y=indices%nx,indices//nx
            indices=indices[(x+dx>=0)&(x+dx<nx)&(y+dy>=0)&(y+dy<ny)]
            other=indices+dx+dy*nx
            indices=indices[((flags[indices]&1)!=0)&((flags[other]&1)!=0)]
            if not len(indices):continue
            other=indices+dx+dy*nx
            shapes=shapely.linestrings(np.stack((coordinates(indices),coordinates(other)),axis=1))
            flags[indices[clear(shapes)]]|=mask
    return {'spacing_m':spacing_m,'margin_m':margin_m,'origin':[imin,jmin],'shape':[nx,ny],
            'flags':base64.b64encode(flags.tobytes()).decode('ascii')}


def attach_grid(water,cache_directory,*,spacing_m=250,margin_m=10,diagnostics=None):
    files={name:ROOT/name for name in ('infrastructure/coastal_grid.py','infrastructure/coastal_water.py','requirements.lock')}
    identity={'kind':'exact-coastal-grid-v1','water_sha256':water.sha256,'projection':FRAME,
              'spacing_m':spacing_m,'margin_m':margin_m,'guard_m':GUARD_M,
              'geos':shapely.geos_version_string,'code':fingerprint(files),'max_cells':1000000}
    data,status=MaterializedCache(cache_directory).get_or_create(identity,
        lambda:build_grid(water,spacing_m=spacing_m,margin_m=margin_m))
    if data['spacing_m']!=spacing_m or data['margin_m']!=margin_m:raise ValueError('Coastal grid identity mismatch')
    grid=CoastalGrid(data);water.grids[margin_m]=grid
    if diagnostics is not None:diagnostics.setdefault('geometry_cache',{})[str(margin_m)]={'status':status,'cells':grid.nx*grid.ny}
    return grid
