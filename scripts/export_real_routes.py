"""Produce the standard real-weather route comparison and a portable review page."""
import argparse
from pathlib import Path
from application.geographic_plan import calculate_geographic,scene
from application.planning import canonical
from presentation.real_route_html import render


def build(output):
    model=scene();a,b=model['start'],model['target']
    result=calculate_geographic({'profile':'vinga','start':dict(longitude=a[0],latitude=a[1]),
        'target':dict(longitude=b[0],latitude=b[1]),'margin_m':10,'departure_offsets_seconds':[0,600]})
    output.mkdir(parents=True,exist_ok=True)
    (output/'result.json').write_text(canonical(result)+'\n')
    (output/'index.html').write_text(render(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=build(args.output)
    print('REAL_ROUTE_REVIEW_COMPLETE',len(result['alternatives']),'alternatives;',args.output/'index.html')
