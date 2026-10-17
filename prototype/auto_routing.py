"""Bounded simple paths on an explicit visibility graph, not weather optimization."""
from dataclasses import dataclass
from heapq import heappop, heappush
from math import isfinite
from .model import Vector
from .polygon import Polygon, xy
from .routes import RouteCandidate

SCOPE = ('Endast enkla vägar i grafen av start/mål och utvidgade polygonboxhörn. '
         'A* med euklidiskt kvaravstånd ordnar geometrisk längd, inte väderrestid. Ingen global optimalitet; '
         'inga tidsberoende tillstånd slås ihop. Ingen automatisk kryss eller väntan.')


@dataclass(frozen=True)
class SearchPolicy:
    clearance_m: float = 1
    max_candidates: int = 32
    max_waypoints: int = 8
    max_expansions: int = 10000
    max_nodes: int = 66

    def __post_init__(self):
        if not isfinite(self.clearance_m) or self.clearance_m <= 0:
            raise ValueError('Positiv finit hörnklarering krävs utöver hindermarginal')
        if any(type(v) is not int or v <= 0 for v in
               (self.max_candidates,self.max_waypoints,self.max_expansions,self.max_nodes)):
            raise ValueError('Positiva heltal krävs för sökgränser')
        if self.max_nodes > 258 or self.max_candidates > 100 or self.max_waypoints > 32 or self.max_expansions > 100000:
            raise ValueError('Sökgränser över prototypens hårda budget')


@dataclass(frozen=True)
class GeneratedRoutes:
    status: str
    candidates: tuple[RouteCandidate, ...]
    lengths_m: tuple[float, ...]
    expansions: int
    node_count: int
    truncated: bool
    policy: SearchPolicy
    limit_reason: str = ''
    scope: str = SCOPE


def generate_routes(position, target, obstacles, policy=SearchPolicy()):
    xy(position); xy(target)
    if type(policy) is not SearchPolicy or policy.max_nodes < 2:
        raise ValueError('Fryst sökpolicy med minst två noder krävs')
    items = []
    for obstacle in obstacles:
        if len(items) >= 64 or type(obstacle) is not Polygon:
            raise ValueError('Högst 64 syntetiska polygoner stöds')
        items.append(obstacle)
    obstacles = tuple(items)
    hard = tuple(o for o in obstacles if o.restriction == 'hard')
    if any(o.intersects(p,p) for o in hard for p in (position,target)):
        return GeneratedRoutes('endpoint_blocked',(),(),0,2,False,policy)
    nodes = [position,target]
    for obstacle in hard:
        xs = [p.east for p in obstacle.vertices]; ys = [p.north for p in obstacle.vertices]
        padding = obstacle.margin_m+policy.clearance_m
        for x,y in ((min(xs)-padding,min(ys)-padding),(min(xs)-padding,max(ys)+padding),
                    (max(xs)+padding,min(ys)-padding),(max(xs)+padding,max(ys)+padding)):
            point = Vector(x,y); xy(point)
            if point not in nodes and not any(o.intersects(point,point) for o in hard):
                nodes.append(point)
                if len(nodes) > policy.max_nodes:
                    return GeneratedRoutes('node_limit',(),(),0,len(nodes),True,policy,limit_reason='max_nodes')
    graph = [[] for _ in nodes]
    for i,a in enumerate(nodes):
        for j in range(i+1,len(nodes)):
            b = nodes[j]
            if not any(o.intersects(a,b) for o in hard):
                length = (b-a).speed
                if not isfinite(length):
                    raise ValueError('Geometrisk längd utanför numeriskt stöd')
                graph[i].append((j,length)); graph[j].append((i,length))
    queue = [((target-position).speed,(0,),0.0)]; candidates=[]; lengths=[]; expansions=0; depth_cut=False
    while queue and expansions < policy.max_expansions and len(candidates) < policy.max_candidates:
        _,path,length = heappop(queue); expansions += 1
        if path[-1] == 1:
            candidates.append(RouteCandidate('auto-'+str(len(candidates)),tuple(nodes[i] for i in path[1:-1])))
            lengths.append(length)
            continue
        for next_node,distance in graph[path[-1]]:
            if next_node in path:
                continue
            if next_node != 1 and len(path)-1 >= policy.max_waypoints:
                depth_cut=True
                continue
            new_length=length+distance
            if not isfinite(new_length):
                raise ValueError('Geometrisk längd utanför numeriskt stöd')
            heappush(queue,(new_length+(target-nodes[next_node]).speed,(*path,next_node),new_length))
            # Memory is bounded independently of how many entries have been popped.
            if len(queue) >= policy.max_expansions:
                return GeneratedRoutes('search_limit',tuple(candidates),tuple(lengths),expansions,len(nodes),True,policy,limit_reason='queue_budget')
    truncated = bool(queue) or depth_cut
    status = 'candidates_found' if candidates else 'no_graph_path'
    if truncated:
        status = 'search_limit'
    limits = []
    if queue:
        limits.append('max_candidates' if len(candidates) >= policy.max_candidates else 'max_expansions')
    if depth_cut:
        limits.append('max_waypoints')
    return GeneratedRoutes(status,tuple(candidates),tuple(lengths),expansions,len(nodes),truncated,policy,limit_reason=','.join(limits))
