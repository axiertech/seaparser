"""One bounded calculation in a private child process; protocol via stdin/stdout."""
import json
import sys
from api.models import PlanInput
from application.geographic_plan import calculate_geographic
from application.planning import canonical


def main():
    data=sys.stdin.buffer.read(8193)
    if len(data)>8192:
        raise ValueError('För stor begäran')
    request=PlanInput.model_validate_json(data)
    print(canonical(calculate_geographic(request.model_dump())))


if __name__=='__main__':
    main()
