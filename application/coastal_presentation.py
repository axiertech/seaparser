"""Lossless reserve evidence and a small view of an actually simulated voyage."""
from copy import deepcopy
from hashlib import sha256
import json

from infrastructure.land import INVERSE
from application.planning import canonical


def coastal_view(result):
    if (result['profile'] != 'vinga-uddevalla' or result['result_qualification'] != 'estimated_high_uncertainty'
            or result['weather_limits_verified'] is not False):
        raise ValueError('Explicit coastal estimate required')
    sources=[];connections=[];records=[];indexes=[{}, {}, {}]
    def intern(value,table,index):
        key=canonical(value)
        if key not in index:index[key]=len(table);table.append(value)
        return index[key]
    source_fields=('variable','source_longitude','source_latitude','source_time','source_value','uncertainty')
    connection_fields=('method','connection_waypoints','connection_expansions','connection_spacing_m','source_search_truncated')
    segments=deepcopy(result['estimated_segments'])
    for segment in segments:
        for sample in segment['samples']:
            sample['longitude'],sample['latitude']=INVERSE.transform(sample['position']['east'],sample['position']['north'])
            refs=[]
            for original in sample.pop('estimates'):
                record=dict(original)
                source={k:record.pop(k) for k in source_fields}
                connection={k:record.pop(k) for k in connection_fields}
                record.update(source=intern(source,sources,indexes[0]),connection=intern(connection,connections,indexes[1]))
                refs.append(intern(record,records,indexes[2]))
            sample['estimate_refs']=refs
    routes=[]
    for candidate in result['comparison']['candidates']:
        if (candidate['status']!='arrived' or not candidate['destination_reached']
                or candidate['arrival_weather_status']!='passed_at_arrival'):
            continue
        own=[s for s in segments if s['candidate']==candidate['candidate']['name']]
        if not own:raise ValueError('Accepted coastal segments required')
        path=[[s['samples'][0]['longitude'],s['samples'][0]['latitude']] for s in own]
        path.append([own[-1]['samples'][-1]['longitude'],own[-1]['samples'][-1]['latitude']])
        waypoints=[path[0],*[list(INVERSE.transform(p['east'],p['north'])) for p in candidate['candidate']['waypoints']],
                   list(INVERSE.transform(candidate['target']['east'],candidate['target']['north']))]
        routes.append({**{k:deepcopy(candidate[k]) for k in ('status','arrival_weather_status','weather_segment_status',
            'departure_time','arrival_time','travel_seconds','distance_m','comfort_exposure','weather_summary')},
            'id':candidate['candidate']['name'],'path':path,'waypoints':waypoints,'segment_count':len(own),
            'result_qualification':'estimated_high_uncertainty','weather_limits_verified':False})
    if not routes:raise ValueError('No arrived coastal estimate to present')
    return {'schema':1,'profile':result['profile'],'input_sha256':result['input_sha256'],
        'full_result_sha256':sha256(canonical(result).encode()).hexdigest(),
        'full_result_hash_format':'application.planning.canonical UTF-8, no newline',
        'result_qualification':'estimated_high_uncertainty','weather_limits_verified':False,
        'routes':routes,'provenance':deepcopy(result['provenance']),'configuration':deepcopy(result['configuration']),
        'land_margin_m':result['land_margin_m'],'source_value_bounds':result['source_value_bounds'],
        'reserve_evidence':{'sources':sources,'connections':connections,'records':records,'segments':segments}}


def restore_estimates(view,sample):
    evidence=view['reserve_evidence'];result=[]
    for ref in sample['estimate_refs']:
        record=dict(evidence['records'][ref]);source=record.pop('source');connection=record.pop('connection')
        result.append({**record,**evidence['sources'][source],**evidence['connections'][connection]})
    return result
