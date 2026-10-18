"""Build a usable static PoC catalog using the real existing calculation engine.

No network, publication, new weather data or invented route values.
"""
import argparse
from copy import deepcopy
import json
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess

from application.geographic_plan import calculate_geographic,scene,compare_alternatives
from application.poc import DEPARTURES
from application.planning import canonical
from presentation.gpx import export_gpx
from deployment.prepare_vinga import PUBLIC_ASSETS

ROOT=Path(__file__).resolve().parents[1]


def compact(result):
    result=deepcopy(result)
    if result['planning']:
        result['planning']={'manifest':result['planning']['manifest']}
    return result


def build(output):
    output=Path(output).resolve()
    if output==Path('/home/web/seaparser/public') or Path('/home/web/seaparser/public') in output.parents:
        raise ValueError('Build outside the public webroot')
    subprocess.run(['node','frontend/build.mjs'],cwd=ROOT,check=True)
    output.mkdir(parents=True,exist_ok=True)
    generated=set()
    for name in PUBLIC_ASSETS:
        if name in ('index.html','main.mjs'):continue
        dst=output/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'frontend/dist'/name,dst);generated.add(name)
    for name in ('index.html','poc.css','poc-main.mjs','poc-transport.mjs','uddevalla-main.mjs'):
        shutil.copyfile(ROOT/'frontend/poc'/name,output/name);generated.add(name)
    shutil.copyfile(ROOT/'fixtures/vinga-uddevalla-preflight.json',output/'vinga-uddevalla.json');generated.add('vinga-uddevalla.json')
    model=scene('vinga-poc');(output/'scene.json').write_text(canonical(model)+'\n');generated.add('scene.json')
    (output/'bank').mkdir(exist_ok=True);(output/'gpx').mkdir(exist_ok=True)
    catalog={'schema':1,'source':'Existing real-data calculation engine; frozen results, not new calculations in the browser',
             'configuration':'settings/development-weather-projected-assumptions.json','cases':{}}
    for a in model['places']:
        for b in model['places']:
            if a['id']==b['id']:continue
            for preset in model['weather_presets']:
                key=a['id']+b['id']+'-'+preset['id']
                request={'profile':'vinga-poc','start':{k:a[k] for k in ('latitude','longitude')},
                    'target':{k:b[k] for k in ('latitude','longitude')},'candidate_limit':4,
                    'departure_offsets_seconds':list(DEPARTURES),'margin_m':10,'boat_profile':'constant-5kn',
                    'max_wind_m_s':preset['max_wind_m_s'],'max_wave_height_m':preset['max_wave_height_m']}
                result=calculate_geographic(request)
                result['comparisons']={'all':result['alternative_comparison']}
                for d in model['departure_options']:
                    subset=[r for r in result['alternatives'] if r['departure_time']==d['time']]
                    result['comparisons'][str(d['offset_seconds'])]=compare_alternatives(subset,300)
                for route in result['alternatives']:
                    if route['status']!='arrived':continue
                    try:content=export_gpx(result,route['id'])
                    except ValueError:continue
                    filename=f'gpx/{key}-{route["id"]}.gpx'
                    (output/filename).write_bytes(content);generated.add(filename)
                (output/'bank'/f'{key}.json').write_text(canonical(compact(result))+'\n')
                generated.add(f'bank/{key}.json')
                catalog['cases'][key]={'file':f'bank/{key}.json','input_sha256':result['input_sha256'],
                    'arrived':sum(r['status']=='arrived' for r in result['alternatives']),
                    'alternative_count':len(result['alternatives'])}
                print('POC_CASE',key,catalog['cases'][key]['arrived'],flush=True)
    (output/'catalog.json').write_text(canonical(catalog)+'\n')
    generated.add('catalog.json')
    (output/'build-receipt.json').write_text(canonical({'schema':1,'files':{n:sha256((output/n).read_bytes()).hexdigest() for n in sorted(generated)},'published':False})+'\n')
    return catalog


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'artifacts/poc-site')
    args=parser.parse_args();build(args.output)
