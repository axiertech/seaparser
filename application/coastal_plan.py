"""Coastal composition of existing normalization and voyage engine, offline only."""
from dataclasses import asdict,replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from infrastructure.coastal_water import CoastalWater
from infrastructure.coastal_grid import attach_grid
from infrastructure.coastal_forecast import CoastalForecast,CoastalObstacle
from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from infrastructure.marine_reserve import NativeWindWithReserve,configured_reserve_policies
from infrastructure.land import FORWARD
from infrastructure.land import FRAME
from prototype.forecast_metadata import ProductMetadata
from prototype.forecast import ForecastPolicy,FixedClock,utc_time
from prototype.model import Vector,ConstantBoat
from prototype.routes import RouteCandidate,compare_routes
from prototype.weather import WeatherPolicy
from prototype.presentation import route_comparison_data
from application.coastal_inputs import coastal_inputs
from application.development_weather import REQUIRED
from application.planning import canonical,digest
from application.poc import route_metrics
from application.geographic_budget import resource_budget,available_voyage_seconds

ROOT=Path(__file__).resolve().parents[1]


def load_coastal_weather(directory,*,policy=None,margin_m=10,cache_directory=None,diagnostics=None):
    directory=Path(directory);request=json.loads((directory/'request.json').read_text())
    profile=request.get('case')
    config_name={'vinga-uddevalla':'coastal-weather-assumptions.json','trelleborg-stromstad':'trelleborg-weather-assumptions.json'}.get(profile)
    if config_name is None:raise ValueError('Unknown source-bound coastal profile')
    config=json.loads((ROOT/'settings'/config_name).read_text())
    if (config['mode']!='coastal_development_estimates' or config['source_bundle']!=directory.name
            or set(config['source_assumptions'])!=REQUIRED or any(not isinstance(v,str) or not v.strip() for v in config['source_assumptions'].values())):
        raise ValueError('Explicit source-bound coastal assumptions required')
    radius={'vinga-uddevalla':120000,'trelleborg-stromstad':350000}[profile]
    if config['motion_radius_m']!=radius:raise ValueError('Source-bound motion radius required')
    if config['model_assumptions']!={'native_coordinate_enclosure':'Coastal AEQD-to-MET coordinate mapping assumed 2-Lipschitz within '+str(radius//1000)+' km, with 2 m guard; numerical development assumption, not source qualification.'}:
        raise ValueError('Explicit regional coordinate enclosure assumption required')
    reserve_config=json.loads((ROOT/'settings/vinga-uddevalla-reserve.json').read_text())
    if profile=='trelleborg-stromstad':
        for fields in reserve_config['products'].values():
            for entry in fields.values():entry['water_path_spacing_m']=500
    policies=configured_reserve_policies(reserve_config)
    land=json.loads((directory/'land/water.json').read_text());data=(directory/'land/water.wkb').read_bytes()
    coast=directory/'land/coastline.osm';source_index=json.loads((directory/'land/sources.json').read_text())['coastline.osm']
    if (sha256(data).hexdigest()!=land['water_sha256'] or land['projection']!=FRAME
            or sha256(coast.read_bytes()).hexdigest()!=land['source_sha256'] or source_index['sha256']!=land['source_sha256']):
        raise ValueError('Coastal water/source snapshot changed')
    water=CoastalWater(data,land['source_sha256'])
    if cache_directory is not None:
        margins={0,margin_m}
        for product in policies.values():margins.add(max(p.water_path_margin_m for p in product.values()))
        for margin in sorted(margins):attach_grid(water,cache_directory,spacing_m=500 if profile=="trelleborg-stromstad" else 250,margin_m=margin,diagnostics=diagnostics)
    sample,payload,audit=coastal_inputs(directory,request,cache_directory=cache_directory,diagnostics=diagnostics)
    current,waves=CopernicusMarineAdapter().normalize_coastal(payload,water,policies,bounds=config['source_bounds'])
    marine_source_hashes={k:v['source_sha256'] for k,v in payload['products'].items()}
    del payload # normalized products own their immutable numeric arrays
    wind=NativeWindWithReserve(sample,water,policies['wind'])
    issued=datetime.fromisoformat(config['assumed_issued_at'].replace('Z','+00:00'))
    wm=ProductMetadata('wind','MET-Nordic-coastal-frozen',request['reference_time'] if profile=='trelleborg-stromstad' else '20261018','MET Nordic original native wind',None,
        sample.times[0],sample.times[-1],current.metadata.coverage,('m/s','m/s'),'ground-to-true-east-north',
        source_sha256=digest(dict(sample.source_hashes)) if profile=='trelleborg-stromstad' else dict(sample.source_hashes)['wind.txt'],planning_blockers=tuple(sorted(REQUIRED)))
    raw=(wm,current.metadata,waves.metadata)
    if any(not set(m.planning_blockers)<=REQUIRED for m in raw):raise ValueError('New coastal source blocker requires explicit assumption')
    metadata=tuple(replace(m,issued_at=issued,planning_blockers=(),assumed_fields=('issued_at',*sorted(REQUIRED))) for m in raw)
    selected=policy or WeatherPolicy(config['max_wind_m_s'],config['max_wave_height_m'])
    environment=CoastalForecast(wind,current,waves,metadata,water,selected,margin_m=margin_m,radius_m=config['motion_radius_m'],profile=profile)
    evidence={'source_metadata':[asdict(m) for m in raw],'wind_source_hashes':dict(sample.source_hashes),
        'marine_source_hashes':marine_source_hashes,
        'source_qualification':'unverified','source_assumptions':config['source_assumptions'],
        'model_assumptions':config['model_assumptions'],'assumed_issued_at':config['assumed_issued_at'],
        'reserve_policies':reserve_config,'water':land,'data_audit':audit}
    return environment,config,evidence,request


def simulate_coastal_candidate(directory,candidate_file,*,departure=None,policy=None,timings=None,cache_directory=None):
    from time import monotonic
    mark=monotonic()
    environment,config,evidence,request=load_coastal_weather(directory,policy=policy,cache_directory=cache_directory,diagnostics=timings)
    if timings is not None:timings['load_seconds']=monotonic()-mark
    saved=json.loads(Path(candidate_file).read_text())
    if saved['water_sha256']!=environment.water.sha256:raise ValueError('Candidate uses another coastal water snapshot')
    start=Vector(*FORWARD.transform(request['start']['longitude'],request['start']['latitude']))
    target=Vector(*FORWARD.transform(request['target']['longitude'],request['target']['latitude']))
    candidates=tuple(RouteCandidate(c['name'],tuple(Vector(p['east'],p['north']) if isinstance(p,dict) else Vector(*p) for p in c['waypoints'])) for c in saved.get('candidates',saved.get('search',{}).get('candidates',[])))
    when=datetime.fromisoformat((departure or request['departure']).replace('Z','+00:00'))
    return _simulate(environment,config,evidence,request,start,target,candidates,when,saved,timings)


def _simulate(environment,config,evidence,request,start,target,candidates,when,saved,timings):
    from time import monotonic
    resources=resource_budget('regional')
    mark=monotonic()
    result=compare_routes(environment,when,target,candidates,position=start,boat=ConstantBoat(5),
        obstacles=(CoastalObstacle(environment.water,environment.margin_m),),weather_policy=environment.policy,
        forecast_policy=ForecastPolicy(config['max_age_seconds']),clock=FixedClock(datetime.fromisoformat(config['planning_time'].replace('Z','+00:00'))),
        max_seconds=available_voyage_seconds(resources,when,(0,),environment.end),step_seconds=resources['step_seconds'],
        max_steps=resources['max_steps'],max_waypoints=resources['max_waypoints'],max_candidates=8) if candidates else None
    if timings is not None:timings['engine_seconds']=monotonic()-mark
    mark=monotonic();report=route_comparison_data(result) if result else {
        'status':'not_simulated','candidates':[],'fastest_candidate':None,'comfortable_candidate':None,
        'reason':'No complete geometric candidate found within the bounded search'}
    segments=[]
    for row in report['candidates']:row.update(route_metrics(row))
    for route in result.candidates if result else ():
        for leg_index,leg in enumerate(route.legs):
            for index,step in enumerate(leg.steps):
                points=[]
                for p,t in ((step.start.position,step.start.time),(step.midpoint.position,step.midpoint.time),(step.end_position,step.end_time)):
                    records=environment.samples(p,t)[3]
                    estimates=[]
                    for record in records:
                        row=asdict(record)
                        row['source_time']=record.source_time.isoformat()
                        row['connection_waypoints']=[list(p) for p in record.connection_waypoints]
                        estimates.append(row)
                    points.append({'position':asdict(p),'time':t.isoformat(),'estimates':estimates})
                segments.append({'candidate':route.candidate.name,'leg':leg_index,'step':index,'samples':points})
    if timings is not None:timings['presentation_seconds']=monotonic()-mark
    # Normalize only the small metadata. The large report/segment tree is
    # already JSON-native; serializing and reparsing it here duplicates the
    # entire result while the voyage engine's objects are still alive.
    details=json.loads(canonical({'provenance':evidence,'configuration':config,
        'source_value_bounds':{'wind_abs_components_m_s':environment.wind_components,'wave_height_m':environment.wave_height_bound}}))
    return {'profile':request['case'],'result_qualification':'estimated_high_uncertainty',
        'weather_limits_verified':False,'comparison':report,'estimated_segments':segments,
        **details,'land_margin_m':environment.margin_m,'input_sha256':digest({'candidate':saved,'config':config,'provenance':evidence,
        'departure':when,'request':request,'selected_weather_limits':asdict(environment.policy),'boat':asdict(ConstantBoat(5)),
        'algorithm':environment.version,'resources':resources,'land_margin_m':environment.margin_m})}


def plan_coastal(directory,payload,*,cache_directory=None,timings=None):
    """Search free regional points, then simulate every complete candidate.

    Offline composition; transport and process timeouts belong to the caller.
    Search budgets are versioned server settings, never client overrides.
    """
    from math import isfinite
    from time import monotonic
    from prototype.water_routing import generate_water_routes
    allowed={'start','target','departure','candidate_limit','boat_profile','max_wind_m_s','max_wave_height_m'}
    if not isinstance(payload,dict) or set(payload)-allowed or not {'start','target','departure'}<=set(payload):
        raise ValueError('Explicit regional endpoints and departure required; unknown options rejected')
    if payload.get('boat_profile','constant-5kn')!='constant-5kn':raise ValueError('Only the existing estimated 5 kn boat is supported')
    def position(value):
        if (not isinstance(value,dict) or set(value)!={'longitude','latitude'}
                or any(type(v) not in (int,float) or not isfinite(v) for v in value.values())
                or not -180<=value['longitude']<=180 or not -90<=value['latitude']<=90):
            raise ValueError('Finite WGS84 longitude/latitude endpoints required')
        return Vector(*FORWARD.transform(value['longitude'],value['latitude'],errcheck=True))
    start,target=position(payload['start']),position(payload['target'])
    if (target-start).speed<=.01:raise ValueError('Distinct regional endpoints required')
    if not isinstance(payload['departure'],str):raise ValueError('Explicit timezone-aware regional departure required')
    when=utc_time(datetime.fromisoformat(payload['departure'].replace('Z','+00:00')),'Regional departure')
    search_policy=json.loads((ROOT/'settings/coastal-search.json').read_text())
    names={'spacing_m','max_cells','max_expansions','max_candidates','max_waypoints','margin_m'}
    if (set(search_policy)!=names or any(type(v) is not int or v<=0 for v in search_policy.values())
            or search_policy['max_candidates']>8):raise ValueError('Explicit bounded coastal search settings required')
    count=payload.get('candidate_limit',search_policy['max_candidates'])
    if type(count) is not int or not 1<=count<=search_policy['max_candidates']:raise ValueError('Regional candidate budget exceeded')
    for name in ('max_wind_m_s','max_wave_height_m'):
        if name in payload and (type(payload[name]) not in (int,float) or not isfinite(payload[name]) or payload[name]<0):
            raise ValueError('Finite nonnegative selected weather limits required')
    mark=monotonic()
    environment,config,evidence,request=load_coastal_weather(directory,margin_m=search_policy['margin_m'],
        cache_directory=cache_directory,diagnostics=timings)
    if timings is not None:timings['load_seconds']=monotonic()-mark
    if not environment.start<=when<environment.end:raise ValueError('Departure outside frozen common coastal validity')
    environment.frame.matrix(start);environment.frame.matrix(target)
    environment.policy=WeatherPolicy(payload.get('max_wind_m_s',environment.policy.max_wind_m_s),
                                     payload.get('max_wave_height_m',environment.policy.max_wave_height_m))
    request={**request,'start':payload['start'],'target':payload['target'],'departure':when.isoformat()}
    resources=resource_budget('regional')
    if search_policy['max_waypoints']>resources['max_waypoints'] or search_policy['max_expansions']>resources['max_expansions']:
        raise ValueError('Coastal search exceeds regional resource budgets')
    mark=monotonic();water=environment.water;margin=environment.margin_m
    search=generate_water_routes(start,target,water.geometry.bounds,lambda a,b:water.clear(a,b,margin),
        point_clear=lambda p:water.clear(p,p,margin),clear_many=lambda p,ends:water.clear_many(p,ends,margin),
        **{k:v for k,v in search_policy.items() if k!='margin_m' and k!='max_candidates'},max_candidates=count,
        **water.grid_callbacks(search_policy['spacing_m'],margin))
    if timings is not None:timings['search_seconds']=monotonic()-mark
    search_view=json.loads(canonical(asdict(search)))
    saved={'water_sha256':water.sha256,'search_policy':search_policy,'geometry_search':search_view}
    result=_simulate(environment,config,evidence,request,start,target,search.candidates,when,saved,timings)
    result['geometry_search']=search_view
    result['search_budget']={**search_policy,'requested_candidates':count,'job_seconds':resources['job_seconds'],
                             'result_bytes':resources['result_bytes']}
    return result
