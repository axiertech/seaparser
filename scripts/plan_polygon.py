"""Reproducible offline polygon detour; no chart, database or network access."""
import argparse
from dataclasses import replace
from application.obstacle_planning import run_obstacle_plan
from prototype.auto_routing import SearchPolicy
from prototype.model import Vector
from prototype.polygon import Polygon
from scripts.plan_synthetic import demo_request


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--margin-m',type=float,default=2)
    parser.add_argument('--clearance-m',type=float,default=5)
    parser.add_argument('--max-candidates',type=int,default=8)
    args=parser.parse_args()
    try:
        polygon=Polygon('synthetic-island-v1',
                        (Vector(40,-5),Vector(60,-5),Vector(60,5),Vector(40,5)),
                        args.margin_m,kind='island')
        request=replace(demo_request(),obstacles=(polygon,))
        print(run_obstacle_plan(request,SearchPolicy(clearance_m=args.clearance_m,
                                                    max_candidates=args.max_candidates)))
    except ValueError as error:
        parser.exit(2,str(error)+'\n')


if __name__=='__main__':
    main()
