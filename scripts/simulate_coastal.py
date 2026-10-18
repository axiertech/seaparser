"""Run the existing voyage engine over a preserved regional geometric candidate."""
import argparse
import json
from pathlib import Path
from time import monotonic
from application.coastal_plan import simulate_coastal_candidate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--departure')
    a=p.parse_args();timings={};start=monotonic()
    result=simulate_coastal_candidate(a.directory,a.candidate,departure=a.departure,timings=timings)
    a.output.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False)+'\n')
    print('COASTAL_ESTIMATED_VOYAGE',json.dumps({'seconds':monotonic()-start,'timings':timings,
        'routes':[{k:r[k] for k in ('status','reason','travel_seconds','distance_m','comfort_exposure','weather_segment_status')}
                  for r in result['comparison']['candidates']],
        'input_sha256':result['input_sha256'],'weather_limits_verified':False}))


if __name__=='__main__':main()
