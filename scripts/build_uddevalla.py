"""Freeze the acquired regional source evidence for the existing PoC.

This is data preflight, not a second routing engine. Missing interpolation
corners block route simulation and GPX; no nearest-node or zero substitution.
"""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
import xarray as xr
from pyproj import Geod

from scripts.audit_met_metadata import axis,matrix,numbers,PROJ4
from scripts.fetch_uddevalla import inspect_marine,capture_met,utc
from infrastructure.native_wind import NativeWindSample
from infrastructure.met_wind_segments import NativeMetWind
from infrastructure.copernicus_fields import wave_node,current_node
from prototype.forecast_data import axis_cell

ROOT=Path(__file__).resolve().parents[1]


def wind_sample(directory,request):
    inventory=capture_met(directory.parent,request,32_000_000)
    bounds=inventory['native_subset'];nx=bounds['x_last']-bounds['x_first']+1;ny=bounds['y_last']-bounds['y_first']+1
    text=(directory/'wind.txt').read_text();coords=(directory/'coordinates.txt').read_text();axes=(directory/'axes.txt').read_text();planes={}
    times=tuple(utc(t) for t in inventory['times'])
    for name in ('wind_speed_10m','wind_direction_10m'):
        blocks=re.findall(r'^'+name+r'\.'+name+rf'\[31\]\[{ny}\]\[{nx}\]\n(.*?)\n\n',text,re.M|re.S)
        if len(blocks)!=1 or len(blocks[0].splitlines())!=31*ny:raise ValueError('Exact native wind shape required')
        rows=[]
        for i,line in enumerate(blocks[0].splitlines()):
            label,separator,row=line.partition(',')
            if not separator or label!=f'[{i//ny}][{i%ny}]':raise ValueError('Native wind row order changed')
            values=numbers(row,nx)
            if min(values)<0 or (name=='wind_direction_10m' and max(values)>360):raise ValueError('Invalid physical wind')
            rows.append(values)
        planes[name]=tuple(tuple(rows[t*ny:(t+1)*ny]) for t in range(31))
        if axis(text,name+'.time',31)!=tuple(Decimal(int(t.timestamp())) for t in times):raise ValueError('Wind validity changed')
        for dim,count,first,last in (('x',1796,bounds['x_first'],bounds['x_last']),('y',2321,bounds['y_first'],bounds['y_last'])):
            if axis(text,name+'.'+dim,last-first+1)!=axis(axes,dim,count)[first:last+1]:raise ValueError('Wind axis mismatch')
    hashes=json.loads((directory/'sources.json').read_text())
    return NativeWindSample(PROJ4,axis(axes,'x',1796)[bounds['x_first']:bounds['x_last']+1],
        axis(axes,'y',2321)[bounds['y_first']:bounds['y_last']+1],times,planes['wind_speed_10m'],planes['wind_direction_10m'],
        tuple(tuple(row) for row in matrix(coords,'land_area_fraction',ny,nx)),utc(request['reference_time']),
        tuple((name,entry['sha256']) for name,entry in sorted(hashes.items())))


def marine_probe(ds,mask,product,point):
    """Use the existing component normalization and all four OWN grid corners."""
    i,fx=axis_cell(tuple(ds.longitude.values),point['longitude']);j,fy=axis_cell(tuple(ds.latitude.values),point['latitude'])
    names=('VHM0','VTM02','VMDR') if product=='waves' else ('uo','vo')
    fields={name:ds[name].squeeze('depth',drop=True) if 'depth' in ds[name].dims else ds[name] for name in names}
    result=[]
    for k in range(ds.sizes['time']):
        nodes=[]
        for dy in (0,1):
            row=[]
            for dx in (0,1):
                raw=[float(fields[n].isel(time=k,latitude=j+dy,longitude=i+dx)) if np.isfinite(fields[n].isel(time=k,latitude=j+dy,longitude=i+dx)) else None for n in names]
                node=wave_node(*raw,float(mask.isel(latitude=j+dy,longitude=i+dx))) if product=='waves' else current_node(*raw)
                row.append(node)
            nodes.append(row)
        missing=sum(node is None for row in nodes for node in row)
        if missing:result.append({'value':None,'missing_corners':missing});continue
        value=[sum(nodes[dy][dx][component]*(fy if dy else 1-fy)*(fx if dx else 1-fx) for dy in (0,1) for dx in (0,1)) for component in range(len(nodes[0][0]))]
        result.append({'value':[float(v) for v in value],'missing_corners':0})
    return {'stencil':{'longitude':ds.longitude.values[i:i+2].tolist(),'latitude':ds.latitude.values[j:j+2].tolist()},'samples':result}


def coastline_display(path,bbox):
    root=ET.parse(path).getroot();nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')};features=[];candidates=[]
    w,s,e,n=bbox
    for way in root.findall('way'):
        points=[nodes[v.attrib['ref']] for v in way.findall('nd')]
        if not any(w<=x<=e and s<=y<=n for x,y in points):continue
        candidates.append(points)
    # Largest coastline chains only for a lightweight display. Full acquisition
    # remains untouched; this selected display never becomes route obstacles.
    candidates.sort(key=lambda pts:(max(x for x,y in pts)-min(x for x,y in pts))+(max(y for x,y in pts)-min(y for x,y in pts)),reverse=True)
    for points in candidates[:250]:
        selected=points if len(points)<24 else [*points[::24],points[-1]]
        features.append({'type':'Feature','properties':{'kind':'source_coastline_display_only'},'geometry':{'type':'LineString','coordinates':[[round(x,6),round(y,6)] for x,y in selected]}})
    return {'type':'FeatureCollection','features':features}


