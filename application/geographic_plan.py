"""Geographic use case composes existing planning; API/UI contain no routing math."""
from dataclasses import replace, asdict
from datetime import datetime, timedelta
from .development_weather import load_development_weather
from .planning import PlanRequest
from prototype.model import ConstantBoat
from prototype.forecast import ForecastPolicy
from prototype.weather import WeatherPolicy
from prototype.routes import RouteCandidate
import json
from infrastructure import land
from infrastructure.geography import to_local,to_geo,metadata
from prototype.auto_routing import SearchPolicy
from prototype.model import Vector
from prototype.polygon import Polygon
from .synthetic_plan import demo_request
from .obstacle_planning import run_obstacle_plan
from .planning import digest


def obstacle(margin=2):
    return Polygon('synthetic-island-v1',(Vector(40,-5),Vector(60,-5),Vector(60,5),Vector(40,5)),margin,kind='island')


def feature(geometry,properties):
    return {'type':'Feature','geometry':geometry,'properties':properties}


def collection(features):
    return {'type':'FeatureCollection','features':features}


def line(points, convert=to_geo):
    coordinates=[convert(p) for p in points]
    return {'type':'LineString','coordinates':coordinates} if len(coordinates)>1 else {'type':'Point','coordinates':coordinates[0]}


def position(value):
    return Vector(value['east'],value['north'])


def obstacle_geometry(shape, convert=to_geo):
    ring=[convert(p) for p in (*shape.vertices,shape.vertices[0])]
    properties={k:v for k,v in asdict(shape).items() if k != 'vertices'}
    return collection([feature({'type':'Polygon','coordinates':[ring]},properties)])


def scene(profile='vinga'):
    if profile == 'vinga':
        return regional_scene()
    if profile != 'synthetic':
        raise ValueError('Okänd region')
    request=demo_request(); shape=obstacle()
    corners=[Vector(-50,-50),Vector(150,-50),Vector(150,50),Vector(-50,50),Vector(-50,-50)]
    return {'synthetic':True,'dataset_version':request.dataset.version,'dataset_id':request.dataset.dataset_id,
            'planning_time':request.planning_time.isoformat(),'departure':request.departures[0].isoformat(),
            'start':to_geo(request.position),'target':to_geo(request.target),'projection':metadata(),
            'coverage':collection([feature({'type':'Polygon','coordinates':[[to_geo(p) for p in corners]]},{'kind':'forecast_coverage','quality':'estimated'})]),
            'obstacles':obstacle_geometry(shape),
            'limits':{'max_candidates':8,'max_departures':2,'margin_m':[0,10]},
            'notice':'Uppskattade syntetiska testdata. Ingen GPS/AIS. Kartbakgrund är inte routingsunderlag.'}


