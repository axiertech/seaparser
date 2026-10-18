"""Offline free-point coastal planning over the preserved real source bundle."""
import argparse
import json
from pathlib import Path
from time import monotonic

from application.coastal_plan import plan_coastal
from application.planning import canonical


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('--request',type=Path,required=True)
    p.add_argument('--cache',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();timings={};start=monotonic()
    result=plan_coastal(a.directory,json.loads(a.request.read_text()),cache_directory=a.cache,timings=timings)
    a.output.write_text(canonical(result)+'\n')
    print('COASTAL_ESTIMATED_PLAN',json.dumps({'seconds':monotonic()-start,'timings':timings,
        'search':{k:result['geometry_search'][k] for k in ('status','expansions','node_count','truncated','limit_reason')},
        'routes':[{k:r[k] for k in ('status','reason','travel_seconds','distance_m','comfort_exposure','weather_segment_status')}
                  for r in result['comparison']['candidates']],
        'input_sha256':result['input_sha256'],'weather_limits_verified':False}))


if __name__=='__main__':main()
