"""One killable regional calculation using the shared frozen data/cache."""
import json
import sys
from pathlib import Path

from api.models import CoastalPlanInput
from application.coastal_plan import plan_coastal
from application.coastal_presentation import coastal_view
from application.planning import canonical

DATA=Path('/home/web/seaparser/data/vinga-uddevalla-20261018')
CACHE=Path('/home/web/seaparser/autonomy/cache/coastal-inputs-v1')


def main():
    data=sys.stdin.buffer.read(8193)
    if len(data)>8192:raise ValueError('För stor begäran')
    request=CoastalPlanInput.model_validate_json(data)
    timings={}
    try:
        full=plan_coastal(DATA,request.model_dump(mode='json'),cache_directory=CACHE,timings=timings)
        result=coastal_view(full,allow_empty=True)
        result['timings']=timings
        print(canonical(result))
    except ValueError as error:
        print(canonical({'error':str(error)[:500]}))


if __name__=='__main__':main()
