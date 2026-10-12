"""Read frozen real reference offline; no HTTP, credentials or live publication."""
import json
from pathlib import Path
from application.real_forecast_reference import plan_reference

if __name__=='__main__':
    path=Path(__file__).resolve().parents[1]/'fixtures/vinga-point-forecast-reference.json'
    print(json.dumps(plan_reference(json.loads(path.read_text())),default=lambda value:value.isoformat(),ensure_ascii=False,sort_keys=True))
