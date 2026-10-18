"""Generate geometry once, then evaluate full routes at every frozen departure."""
from dataclasses import asdict, replace
import json
from prototype.auto_routing import generate_routes, SearchPolicy
from .planning import canonical, digest, run_plan


def run_obstacle_plan(request, policy=SearchPolicy(), *, node_radius_m=None):
    search = generate_routes(request.position,request.target,request.obstacles,policy,node_radius_m=node_radius_m)
    plan = None
    if search.candidates:
        plan = json.loads(run_plan(replace(request,candidates=search.candidates)))
    search_data=asdict(search)
    # Preserve the serialized identity of frozen legacy 64-obstacle references.
    # Non-default configured obstacle budgets are always explicit in new reports.
    if policy.max_obstacles==64:search_data['policy'].pop('max_obstacles')
    if node_radius_m is not None:
        search_data['node_domain']={'origin_m':[0,0],'radius_m':node_radius_m,'membership':'exact_squared_coordinates',
                                    'obstacles_removed':False}
    identity = {'geometry_algorithm':'polygon-box-visibility-simple-paths-astar-v2',
                'search':search_data,'request':asdict(request)}
    return canonical({'geometry_algorithm':identity['geometry_algorithm'],
                      'geometry_search':search_data,'planning':plan,
                      'input_sha256':digest(identity),
                      'limitations':'Ingen verifierad grafkandidat är inte bevis för att ingen möjlig rutt finns.'})
