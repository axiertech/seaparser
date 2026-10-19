"""JSON-export med uppslagspositioner, giltighetstider och antaganden."""
import json
from dataclasses import asdict,fields,is_dataclass
from datetime import datetime


def json_value(value):
    """Build one JSON-native tree; immutable engine objects stay untouched."""
    if is_dataclass(value):return {f.name:json_value(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,datetime):return value.isoformat()
    if isinstance(value,dict):return {k:json_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_value(v) for v in value]
    return value


def step_data(steps):
    missing=[e.current_status=='assumed_zero' for s in steps for e in (s.start,s.midpoint)]
    coverage=('ej utvärderad' if not missing else 'saknas helt' if all(missing)
              else 'delvis' if any(missing) else 'full vid uppslag')
    rows=[]
    for step in steps:
        row=json_value(step)
        row.update(sog_m_s=step.midpoint.ground.speed,cog_degrees=step.midpoint.ground.course,
                   steering_degrees=step.midpoint.water.course)
        rows.append(row)
    return {'current_coverage':coverage,'steps':rows}


def voyage_data(voyage):
    row={f.name:json_value(getattr(voyage,f.name)) for f in fields(voyage) if f.name!='steps'}
    row.update(step_data(voyage.steps))
    return row


def route_comparison_data(comparison):
    """Lossless comparison without repeated asdict and JSON round trips."""
    rows=[]
    for route in comparison.candidates:
        row={f.name:json_value(getattr(route,f.name)) for f in fields(route) if f.name!='legs'}
        row['legs']=[voyage_data(leg) for leg in route.legs];rows.append(row)
    return {'status':comparison.status,'scope':comparison.scope,
        'fastest_candidate':comparison.fastest.candidate.name if comparison.fastest else None,
        'comfortable_candidate':comparison.comfortable.candidate.name if comparison.comfortable else None,
        'weather_policy':json_value(comparison.weather_policy),
        'max_comfort_extra_seconds':comparison.max_comfort_extra_seconds,'comfort_model':comparison.comfort_model,
        'forecast_policy':json_value(comparison.forecast_policy),'planning_time':json_value(comparison.planning_time),
        'dataset_id':comparison.dataset_id,'dataset_version':comparison.dataset_version,
        'forecast_products':json_value(comparison.forecast_products),
        'weather_verification_scope':comparison.weather_verification_scope,'candidates':rows}


def export(steps):
    return json.dumps(step_data(steps),ensure_ascii=False,indent=2)


def export_voyage(voyage):
    return json.dumps(voyage_data(voyage),ensure_ascii=False,indent=2)


def export_route_comparison(comparison):
    return json.dumps(route_comparison_data(comparison),ensure_ascii=False,indent=2)


def export_departure_comparison(comparison):
    """Include complete per-departure evidence and explicit objective summaries."""
    def summary(route):
        if route is None:
            return None
        return {'candidate': route.candidate.name, 'departure_time': route.departure_time,
                'travel_seconds': route.travel_seconds, 'arrival_time': route.arrival_time,
                'comfort_exposure': route.comfort_exposure}

    return json.dumps({
        'status': comparison.status, 'scope': comparison.scope,
        'planning_time': comparison.planning_time,
        'selection_criterion': comparison.selection_criterion,
        'selected': summary(comparison.selected),
        'shortest_travel': summary(comparison.shortest_travel),
        'earliest_arrival': summary(comparison.earliest_arrival),
        'departures': [{'departure_time': row.departure_time,
                        'routes': json.loads(export_route_comparison(row.routes))}
                       for row in comparison.departures]},
        default=lambda value: value.isoformat(), ensure_ascii=False, indent=2)
