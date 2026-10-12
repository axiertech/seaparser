"""Frozen synthetic composition shared by CLI and geographic planning."""
from datetime import timedelta

from .planning import PlanRequest
from infrastructure.synthetic_forecast import PLAN, START, synthetic_snapshot
from prototype.forecast import ForecastPolicy
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.obstacles import Rectangle
from prototype.routes import RouteCandidate
from prototype.sailing import PolarBoat
from prototype.weather import WeatherPolicy


def demo_request(*, boat='polar', blocked_direct=False, step_seconds=10, selection_criterion=None, scenario='baseline'):
    if boat not in ('polar', 'constant'):
        raise ValueError('Okänd syntetisk båtmodell')
    return PlanRequest(
        dataset=synthetic_snapshot(scenario), planning_time=PLAN,
        departures=(START, START+timedelta(seconds=600)), target=Vector(100, 0),
        candidates=(RouteCandidate('direct'), RouteCandidate('north', (Vector(20, 20), Vector(80, 20))),
                    RouteCandidate('south', (Vector(20, -20), Vector(80, -20)))),
        boat=PolarBoat() if boat == 'polar' else ConstantBoat(1/KNOT, leeway=0),
        weather_policy=WeatherPolicy(5, 1), forecast_policy=ForecastPolicy(600),
        obstacles=(Rectangle('synthetic-island', 40, -5, 60, 5),) if blocked_direct else (),
        step_seconds=step_seconds, selection_criterion=selection_criterion)
