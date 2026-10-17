"""Offline native-geometry, expanded-land and conditional route review.

No download, publication or routing-area expansion. Public API defaults stay
on the existing configuration; this CLI uses the named alternate assumptions.
"""
import argparse
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

from application.development_weather import ROOT,load_development_weather
from application.geographic_plan import calculate_geographic,scene
from application.planning import canonical,PlanRequest,run_plan
from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from infrastructure.land import load_land
from presentation.real_route_html import render
from prototype.auto_routing import generate_routes,SearchPolicy
from prototype.model import Vector,ConstantBoat
from prototype.forecast import ForecastPolicy
from prototype.weather import WeatherPolicy
from prototype.routes import RouteCandidate
from datetime import datetime
import json
from scripts.freeze_copernicus_reference import freeze_native_with_audit


def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    s=scene();a,b=s['start'],s['target']
    payload=dict(profile='vinga',start=dict(longitude=a[0],latitude=a[1]),target=dict(longitude=b[0],latitude=b[1]),
                 margin_m=10,departure_offsets_seconds=[0,600])
    result=calculate_geographic(payload,weather_config=ROOT/'settings/development-weather-native-assumptions.json')
    (output/'result.json').write_text(canonical(result)+'\n');(output/'index.html').write_text(render(result))
    raw,_=freeze_native_with_audit(ROOT/'fixtures/vinga-expanded-20261017',radius_m=2000)
    dataset=CopernicusMarineAdapter().normalize(raw,native_radius_m=2000);time=dataset.products[0].times[0]
    dataset.validate_segment(Vector(-1500,0),time,Vector(1500,0),time+timedelta(seconds=1200))
    land=load_land(ROOT/'fixtures/vinga-land-expanded-20261017.geojson',review_bounds=(11.55,57.60,11.66,57.67))
    search=generate_routes(Vector(300,-400),Vector(300,400),land.obstacles,
        SearchPolicy(clearance_m=5,max_candidates=2,max_waypoints=8,max_expansions=1000,max_nodes=26))
    feasible_search=generate_routes(Vector(500,0),Vector(500,350),land.obstacles,
        SearchPolicy(clearance_m=5,max_candidates=2,max_waypoints=8,max_expansions=1000,max_nodes=26))
    composed,config,evidence=load_development_weather(ROOT/'settings/development-weather-native-assumptions.json')
    specified=PlanRequest(dataset=composed,planning_time=datetime.fromisoformat(config['planning_time'].replace('Z','+00:00')),
        departures=(datetime.fromisoformat(config['departure'].replace('Z','+00:00')),),position=Vector(500,0),target=Vector(500,350),
        candidates=(RouteCandidate('specified-east-segment'),),boat=ConstantBoat(config['boat_speed_knots']),obstacles=land.obstacles,
        weather_policy=WeatherPolicy(config['max_wind_m_s'],config['max_wave_height_m']),forecast_policy=ForecastPolicy(config['max_age_seconds']),
        step_seconds=30,max_seconds=1800,max_steps=2000)
    specified_result=json.loads(run_plan(specified))
    (output/'specified-route.json').write_text(canonical(specified_result)+'\n')
    report=dict(scope='native_marine_geometry_and_expanded_land_component_review',source_qualification='unverified',
        result_qualification='diagnostic_only',routing_area_expanded=False,unchanged_development_radius_m=900,
        native_marine_radius_m=2000,guard_m=1,geographic_disk_bounds=dataset.products[0].geographic_bounds,
        products=[dict(product=p.metadata.product,node_count=len(p.latitude)*len(p.longitude),time_count=len(p.times),
            source_sha256=p.metadata.source_sha256,issued_at=None,planning_blockers=p.metadata.planning_blockers,
            whole_disk_support_nodes=len(p.support_nodes)) for p in dataset.products],
        segment_check=dict(start_m=[-1500,0],end_m=[1500,0],seconds=1200,
            whole_envelope_data_support='passed_within_coordinate_interpolation_model'),
        land=dict(snapshot_sha256=land.sha256,closed_hulls=len(land.obstacles),review_disk_radius_m=1500,
            completeness='unknown',depth='unknown',geometry_search=asdict(search),feasible_endpoint_search=asdict(feasible_search)),
        conditional_demo=dict(input_sha256=result['input_sha256'],result_qualification=result['result_qualification'],
            algorithm_version=result['planning']['manifest']['algorithm_version'] if result['planning'] else None,snapshot_date='2026-10-17',
            configured_radius_m=900,geometry_search_status=result['geometry_search']['status'],alternative_comparison=result['alternative_comparison'],alternatives=result['alternatives']),specified_route=dict(scope='Single explicitly supplied segment; not automatic candidate search',
            result_qualification=specified_result['manifest']['result_qualification'],comparison=specified_result['comparison']))
    (output/'report.json').write_text(canonical(report)+'\n')
    return report,result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report,result=build(a.output)
    print('NATIVE_MARINE_REVIEW_COMPLETE',len(result['alternatives']),'conditional alternatives;',
          report['land']['closed_hulls'],'land hulls; expanded geometry search',report['land']['geometry_search']['status'])