def build(directory):
    directory=Path(directory);request=json.loads((directory/'request.json').read_text());inventory=inspect_marine(directory/'marine',request);sample=wind_sample(directory/'met',request);wind=NativeMetWind(sample)
    probes={name:{'position':request[name],'wind':[{'east_m_s':(v:=wind.at(request[name]['longitude'],request[name]['latitude'],t)).east,'north_m_s':v.north,'speed_m_s':v.speed} for t in sample.times]} for name in ('start','target')}
    products={}
    with xr.open_dataset(directory/'marine/wave-mask.nc',engine='h5netcdf') as static:
        for product,field in (('waves','VHM0'),('current','uo')):
            with xr.open_dataset(directory/f'marine/{product}.nc',engine='h5netcdf') as ds:
                expected_times=np.array([np.datetime64(t.replace(tzinfo=None),'s') for t in sample.times])
                if not np.array_equal(ds.time.values,expected_times):raise ValueError('Exact common wind/marine times required')
                if product=='waves' and (not np.array_equal(ds.longitude.values,static.longitude.values) or not np.array_equal(ds.latitude.values,static.latitude.values)):
                    raise ValueError('Wave mask must use the exact own wave grid')
                for name in probes:probes[name][product]=marine_probe(ds,static['mask'],product,request[name])
                names=('VHM0','VTM02','VMDR') if product=='waves' else ('uo','vo')
                valid=np.logical_and.reduce([np.isfinite(ds[name].squeeze().values).all(axis=0) for name in names])
                if product=='waves':valid=valid & (static['mask'].values==1)
                products[product]={'longitude':ds.longitude.values.tolist(),'latitude':ds.latitude.values.tolist(),'node_valid_all_times':valid.tolist(),
                    'units':{n:v['units'] for n,v in inventory['products'][product]['variables'].items()},'coverage':inventory['products'][product]['coverage']}
    blockers=[]
    for name,probe in probes.items():
        for product in ('waves','current'):
            failed=[i for i,v in enumerate(probe[product]['samples']) if v['value'] is None]
            if failed:blockers.append({'kind':'missing_interpolation_corners','place':name,'product':product,'failed_time_count':len(failed),'time_indices':failed,'stencil':probe[product]['stencil']})
    if not blockers:raise ValueError('This blocked-case publication requires actual missing endpoint support; run qualified regional planning instead')
    files=['met/'+n for n in json.loads((directory/'met/sources.json').read_text())]+['marine/waves.nc','marine/current.nc','marine/wave-mask.nc','land/coastline.osm']
    source_hashes={n:sha256((directory/n).read_bytes()).hexdigest() for n in files}
    _,_,distance=Geod(ellps='WGS84').inv(request['start']['longitude'],request['start']['latitude'],request['target']['longitude'],request['target']['latitude'])
    return {'schema':1,'case':'vinga-uddevalla','reference_time':request['reference_time'],'valid_times':list(inventory['common_times']),
        'bbox':request['bbox'],'planning_area':request['planning_area'],'probes':probes,'products':products,'blockers':blockers,
        'route_status':'blocked_at_data_preflight','routing_performed':False,'gpx_available':False,'travel_seconds':None,'comfort_exposure':None,
        'straight_line_distance_m':distance,'straight_line_scope':'Fågelvägsavstånd, inte en beräknad eller farbar rutt.',
        'land_inventory':json.loads((directory/'land/inventory.json').read_text()),'coastline_display':coastline_display(directory/'land/coastline.osm',request['bbox']),
        'source_sha256':source_hashes,'assumptions':request['assumptions']+[
            'Regionalt uttag med 30 timmars giltighet. Källutfärdande och körförenlighet är fortfarande overifierade.',
            'Båtprofil: befintlig uppskattad konstantfart 5 kn. Ingen restid eller komfort beräknas när dataförkontrollen blockerar.',
            'Brun kustlinje är ett urval av 250 större kedjor, förenklat enbart för visning. Det fullständiga uttaget är bevarat. Öppna kustkedjor är inte slutna routingpolygoner. Djup och fullständighet är okända.',
            'Befintlig bilinjär marin interpolation kräver alla fyra egna gridhörn. Närmaste värde eller noll ersätter aldrig en lucka.',
            'Sökningen startas inte när måldata saknas. Nuvarande lokala sök- och landgränser har inte lyfts eller kringgåtts för detta exempel.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,default=ROOT/'fixtures/vinga-uddevalla-preflight.json');a=p.parse_args()
    result=build(a.directory);a.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    print('REGIONAL_PREFLIGHT',len(result['valid_times']),'timesteps',len(result['blockers']),'blockers',a.output.stat().st_size,'public bytes')
