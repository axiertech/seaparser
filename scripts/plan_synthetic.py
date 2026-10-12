"""Run the documented offline scenario; no private config, network or database."""
import argparse
from application.planning import run_plan
from application.synthetic_plan import demo_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boat', choices=('polar', 'constant'), default='polar')
    parser.add_argument('--blocked-direct', action='store_true')
    parser.add_argument('--scenario', choices=('baseline', 'weather-limit', 'unverified', 'missing-waves'), default='baseline')
    parser.add_argument('--step-seconds', type=float, default=10)
    parser.add_argument('--selection-criterion', choices=('shortest_travel_time', 'earliest_arrival'))
    args = parser.parse_args()
    try:
        print(run_plan(demo_request(boat=args.boat, blocked_direct=args.blocked_direct,
                                   step_seconds=args.step_seconds, selection_criterion=args.selection_criterion, scenario=args.scenario)))
    except ValueError as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
