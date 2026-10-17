"""Measured offline sensitivity on frozen real weather; never a live fetch."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from time import perf_counter
import subprocess
import sys

from application.development_weather import load_development_weather
from application.geographic_plan import scene, calculate_geographic
from application.planning import canonical

DEPARTURES = (0, 600, 3600, 10800)


def audit():
    dataset, config, evidence = load_development_weather()
    base = datetime.fromisoformat(config['departure'].replace('Z', '+00:00'))
    products = dataset.product_metadata
    valid_from = max(p.valid_from for p in products)
    valid_until = min(p.valid_until for p in products)
    # Reserve the full existing per-route duration, not merely a start-time lookup.
    if any(not (valid_from <= base + timedelta(seconds=o) and
                base + timedelta(seconds=o + 1800) < valid_until) for o in DEPARTURES):
        raise ValueError('Auditavgångar och hela ruttbudgeten måste rymmas i gemensamt tidsstöd')
    s = scene('vinga'); a, b = s['start'], s['target']
    payload = {'profile': 'vinga', 'start': {'latitude': a[1], 'longitude': a[0]},
               'target': {'latitude': b[1], 'longitude': b[0]}, 'margin_m': 10,
               'departure_offsets_seconds': list(DEPARTURES)}
    reports = []
    for limit in (2, 4, 8):
        started = perf_counter()
        result = calculate_geographic(payload, audit_candidate_limit=limit)
        elapsed = perf_counter() - started
        departures = []
        for d in result['planning']['comparison']['departures']:
            routes = d['routes']; by_name = {r['candidate']['name']: r for r in routes['candidates']}
            def selected(name):
                r = by_name.get(name)
                return None if r is None else {'candidate': r['candidate']['name']} | {
                    k: r[k] for k in ('travel_seconds', 'comfort_exposure', 'arrival_time')}
            departures.append({'departure': d['departure_time'],
                'fastest': selected(routes['fastest_candidate']),
                'comfortable': selected(routes['comfortable_candidate']),
                'same_winner': routes['fastest_candidate'] is not None and routes['fastest_candidate'] == routes['comfortable_candidate'],
                'candidates': [{k: r[k] for k in ('candidate', 'status', 'reason', 'travel_seconds', 'comfort_exposure')}
                               for r in routes['candidates']]})
        reports.append({'candidate_limit': limit, 'elapsed_seconds': elapsed,
            'input_sha256': result['input_sha256'], 'dataset_sha256': result['planning']['manifest']['dataset_sha256'],
            'geometry_search': result['geometry_search'], 'departures': departures,
            'result_bytes': len(canonical(result).encode())})
    return {'synthetic_weather': False, 'source_qualification': evidence['source_qualification'],
        'result_qualification': 'conditional_on_assumptions', 'weather_provenance': evidence,
        'common_time_support': {'from': valid_from.isoformat(), 'until_exclusive': valid_until.isoformat()},
        'departure_offsets_seconds': list(DEPARTURES), 'max_route_seconds': 1800,
        'timing_scope': 'Warm frozen-input cache, sequential calculation wall time; excludes final JSON encoding and process startup. Not an API latency guarantee.',
        'scope': 'Endast denna frysta fixture, graf och fyra avgångar; geometrisk ordning är inte väderoptimalitet.',
        'reports': reports}


def audit_workers():
    """Cold process protocol with the unchanged 20 s and 8 MB job limits."""
    s=scene();a,b=s['start'],s['target']
    payload={'profile':'vinga','start':dict(longitude=a[0],latitude=a[1]),
             'target':dict(longitude=b[0],latitude=b[1]),'margin_m':10}
    reports=[]
    for count,offsets in ((4,DEPARTURES),(8,(0,600))):
        started=perf_counter()
        try:
            process=subprocess.run([sys.executable,'-B','-m','scripts.geographic_worker'],
                input=canonical(payload | {'candidate_limit':count,'departure_offsets_seconds':list(offsets)}).encode(),
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=20,check=True,
                cwd=Path(__file__).resolve().parents[1])
            elapsed=perf_counter()-started
            result=json.loads(process.stdout)
            reports.append({'candidate_limit':count,'departure_offsets_seconds':list(offsets),
                'elapsed_seconds':elapsed,'result_bytes':len(process.stdout),
                'within_job_limits':elapsed<20 and len(process.stdout)<=8_000_000,
                'alternatives':len(result['alternatives']),'input_sha256':result['input_sha256']})
        except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
            reports.append({'candidate_limit':count,'departure_offsets_seconds':list(offsets),
                'elapsed_seconds':perf_counter()-started,'within_job_limits':False})
    return {'scope':'Sequential cold worker process, same frozen default endpoints; no latency guarantee for other routes or concurrent load.',
            'timeout_seconds':20,'max_result_bytes':8_000_000,'reports':reports}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--workers',action='store_true',help='Measure only the two interactive ceilings in cold workers')
    args = parser.parse_args()
    report = audit_workers() if args.workers else audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical(report) + '\n')
        print('AUDIT_COMPLETE', [(r['candidate_limit'], round(r['elapsed_seconds'], 3)) for r in report['reports']])
    else:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
