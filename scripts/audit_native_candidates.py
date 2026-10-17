"""Bounded offline search over unchanged real native weather and all 24 hulls.

No network or API budget extension. Explicit 66-node audit policy, 1000 queue/
expansion budget, 8 waypoints and 1800 s per-route duration remain finite.
"""
import argparse
from pathlib import Path
from time import perf_counter
import json
import subprocess
import sys

from application.development_weather import ROOT
from application.geographic_plan import calculate_geographic
from application.planning import canonical
from infrastructure.land import to_geo
from presentation.real_route_html import render
from prototype.model import Vector

OFFSETS=(0,600,3600,10800)
CONFIG=ROOT/'settings/development-weather-native-assumptions.json'


def payload():
    a,b=to_geo(Vector(500,0)),to_geo(Vector(500,350))
    return dict(profile='vinga',start=dict(longitude=a[0],latitude=a[1]),
        target=dict(longitude=b[0],latitude=b[1]),margin_m=10,
        departure_offsets_seconds=list(OFFSETS))


def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    reports=[]
    for limit in (2,4,8):
        started=perf_counter()
        result=calculate_geographic(payload(),weather_config=CONFIG,
            audit_candidate_limit=limit,audit_node_limit=66)
        elapsed=perf_counter()-started
        encoded=canonical(result)+'\n'
        reports.append(dict(candidate_limit=limit,elapsed_seconds=elapsed,result_bytes=len(encoded.encode()),
            input_sha256=result['input_sha256'],geometry_search=result['geometry_search'],
            search_budget=result['search_budget'],alternative_comparison=result['alternative_comparison'],
            alternatives=result['alternatives']))
        if limit==8:
            (output/'result.json').write_text(encoded)
        print('NATIVE_CANDIDATE_AUDIT',limit,round(elapsed,3),len(result['alternatives']),flush=True)
    (output/'index.html').write_text(render(result))
    report=dict(scope='Offline only; same explicit endpoints, all24 hard land hulls, frozen real17Oct MET/WAV/PHY. No weather optimality.',
        source_qualification='unverified',result_qualification='conditional_on_assumptions',
        start_m=[500,0],target_m=[500,350],departure_offsets_seconds=list(OFFSETS),
        max_route_seconds=1800,unchanged_development_radius_m=900,
        interactive_extension_enabled=False,interactive_timeout_seconds=20,interactive_result_bytes=8000000,
        timing_scope='Sequential wall time through result composition, before final encoding. First case cold application cache; later cases warm. No concurrent-load or API latency guarantee.',
        land_sha256=result['land']['sha256'],weather_provenance=result['weather_provenance'],reports=reports)
    (output/'audit.json').write_text(canonical(report)+'\n')
    return report


def workers(output):
    """Cold audit composition with the existing interactive process limits."""
    reports=[]
    for count,offsets in ((2,OFFSETS),(4,OFFSETS),(8,(0,600))):
        started=perf_counter()
        try:
            p=subprocess.run([sys.executable,'-B','-m',__spec__.name,'--worker-candidates',str(count),
                '--offsets',*(str(o) for o in offsets)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                timeout=20,check=True,cwd=ROOT)
            elapsed=perf_counter()-started
            result=json.loads(p.stdout)
            reports.append(dict(candidate_limit=count,departure_offsets_seconds=offsets,elapsed_seconds=elapsed,
                result_bytes=len(p.stdout),within_job_limits=elapsed<20 and len(p.stdout)<=8000000,
                alternative_count=len(result['alternatives']),input_sha256=result['input_sha256']))
        except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
            reports.append(dict(candidate_limit=count,departure_offsets_seconds=offsets,
                elapsed_seconds=perf_counter()-started,within_job_limits=False))
        print('NATIVE_COLD_WORKER',count,round(reports[-1]['elapsed_seconds'],3),reports[-1]['within_job_limits'],flush=True)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    report=dict(scope='Sequential cold offline workers for the audited endpoints only; no interactive extension or concurrent-load guarantee.',
        timeout_seconds=20,max_result_bytes=8000000,host_load='Uncontrolled; no isolated-CPU or concurrent-load claim.',reports=reports)
    (output/'workers.json').write_text(canonical(report)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    p.add_argument('--workers',action='store_true')
    p.add_argument('--worker-candidates',type=int,choices=(2,4,8))
    p.add_argument('--offsets',type=int,nargs='+',choices=OFFSETS,default=list(OFFSETS))
    a=p.parse_args()
    if a.worker_candidates:
        print(canonical(calculate_geographic(payload() | {'departure_offsets_seconds':a.offsets},
            weather_config=CONFIG,audit_candidate_limit=a.worker_candidates,audit_node_limit=66)))
    elif a.output:
        (workers if a.workers else build)(a.output)
    else:
        p.error('--output krävs')
