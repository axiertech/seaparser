"""Produce the standard real-weather route comparison and a portable review page."""
import argparse
from pathlib import Path
from application.geographic_plan import calculate_geographic,scene
from application.planning import canonical
from presentation.real_route_html import render


def build(output, *, candidates=2, departures=(0,600)):
    model=scene();a,b=model['start'],model['target']
    result=calculate_geographic({'profile':'vinga','start':dict(longitude=a[0],latitude=a[1]),
        'target':dict(longitude=b[0],latitude=b[1]),'margin_m':10,'departure_offsets_seconds':list(departures),'candidate_limit':candidates})
    output.mkdir(parents=True,exist_ok=True)
    (output/'result.json').write_text(canonical(result)+'\n')
    (output/'index.html').write_text(render(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidates',type=int,choices=(2,4,8),default=2)
    parser.add_argument('--departures',type=int,nargs='+',default=[0,600])
    args=parser.parse_args();result=build(args.output,candidates=args.candidates,departures=args.departures)
    print('REAL_ROUTE_REVIEW_COMPLETE',len(result['alternatives']),'alternatives;',args.output/'index.html')
