"""Offline candidate sensitivity; same frozen dataset and clock, never API input."""
import json
from application.geographic_plan import scene,calculate_geographic


def audit():
    s=scene('vinga');a,b=s['start'],s['target']
    payload={'profile':'vinga','start':{'latitude':a[1],'longitude':a[0]},'target':{'latitude':b[1],'longitude':b[0]},'margin_m':10}
    reports=[]
    for limit in (2,8):
        r=calculate_geographic(payload,audit_candidate_limit=limit)
        departures=[]
        for d in r['planning']['comparison']['departures']:
            routes=d['routes'];by_name={a['candidate']['name']:a for a in routes['candidates']}
            def selected(name):
                result=by_name.get(name)
                return None if result is None else {'candidate':result['candidate']} | {k:result[k] for k in ('travel_seconds','comfort_exposure','arrival_time')}
            departures.append({'departure':d['departure_time'],'fastest':selected(routes['fastest_candidate']),
                               'comfortable':selected(routes['comfortable_candidate'])})
        reports.append({'candidate_limit':limit,'input_sha256':r['input_sha256'],'dataset_id':r['planning']['manifest']['dataset_id'],
                        'dataset_version':r['planning']['manifest']['dataset_version'],'search_status':r['geometry_search']['status'],
                        'truncated':r['geometry_search']['truncated'],'departures':departures})
    return {'synthetic_weather':True,'scope':'Endast denna frysta fixture, graf och två avgångar; inte global optimalitet.', 'reports':reports}

if __name__=='__main__':
    print(json.dumps(audit(),sort_keys=True,ensure_ascii=False))
