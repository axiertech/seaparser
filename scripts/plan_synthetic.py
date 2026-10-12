"""Run the documented offline scenario; no private config, network or database."""
import argparse
from datetime import timedelta

from application.planning import PlanRequest, run_plan
from infrastructure.synthetic_forecast import PLAN, START, synthetic_snapshot
from prototype.forecast import ForecastPolicy
from prototype.model import ConstantBoat, KNOT, Vector
from prototype.obstacles import Rectangle
from prototype.routes import RouteCandidate
from prototype.sailing import PolarBoat
from prototype.weather import WeatherPolicy


def demo_request(*, boat='polar', blocked_direct=False, step_seconds=10, selection_criterion=None):
    if boat not in ('polar', 'constant'):
        raise ValueError('Okänd syntetisk båtmodell')
    return PlanRequest(
        dataset=synthetic_snapshot(), planning_time=PLAN,
        departures=(START, START+timedelta(seconds=600)), target=Vector(100, 0),
        candidates=(RouteCandidate('direct'), RouteCandidate('north', (Vector(20, 20), Vector(80, 20))),
                    RouteCandidate('south', (Vector(20, -20), Vector(80, -20)))),
        boat=PolarBoat() if boat == 'polar' else ConstantBoat(1/KNOT, leeway=0),
        weather_policy=WeatherPolicy(5, 1), forecast_policy=ForecastPolicy(600),
        obstacles=(Rectangle('synthetic-island', 40, -5, 60, 5),) if blocked_direct else (),
        step_seconds=step_seconds, selection_criterion=selection_criterion)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boat', choices=('polar', 'constant'), default='polar')
    parser.add_argument('--blocked-direct', action='store_true')
    parser.add_argument('--step-seconds', type=float, default=10)
    parser.add_argument('--selection-criterion', choices=('shortest_travel_time', 'earliest_arrival'))
    args = parser.parse_args()
    try:
        print(run_plan(demo_request(boat=args.boat, blocked_direct=args.blocked_direct,
                                   step_seconds=args.step_seconds, selection_criterion=args.selection_criterion)))
    except ValueError as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
