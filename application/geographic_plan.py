"""Geographic use case composes existing planning; API/UI contain no routing math."""
from dataclasses import replace, asdict
from datetime import timedelta
import json
from infrastructure.geography import to_local,to_geo,metadata
from prototype.auto_routing import SearchPolicy
from prototype.model import Vector
from prototype.polygon import Polygon
from .synthetic_plan import demo_request
from .obstacle_planning import run_obstacle_plan


def obstacle(margin=2):
    return Polygon('synthetic-island-v1',(Vector(40,-5),Vector(60,-5),Vector(60,5),Vector(40,5)),margin,kind='island')


def feature(geometry,properties):
    return {'type':'Feature','geometry':geometry,'properties':properties}


def collection(features):
    return {'type':'FeatureCollection','features':features}


def line(points):
    coordinates=[to_geo(p) for p in points]
    return {'type':'LineString','coordinates':coordinates} if len(coordinates)>1 else {'type':'Point','coordinates':coordinates[0]}


def position(value):
    return Vector(value['east'],value['north'])


def obstacle_geometry(shape):
    ring=[to_geo(p) for p in (*shape.vertices,shape.vertices[0])]
    properties={k:v for k,v in asdict(shape).items() if k != 'vertices'}
    return collection([feature({'type':'Polygon','coordinates':[ring]},properties)])


def scene():
    request=demo_request(); shape=obstacle()
    corners=[Vector(-50,-50),Vector(150,-50),Vector(150,50),Vector(-50,50),Vector(-50,-50)]
    return {'synthetic':True,'dataset_version':request.dataset.version,'dataset_id':request.dataset.dataset_id,
            'planning_time':request.planning_time.isoformat(),'departure':request.departures[0].isoformat(),
            'start':to_geo(request.position),'target':to_geo(request.target),'projection':metadata(),
            'coverage':collection([feature({'type':'Polygon','coordinates':[[to_geo(p) for p in corners]]},{'kind':'forecast_coverage','quality':'estimated'})]),
            'obstacles':obstacle_geometry(shape),
            'limits':{'max_candidates':8,'max_departures':2,'margin_m':[0,10]},
            'notice':'Uppskattade syntetiska testdata. Ingen GPS/AIS. Kartbakgrund är inte routingsunderlag.'}


def calculate_geographic(payload):
    start=to_local(payload['start']['latitude'],payload['start']['longitude'])
    target=to_local(payload['target']['latitude'],payload['target']['longitude'])
    shape=obstacle(payload.get('margin_m',2))
    request=demo_request(scenario=payload.get('scenario','baseline'))
    offsets=payload.get('departure_offsets_seconds',[0,600])
    request=replace(request,position=start,target=target,obstacles=(shape,),
                    departures=tuple(request.departures[0]+timedelta(seconds=o) for o in offsets),
                    max_candidates=8,max_waypoints=4,max_steps=2000,max_seconds=1800,
                    step_seconds=10,tolerance_m=.01)
    raw=json.loads(run_obstacle_plan(request,SearchPolicy(clearance_m=5,max_candidates=8,
                                                        max_waypoints=4,max_expansions=1000,max_nodes=10)))
    features=[]; alternatives=[]
    if raw['planning']:
        for index,departure in enumerate(raw['planning']['comparison']['departures']):
            report=departure['routes']
            for route in report['candidates']:
                identifier=f'{index}-{route["candidate"]["name"]}'
                props={key:route[key] for key in ('status','reason','travel_seconds','arrival_time','comfort_exposure','weather_segment_status','arrival_weather_status')}
                props.update({'id':identifier,'candidate':route['candidate']['name'],
                              'departure_time':departure['departure_time'],
                              'fastest':route['candidate']['name']==report['fastest_candidate'],
                              'comfortable':route['candidate']['name']==report['comfortable_candidate']})
                planned=(start,*(position(p) for p in route['candidate']['waypoints']),target)
                actual=(start,*(position(s['end_position']) for leg in route['legs'] for s in leg['steps']))
                features.append(feature(line(planned),props|{'kind':'planned'}))
                features.append(feature(line(actual),props|{'kind':'accepted'}))
                for i,p in enumerate(planned):
                    features.append(feature({'type':'Point','coordinates':to_geo(p)},props|{'kind':'waypoint','order':i}))
                alternatives.append(props|{'waypoints':[to_geo(p) for p in planned]})
    return {'synthetic':True,'projection':metadata(),'geometry_search':raw['geometry_search'],
            'input_sha256':raw['input_sha256'],'planning':raw['planning'],'routes':collection(features),
            'alternatives':alternatives,'obstacles':obstacle_geometry(shape),
            'notice':raw['limitations']+' Uppskattad polar och syntetisk komfort; inga verkliga djupdata.'}