def calculate_geographic(payload, *, audit_candidate_limit=None):
    if payload.get('profile','vinga') not in ('synthetic','vinga'):
        raise ValueError('Okänd region')
    regional=payload.get('profile','vinga')=='vinga'
    candidate_limit=2 if regional else 8
    if audit_candidate_limit is not None:
        if not regional or audit_candidate_limit not in (2,4,8):
            raise ValueError('Offlineaudit tillåter endast Vinga och 2/4/8 kandidater')
        candidate_limit=audit_candidate_limit
    convert=land.to_geo if regional else to_geo
    local=land.to_local if regional else to_local
    projection=land.metadata() if regional else metadata()
    start=local(payload['start']['latitude'],payload['start']['longitude'])
    target=local(payload['target']['latitude'],payload['target']['longitude'])
    shape=obstacle(payload.get('margin_m',2))
    if regional:
        if payload.get('scenario','baseline') != 'baseline':
            raise ValueError('Verkligt väder ersätts aldrig med syntetiska marina scenarier')
        dataset,config,evidence=load_development_weather()
        request=PlanRequest(dataset=dataset,
            planning_time=datetime.fromisoformat(config['planning_time'].replace('Z','+00:00')),
            departures=(datetime.fromisoformat(config['departure'].replace('Z','+00:00')),),
            position=start,target=target,candidates=(RouteCandidate('direct'),),
            boat=ConstantBoat(config['boat_speed_knots']),
            weather_policy=WeatherPolicy(payload.get('max_wind_m_s') if payload.get('max_wind_m_s') is not None else config['max_wind_m_s'],
                                         payload.get('max_wave_height_m') if payload.get('max_wave_height_m') is not None else config['max_wave_height_m']),
            forecast_policy=ForecastPolicy(config['max_age_seconds']),max_comfort_extra_seconds=300)
    else:
        request=demo_request(scenario=payload.get('scenario','baseline'))
    snapshot=land.load_land(margin_m=payload.get('margin_m',2)) if regional else None
    shapes=snapshot.obstacles if regional else (shape,)
    waypoints=8 if regional else 4
    offsets=payload.get('departure_offsets_seconds',[0,600])
    request=replace(request,position=start,target=target,obstacles=shapes,
                    candidates=request.candidates[:2] if regional else request.candidates,
                    departures=tuple(request.departures[0]+timedelta(seconds=o) for o in offsets),
                    max_candidates=candidate_limit,max_waypoints=waypoints,max_steps=2000,max_seconds=1800,
                    step_seconds=30 if regional else 10,tolerance_m=.01)
    if regional:
        sampled=request.dataset.evaluate(start,request.departures[0])
        start_weather={'time':request.departures[0].isoformat(),
                       'wind_m_s':sampled.wind.speed if sampled.wind is not None else None,
                       'current_m_s':sampled.current.speed if sampled.current is not None else None,
                       'wave_height_m':sampled.waves.height_m if sampled.waves is not None else None,
                       'wave_period_seconds':sampled.waves.period_seconds if sampled.waves is not None else None}
    raw=json.loads(run_obstacle_plan(request,SearchPolicy(clearance_m=5,max_candidates=candidate_limit,
                                                        max_waypoints=waypoints,max_expansions=1000,max_nodes=26 if regional else 10)))
    features=[]; alternatives=[]
    if raw['planning']:
        for index,departure in enumerate(raw['planning']['comparison']['departures']):
            report=departure['routes']
            for route in report['candidates']:
                identifier=f'{index}-{route["candidate"]["name"]}'
                props={key:route[key] for key in ('status','reason','travel_seconds','arrival_time','comfort_exposure','weather_segment_status','arrival_weather_status')}
                props.update({'qualification':'conditional_on_assumptions' if regional else 'synthetic_reference', 'id':identifier,'candidate':route['candidate']['name'],
                              'departure_time':departure['departure_time'],
                              'fastest':route['candidate']['name']==report['fastest_candidate'],
                              'comfortable':route['candidate']['name']==report['comfortable_candidate']})
                planned=(start,*(position(p) for p in route['candidate']['waypoints']),target)
                actual=(start,*(position(s['end_position']) for leg in route['legs'] for s in leg['steps']))
                features.append(feature(line(planned,convert),props|{'kind':'planned'}))
                features.append(feature(line(actual,convert),props|{'kind':'accepted'}))
                for i,p in enumerate(planned):
                    features.append(feature({'type':'Point','coordinates':convert(p)},props|{'kind':'waypoint','order':i}))
                alternatives.append(props|{'waypoints':[convert(p) for p in planned]})
    land_metadata=json.loads(snapshot.source_geojson)['metadata'] | {'sha256':snapshot.sha256} if regional else None
    identity=digest({'routing_input_sha256':raw['input_sha256'],'land_snapshot_sha256':snapshot.sha256,
                     'projection':projection,'geographic_algorithm':'vinga-aeqd-geojson-v1'}) if regional else raw['input_sha256']
    return {'synthetic':not regional,'profile':'vinga' if regional else 'synthetic','projection':projection,'geometry_search':raw['geometry_search'],
            'land':land_metadata,'depth_status':'unknown','navigational_safety':'not_assessed',
            'data_quality':{'weather':'real_frozen_with_assumptions' if regional else 'synthetic_estimated','boat':'estimated','land':'unknown' if regional else 'synthetic_estimated'},
            **({'weather_provenance':evidence,'weather_at_start':start_weather,'result_qualification':'conditional_on_assumptions',
                 'selected_weather_limits':{'wind_m_s':request.weather_policy.max_wind_m_s,'wave_height_m':request.weather_policy.max_wave_height_m}} if regional else {}),
            'input_sha256':identity,'planning':raw['planning'],'routes':collection(features),
            'alternatives':alternatives,'obstacles':collection([f for p in shapes for f in obstacle_geometry(p,convert)['features']]),
            'notice':raw['limitations']+(' Verkliga historiska MET/WAV/PHY-data 2026-10-13; beräknad med uttryckliga utvecklingsantaganden, uppskattad konstantfartsbåt och ej validerat komfortmått.' if regional else ' Syntetiska referensdata.')+' Djup och landfullständighet är okända. Ej navigationssäkert.'}


def regional_scene():
    dataset,config,evidence=load_development_weather()
    snapshot=land.load_land(margin_m=10)
    corners=(Vector(-450,-420),Vector(520,-420),Vector(520,420),Vector(-450,420),Vector(-450,-420))
    return {'synthetic':False,'profile':'vinga','dataset_version':dataset.version,'dataset_id':dataset.dataset_id,
            'planning_time':config['planning_time'],'departure':config['departure'],
            'weather_provenance':evidence,'weather_limits':{'max_wind_m_s':config['max_wind_m_s'],'max_wave_height_m':config['max_wave_height_m']},
            'start':land.to_geo(Vector(300,-400)),'target':land.to_geo(Vector(300,400)),'projection':land.metadata(),
            'coverage':collection([feature({'type':'Polygon','coordinates':[[land.to_geo(p) for p in corners]]},{'kind':'forecast_coverage','quality':'estimated'})]),
            'obstacles':collection([f for p in snapshot.obstacles for f in obstacle_geometry(p,land.to_geo)['features']]),
            'land_display':json.loads(snapshot.source_geojson),'land':json.loads(snapshot.source_geojson)['metadata'] | {'sha256':snapshot.sha256},
            'depth_status':'unknown','navigational_safety':'not_assessed','default_margin_m':10,
            'limits':{'max_candidates':2,'max_departures':2,'margin_m':[0,10]},
            'notice':'Vinga: verkliga frysta MET-vind- och Copernicus-våg-/strömdata 2026-10-13. Historisk ruttjämförelse med uttryckliga antaganden och uppskattad konstantfartsbåt. Djup och landfullständighet okända. Ej navigationssäkert.'}
