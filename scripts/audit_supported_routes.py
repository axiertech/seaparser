"""Offline audit and cold API-worker measurements for the bounded native profile."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from application.development_weather import ROOT
from application.geographic_plan import calculate_geographic
from application.planning import canonical
from presentation.real_route_html import render
from scripts.audit_native_candidates import payload,OFFSETS


def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    reports=[];selected=None
    for limit in (2,4,8):
        request=payload() | {'profile':'vinga-native'}
        started=perf_counter()
        result=calculate_geographic(request,audit_candidate_limit=limit)
        elapsed=perf_counter()-started
        reports.append(dict(candidate_limit=limit,elapsed_seconds=elapsed,result_bytes=len(canonical(result).encode())+1,
            geometry_search=result['geometry_search'],alternative_comparison=result['alternative_comparison'],
            alternatives=result['alternatives'],input_sha256=result['input_sha256']))
        if limit==4:
            # Publish a review of an actually permitted interactive combination.
            selected=calculate_geographic(request | {'candidate_limit':4})
        print('SUPPORTED_ROUTE_AUDIT',limit,round(elapsed,3),len(result['alternatives']),flush=True)
    (output/'result.json').write_text(canonical(selected)+'\n')
    (output/'index.html').write_text(render(selected))
    products=selected['planning']['manifest']['forecast_products']
    report=dict(profile='vinga-native',scope='Only examined graph paths and explicit departures; no global weather optimality.',
        source_qualification='unverified',result_qualification='conditional_on_assumptions',
        node_radius_m=900,max_nodes=26,hard_obstacles=24,max_route_seconds=1800,
        departure_offsets_seconds=OFFSETS,common_time_support=dict(valid_from=max(p['valid_from'] for p in products),
            until_exclusive=min(p['valid_until'] for p in products)),
        timing_scope='Sequential composition wall time before encoding; first cache cold, later warm. Not a concurrent-load guarantee.',
        reports=reports)
    (output/'audit.json').write_text(canonical(report)+'\n')
    return report


def workers(output):
    rows=[]
    for limit,offsets in ((2,OFFSETS),(4,OFFSETS),(8,(0,600))):
        request=payload() | dict(profile='vinga-native',candidate_limit=limit,departure_offsets_seconds=offsets)
        started=perf_counter()
        try:
            p=subprocess.run([sys.executable,'-B','-m','scripts.geographic_worker'],input=canonical(request).encode(),
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=True,cwd=ROOT)
            elapsed=perf_counter()-started;r=json.loads(p.stdout)
            rows.append(dict(candidate_limit=limit,departure_offsets_seconds=offsets,elapsed_seconds=elapsed,
                result_bytes=len(p.stdout),within_job_limits=elapsed<20 and len(p.stdout)<=8000000,
                node_count=r['geometry_search']['node_count'],alternative_count=len(r['alternatives']),input_sha256=r['input_sha256']))
        except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
            rows.append(dict(candidate_limit=limit,departure_offsets_seconds=offsets,
                elapsed_seconds=perf_counter()-started,within_job_limits=False))
        print('SUPPORTED_COLD_WORKER',limit,round(rows[-1]['elapsed_seconds'],3),rows[-1]['within_job_limits'],flush=True)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    report=dict(scope='Sequential cold standard API workers for explicit native endpoints only; no concurrent-load or general latency guarantee.',
        timeout_seconds=20,max_result_bytes=8000000,max_active=2,max_evaluations=16,reports=rows)
    (output/'workers.json').write_text(canonical(report)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',action='store_true');a=p.parse_args()
    (workers if a.workers else build)(a.output)
