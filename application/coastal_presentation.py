"""Lossless reserve evidence and a small view of an actually simulated voyage."""
from copy import deepcopy
from hashlib import sha256
import json

from infrastructure.land import INVERSE
from application.planning import canonical


def full_result_digest(result):
    # Same canonical bytes, hashed incrementally instead of a full string plus
    # its UTF-8 copy while the complete route/evidence tree is still resident.
    digest=sha256()
    encoder=json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    for chunk in encoder.iterencode(result):digest.update(chunk.encode('utf-8'))
    return digest.hexdigest()


def coastal_view(result,*,allow_empty=False):
    if (result['profile'] not in ('vinga-uddevalla','trelleborg-stromstad') or result['result_qualification'] != 'estimated_high_uncertainty'
            or result['weather_limits_verified'] is not False):
        raise ValueError('Explicit coastal estimate required')
    sources=[];connections=[];records=[];indexes=[{}, {}, {}]
    def intern(value,table,index):
        key=canonical(value)
        if key not in index:index[key]=len(table);table.append(value)
        return index[key]
    source_fields=('variable','source_longitude','source_latitude','source_time','source_value','uncertainty')
    connection_fields=('method','connection_waypoints','connection_expansions','connection_spacing_m','source_search_truncated')
    segments=[]
    for original_segment in result['estimated_segments']:
        segment={k:v for k,v in original_segment.items() if k!='samples'}
        segment['samples']=[];segments.append(segment)
        for original_sample in original_segment['samples']:
            sample={k:v for k,v in original_sample.items() if k!='estimates'}
            segment['samples'].append(sample)
            sample['longitude'],sample['latitude']=INVERSE.transform(sample['position']['east'],sample['position']['north'])
            refs=[]
            for original in original_sample['estimates']:
                record=dict(original)
                source={k:record.pop(k) for k in source_fields}
                connection={k:record.pop(k) for k in connection_fields}
                record.update(source=intern(source,sources,indexes[0]),connection=intern(connection,connections,indexes[1]))
                refs.append(intern(record,records,indexes[2]))
            sample['estimate_refs']=refs
    routes=[]
    for candidate in result['comparison']['candidates']:
        arrived=(candidate['status']=='arrived' and candidate['destination_reached'] and candidate['arrival_weather_status']=='passed_at_arrival')
        partial=(result['profile']=='trelleborg-stromstad' and candidate['status']!='arrived')
        if not arrived and not partial:continue
        own=[s for s in segments if s['candidate']==candidate['candidate']['name']]
        if not own:
            if partial:continue
            raise ValueError('Accepted coastal segments required')
        path=[[s['samples'][0]['longitude'],s['samples'][0]['latitude']] for s in own]
        path.append([own[-1]['samples'][-1]['longitude'],own[-1]['samples'][-1]['latitude']])
        waypoints=[path[0],*[list(INVERSE.transform(p['east'],p['north'])) for p in candidate['candidate']['waypoints']],
                   list(INVERSE.transform(candidate['target']['east'],candidate['target']['north']))]
        if partial:waypoints=path # Never export the untraversed tail of a partial route.
        routes.append({**{k:deepcopy(candidate[k]) for k in ('status','arrival_weather_status','weather_segment_status',
            'departure_time','arrival_time','travel_seconds','distance_m','comfort_exposure','weather_summary')},
            'partial':partial,'stop_reason':candidate['reason'],'requested_target':candidate['target'],
            'end_time':own[-1]['samples'][-1]['time'],
            'elapsed_seconds':candidate['elapsed_seconds'],
            'id':candidate['candidate']['name'],'path':path,'waypoints':waypoints,'segment_count':len(own),
            'result_qualification':'estimated_high_uncertainty','weather_limits_verified':False})
    if not routes and not allow_empty:raise ValueError('No arrived coastal estimate to present')
    return {'schema':1,'profile':result['profile'],'input_sha256':result['input_sha256'],
        'full_result_sha256':full_result_digest(result),
        'full_result_hash_format':'application.planning.canonical UTF-8, no newline',
        'result_qualification':'estimated_high_uncertainty','weather_limits_verified':False,
        'routes':routes,'provenance':deepcopy(result['provenance']),'configuration':deepcopy(result['configuration']),
        'land_margin_m':result['land_margin_m'],'source_value_bounds':result['source_value_bounds'],
        'reserve_evidence':{'sources':sources,'connections':connections,'records':records,'segments':segments},
        'comparison':{k:result['comparison'].get(k) for k in ('status','scope','fastest_candidate',
            'comfortable_candidate','max_comfort_extra_seconds','comfort_model')},
        'failures':[{k:r.get(k) for k in ('candidate','status','reason','arrival_weather_status')}
                    for r in result['comparison']['candidates'] if r['status']!='arrived'],
        'geometry_search':result.get('geometry_search'),'search_budget':result.get('search_budget')}


def restore_estimates(view,sample):
    evidence=view['reserve_evidence'];result=[]
    for ref in sample['estimate_refs']:
        record=dict(evidence['records'][ref]);source=record.pop('source');connection=record.pop('connection')
        result.append({**record,**evidence['sources'][source],**evidence['connections'][connection]})
    return result


from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def coastal_coverage():
    """Small frozen coverage metadata; never load forecast arrays on HTTP calls."""
    path=Path(__file__).resolve().parents[1]/'fixtures/vinga-uddevalla-preflight.json'
    data=json.loads(path.read_text())
    return {k:data[k] for k in ('bbox','valid_times','reference_time')}


def swedish_coast_snapshot():
    """Return the saved simulation; no large weather load on HTTP requests."""
    return json.loads((Path(__file__).resolve().parents[1]/'fixtures/trelleborg-voyage.json').read_text())
