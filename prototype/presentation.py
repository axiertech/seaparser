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
