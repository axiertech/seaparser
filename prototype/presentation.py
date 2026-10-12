"""JSON-export med uppslagspositioner, giltighetstider och antaganden."""
import json
from dataclasses import asdict


def export(steps):
    missing = [e.current_status == "assumed_zero"
               for s in steps for e in (s.start, s.midpoint)]
    coverage = ("ej utvärderad" if not missing else "saknas helt" if all(missing)
                else "delvis" if any(missing) else "full vid uppslag")
    rows = []
    for step in steps:
        row = asdict(step)
        row["sog_m_s"] = step.midpoint.ground.speed
        row["cog_degrees"] = step.midpoint.ground.course
        row["steering_degrees"] = step.midpoint.water.course
        rows.append(row)
    return json.dumps({"current_coverage": coverage, "steps": rows},
                      default=lambda value: value.isoformat(), ensure_ascii=False, indent=2)


def export_voyage(voyage):
    data = asdict(voyage)
    data.update(json.loads(export(voyage.steps)))
    return json.dumps(data, default=lambda value: value.isoformat(),
                      ensure_ascii=False, indent=2)


def export_route_comparison(comparison):
    """Present every candidate and its scope, including failed partial voyages."""
    rows = []
    for route in comparison.candidates:
        row = asdict(route)
        row['legs'] = [json.loads(export_voyage(leg)) for leg in route.legs]
        rows.append(row)
    return json.dumps({'status': comparison.status, 'scope': comparison.scope,
                       'fastest_candidate': (comparison.fastest.candidate.name
                                             if comparison.fastest else None),
                       'comfortable_candidate': (comparison.comfortable.candidate.name
                                                 if comparison.comfortable else None),
                       'weather_policy': asdict(comparison.weather_policy) if comparison.weather_policy else None,
                       'max_comfort_extra_seconds': comparison.max_comfort_extra_seconds,
                       'comfort_model': comparison.comfort_model,
                       'forecast_policy': asdict(comparison.forecast_policy) if comparison.forecast_policy else None,
                       'planning_time': comparison.planning_time,
                       'weather_verification_scope': comparison.weather_verification_scope, 'candidates': rows}, default=lambda value: value.isoformat(),
                      ensure_ascii=False, indent=2)
