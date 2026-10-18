"""Bounded water-grid candidates; geometry is supplied as pure callbacks.

No I/O, forecast substitution or claim of global weather optimality. Every
candidate edge is checked against the same closed land/margin model.
"""
from dataclasses import dataclass
from heapq import heappop,heappush
from math import ceil,floor,hypot,isfinite
from .model import Vector
from .routes import RouteCandidate


@dataclass(frozen=True)
class WaterRoutes:
    status: str
    candidates: tuple
    expansions: int
    node_count: int
    truncated: bool
    limit_reason: str
    spacing_m: float
    scope: str='Bounded water-grid geometry candidates; actual voyages evaluated separately. No global optimum claim.'


def generate_water_routes(start,target,bounds,clear,*,point_clear=None,clear_many=None,grid_point_clear=None,grid_edge_clear=None,spacing_m=125,max_cells=1000000,max_expansions=300000,max_candidates=3,max_waypoints=256):
    if len(bounds)!=4 or not all(isfinite(v) for v in (*bounds,start.east,start.north,target.east,target.north,spacing_m)) or spacing_m<=0:
        raise ValueError('Finite regional bounds/spacing required')
    if any(type(v) is not int or v<=0 for v in (max_cells,max_expansions,max_candidates,max_waypoints)):raise ValueError('Positive water-grid budgets required')
    w,s,e,n=bounds
    if not w<e or not s<n:raise ValueError('Ordered regional bounds required')
    if any(not w<=p.east<=e or not s<=p.north<=n for p in (start,target)):
        raise ValueError('Endpoints must lie within the configured regional search bounds')
    imin,imax,jmin,jmax=ceil(w/spacing_m),floor(e/spacing_m),ceil(s/spacing_m),floor(n/spacing_m)
    if (imax-imin+1)*(jmax-jmin+1)>max_cells:return WaterRoutes('grid_limit',(),0,0,True,'max_cells',spacing_m)
    if not clear(start,start) or not clear(target,target):return WaterRoutes('endpoint_blocked',(),0,0,False,'',spacing_m)
    allowed=point_clear or (lambda p:clear(p,p));points={};edges={};coordinates={}
    def point(key):
        if key not in coordinates:coordinates[key]=Vector(key[0]*spacing_m,key[1]*spacing_m)
        return coordinates[key]
    def supported(key):
        if not imin<=key[0]<=imax or not jmin<=key[1]<=jmax:return False
        if key not in points:
            answer=grid_point_clear(key) if grid_point_clear is not None else None
            points[key]=bool(allowed(point(key)) if answer is None else answer)
        return points[key]
    def edge(a,b):
        key=tuple(sorted((a,b)))
        if key not in edges:
            answer=grid_edge_clear(a,b) if grid_edge_clear is not None else None
            edges[key]=bool(clear(point(a),point(b)) if answer is None else answer)
        return edges[key]
    def anchors(p):
        i,j=round(p.east/spacing_m),round(p.north/spacing_m)
        keys=tuple((x,y) for x in range(i-3,i+4) for y in range(j-3,j+4) if supported((x,y)))
        if clear_many is None:return tuple(key for key in keys if clear(p,point(key)))
        answers=clear_many(p,tuple(point(key) for key in keys))
        if len(answers)!=len(keys):raise ValueError('One geometry answer per endpoint anchor required')
        return tuple(key for key,answer in zip(keys,answers) if answer)
    first,last=anchors(start),set(anchors(target))
    if not first or not last:return WaterRoutes('no_endpoint_connection',(),0,len(points),False,'grid_resolution_or_margin',spacing_m)
    penalties=set();routes=[];expansions=0;reason='';seen=set()
    for attempt in range(max_candidates):
        queue=[];cost={};previous={};end=None
        for key in first:
            g=(point(key)-start).speed;cost[key]=g;heappush(queue,(g+(target-point(key)).speed,g,key))
        while queue and expansions<max_expansions:
            _,g,key=heappop(queue)
            if g!=cost.get(key):continue
            expansions+=1
            if key in last:end=key;break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                nxt=(key[0]+dx,key[1]+dy)
                if not supported(nxt) or not edge(key,nxt):continue
                distance=spacing_m*hypot(dx,dy);new=g+distance*(1.8 if nxt in penalties else 1)
                if new<cost.get(nxt,float('inf')):
                    cost[nxt]=new;previous[nxt]=key;heappush(queue,(new+(target-point(nxt)).speed,new,nxt))
        if end is None:
            reason='max_expansions' if queue else 'no_grid_path';break
        keys=[end]
        while keys[-1] in previous:keys.append(previous[keys[-1]])
        keys.reverse();path=[start,*[point(key) for key in keys],target]
        # Keep one anchor on later candidates, so line-of-sight smoothing does
        # not silently erase the deliberate geometric alternative.
        anchor=None
        if attempt:
            direction=target-start;length=max(direction.speed,1e-12)
            anchor=max(range(1,len(path)-1),key=lambda i:abs(direction.east*(path[i].north-start.north)-direction.north*(path[i].east-start.east))/length)
        smooth=[start];i=0
        while i<len(path)-1:
            end_index=anchor if anchor is not None and i<anchor else len(path)-1
            if clear_many is None:
                j=end_index
                while j>i+1 and not clear(path[i],path[j]):j-=1
            elif clear(path[i],path[end_index]):
                j=end_index
            else:
                j=None
                for high in range(end_index-1,i,-16):
                    indices=tuple(range(high,max(i,high-16),-1))
                    answers=clear_many(path[i],tuple(path[k] for k in indices))
                    if len(answers)!=len(indices):raise ValueError('One geometry answer per candidate segment required')
                    j=next((k for k,answer in zip(indices,answers) if answer),None)
                    if j is not None:break
                if j is None:raise ValueError('Generated edge lost closed land support')
            if not clear(path[i],path[j]):raise ValueError('Generated edge lost closed land support')
            if path[j]!=smooth[-1]:smooth.append(path[j])
            i=j
        waypoints=tuple(smooth[1:-1]);identity=tuple((p.east,p.north) for p in waypoints)
        if len(waypoints)>max_waypoints:reason='max_waypoints';break
        if identity not in seen:routes.append(RouteCandidate(f'water-{len(routes)}',waypoints));seen.add(identity)
        for x,y in keys:
            for dx in range(-2,3):
                for dy in range(-2,3):penalties.add((x+dx,y+dy))
    # Repeated smoothing can collapse several attempts to the same candidate;
    # exhausting attempts is still a search limit even with fewer unique routes.
    reason=reason or 'max_candidates'
    truncated=reason in ('max_expansions','max_waypoints','max_candidates')
    return WaterRoutes('candidates' if routes else reason,tuple(routes),expansions,len(points),truncated,reason,spacing_m)
