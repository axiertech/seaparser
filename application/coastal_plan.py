"""Coastal composition of existing normalization and voyage engine, offline only."""
from dataclasses import asdict,replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from infrastructure.coastal_water import CoastalWater
from infrastructure.coastal_forecast import CoastalForecast,CoastalObstacle
from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from infrastructure.marine_reserve import NativeWindWithReserve,configured_reserve_policies
from infrastructure.land import FORWARD
from infrastructure.land import FRAME
from prototype.forecast_metadata import ProductMetadata
from prototype.forecast import ForecastPolicy,FixedClock
from prototype.model import Vector,ConstantBoat
from prototype.routes import RouteCandidate,compare_routes
from prototype.weather import WeatherPolicy
from prototype.presentation import export_route_comparison
from application.coastal_inputs import coastal_inputs
from application.development_weather import REQUIRED
from application.planning import canonical,digest
from application.poc import route_metrics
from application.geographic_budget import resource_budget,available_voyage_seconds

ROOT=Path(__file__).resolve().parents[1]


def load_coastal_weather(directory,*,policy=None,margin_m=10,cache_directory=None,diagnostics=None):
    directory=Path(directory);request=json.loads((directory/'request.json').read_text())
    config=json.loads((ROOT/'settings/coastal-weather-assumptions.json').read_text())
    if (config['mode']!='coastal_development_estimates' or config['source_bundle']!=directory.name
            or set(config['source_assumptions'])!=REQUIRED or any(not isinstance(v,str) or not v.strip() for v in config['source_assumptions'].values())):
        raise ValueError('Explicit source-bound coastal assumptions required')
    if config['model_assumptions']!={'native_coordinate_enclosure':'Coastal AEQD-to-MET coordinate mapping assumed 2-Lipschitz within 120 km, with 2 m guard; numerical development assumption, not source qualification.'}:
        raise ValueError('Explicit regional coordinate enclosure assumption required')
    reserve_config=json.loads((ROOT/'settings/vinga-uddevalla-reserve.json').read_text());policies=configured_reserve_policies(reserve_config)
    land=json.loads((directory/'land/water.json').read_text());data=(directory/'land/water.wkb').read_bytes()
    coast=directory/'land/coastline.osm';source_index=json.loads((directory/'land/sources.json').read_text())['coastline.osm']
    if (sha256(data).hexdigest()!=land['water_sha256'] or land['projection']!=FRAME
            or sha256(coast.read_bytes()).hexdigest()!=land['source_sha256'] or source_index['sha256']!=land['source_sha256']):
        raise ValueError('Coastal water/source snapshot changed')
    water=CoastalWater(data,land['source_sha256'])
    sample,payload,audit=coastal_inputs(directory,request,cache_directory=cache_directory,diagnostics=diagnostics)
    current,waves=CopernicusMarineAdapter().normalize_coastal(payload,water,policies,bounds=config['source_bounds'])
    wind=NativeWindWithReserve(sample,water,policies['wind'])
    issued=datetime.fromisoformat(config['assumed_issued_at'].replace('Z','+00:00'))
    wm=ProductMetadata('wind','MET-Nordic-coastal-frozen','20261018','MET Nordic original native wind',None,
        sample.times[0],sample.times[-1],current.metadata.coverage,('m/s','m/s'),'ground-to-true-east-north',
        source_sha256=dict(sample.source_hashes)['wind.txt'],planning_blockers=tuple(sorted(REQUIRED)))
    raw=(wm,current.metadata,waves.metadata)
    if any(not set(m.planning_blockers)<=REQUIRED for m in raw):raise ValueError('New coastal source blocker requires explicit assumption')
    metadata=tuple(replace(m,issued_at=issued,planning_blockers=(),assumed_fields=('issued_at',*sorted(REQUIRED))) for m in raw)
    selected=policy or WeatherPolicy(config['max_wind_m_s'],config['max_wave_height_m'])
    environment=CoastalForecast(wind,current,waves,metadata,water,selected,margin_m=margin_m,radius_m=config['motion_radius_m'])
    evidence={'source_metadata':[asdict(m) for m in raw],'wind_source_hashes':dict(sample.source_hashes),
        'marine_source_hashes':{k:v['source_sha256'] for k,v in payload['products'].items()},
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
    candidates=tuple(RouteCandidate(c['name'],tuple(Vector(*p) for p in c['waypoints'])) for c in saved['candidates'])
    when=datetime.fromisoformat((departure or request['departure']).replace('Z','+00:00'))
    resources=resource_budget('regional')
    mark=monotonic()
    result=compare_routes(environment,when,target,candidates,position=start,boat=ConstantBoat(5),
        obstacles=(CoastalObstacle(environment.water,10),),weather_policy=environment.policy,
        forecast_policy=ForecastPolicy(config['max_age_seconds']),clock=FixedClock(datetime.fromisoformat(config['planning_time'].replace('Z','+00:00'))),
        max_seconds=available_voyage_seconds(resources,when,(0,),environment.end),step_seconds=resources['step_seconds'],
        max_steps=resources['max_steps'],max_waypoints=resources['max_waypoints'],max_candidates=8)
    if timings is not None:timings['engine_seconds']=monotonic()-mark
    mark=monotonic();report=json.loads(export_route_comparison(result));segments=[]
    for row in report['candidates']:row.update(route_metrics(row))
    for route in result.candidates:
        for leg_index,leg in enumerate(route.legs):
            for index,step in enumerate(leg.steps):
                points=[]
                for p,t in ((step.start.position,step.start.time),(step.midpoint.position,step.midpoint.time),(step.end_position,step.end_time)):
                    records=environment.samples(p,t)[3]
                    points.append({'position':asdict(p),'time':t,'estimates':[asdict(r) for r in records]})
                segments.append({'candidate':route.candidate.name,'leg':leg_index,'step':index,'samples':points})
    if timings is not None:timings['presentation_seconds']=monotonic()-mark
    return json.loads(canonical({'profile':'vinga-uddevalla','result_qualification':'estimated_high_uncertainty',
        'weather_limits_verified':False,'comparison':report,'estimated_segments':segments,'provenance':evidence,
        'configuration':config,'land_margin_m':10,'source_value_bounds':{'wind_abs_components_m_s':environment.wind_components,
        'wave_height_m':environment.wave_height_bound},'input_sha256':digest({'candidate':saved,'config':config,'provenance':evidence,
        'departure':when,'request':request,'selected_weather_limits':asdict(environment.policy),'boat':asdict(ConstantBoat(5)),
        'algorithm':environment.version,'resources':resources,'land_margin_m':environment.margin_m})}))
