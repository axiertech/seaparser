"""Capture real source inputs for Vinga–Uddevalla; never invent or publish routes.

Reuse MET metadata validation and the existing Copernicus downloader/cache.
An immutable request permits interrupted runs to resume without new forecasts.
"""
import argparse
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote,urlencode
from urllib.request import Request
import xml.etree.ElementTree as ET

from scripts.probe_forecast_metadata import MET_OPENER
from scripts.audit_met_metadata import axis,field_metadata,geometry_metadata,time_metadata,PROJ4
from scripts.copernicus_budget import digest
from infrastructure.copernicus_fields import CURRENT_FIELDS,WAVE_FIELDS,BATHY_FIELDS,validate_fields

ROOT=Path(__file__).resolve().parents[1]
BBOX=(11.0,57.45,12.2,58.6)
INNER=(11.10,57.55,12.10,58.50)
USER_AGENT='SeaParser-development/0.1 (+https://seaparser.com)'


def utc(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Explicit UTC offset required')
    return result.astimezone(timezone.utc)


def plan(departure=None,now=None):
    now=now or datetime.now(timezone.utc)
    start=utc(departure) if departure else now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=2)
    if start.minute or start.second or start.microsecond:raise ValueError('Whole-hour departure required')
    reference=now.replace(hour=0,minute=0,second=0,microsecond=0)
    if start<reference or start+timedelta(hours=30)>reference+timedelta(hours=58):raise ValueError('Departure and 30-hour window must fit the selected MET reference')
    return dict(schema=1,case='vinga-uddevalla',bbox=list(BBOX),planning_area=list(INNER),
        reference_time=reference.isoformat(),departure=start.isoformat(),end=(start+timedelta(hours=30)).isoformat(),
        boat_profile='constant-5kn',estimated_boat=True,
        start={'longitude':11.613,'latitude':57.633,'label':'Vinga, preliminär vattenpunkt öster om ön'},
        target={'longitude':11.900,'latitude':58.337,'label':'Uddevalla / Byfjorden, preliminär vattenpunkt'},
        assumptions=['Start och mål måste verifieras mot nytt landunderlag innan beräkning.',
            'Modellreferens är inte verifierad utfärdandetid; körförenlighet måste redovisas separat.',
            'Våg- och strömmasker gäller var sin produkt. Saknade värden får inte fyllas med noll.',
            'Ingen utökning av nuvarande 900m-routing sker genom datahämtningen.'],routing_enabled=False)


def cached_fetch(base,name,url,*,limit,data=None,timeout=90,validator=None):
    """Hash-checked frozen responses; partial responses never become cache hits."""
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    index=base/'sources.json';entries=json.loads(index.read_text()) if index.exists() else {}
    identity=sha256(url.encode()+b'\0'+(data or b'')).hexdigest();target=base/name
    if name in entries:
        entry=entries[name]
        if entry['request_sha256']!=identity or not target.is_file() or target.is_symlink() or target.stat().st_size!=entry['bytes'] or digest(target)!=entry['sha256']:raise ValueError('Existing source changed; preserving it and stopping')
        body=target.read_bytes()
        if validator:validator(body)
        print('SOURCE_CACHE_HIT',name,flush=True);return body
    if target.exists() or target.is_symlink():raise ValueError('Unindexed source exists; never overwrite it')
    request=Request(url,data=data,headers={'User-Agent':USER_AGENT,'Accept-Encoding':'identity'})
    with MET_OPENER.open(request,timeout=timeout) as response:body=response.read(limit+1)
    if len(body)>limit:raise ValueError('Source response exceeds configured byte budget')
    if validator:validator(body)
    with tempfile.NamedTemporaryFile(prefix=target.name+'.partial-',dir=base,delete=False) as stream:
        stream.write(body);temporary=Path(stream.name)
    temporary.replace(target)
    entries[name]=dict(url=url,request_sha256=identity,bytes=len(body),sha256=sha256(body).hexdigest(),retrieved_at=datetime.now(timezone.utc).isoformat())
    pending=index.with_suffix('.tmp');pending.write_text(json.dumps(entries,indent=2,sort_keys=True)+'\n');pending.replace(index)
    print('SOURCE_CAPTURED',name,len(body),flush=True);return body


def native_window(xs,ys,bbox):
    from bisect import bisect_left,bisect_right
    from pyproj import CRS,Transformer
    transform=Transformer.from_crs('EPSG:4326',CRS.from_proj4(PROJ4),always_xy=True)
    w,s,e,n=bbox
    border=[(w+(e-w)*i/100,lat) for i in range(101) for lat in (s,n)]+[(lon,s+(n-s)*i/100) for i in range(101) for lon in (w,e)]
    positions=[transform.transform(lon,lat,errcheck=True) for lon,lat in border]
    bounds=[]
    for dimension,values in enumerate((xs,ys)):
        low=bisect_right(values,min(p[dimension] for p in positions))-3
        high=bisect_left(values,max(p[dimension] for p in positions))+2
        if low<0 or high>=len(values):raise ValueError('Requested area outside native MET grid')
        bounds.extend((low,high))
    return tuple(bounds)


def capture_met(output,request,limit):
    directory=Path(output)/'met';reference=utc(request['reference_time'])
    base=f'https://thredds.met.no/thredds/dodsC/metpparchive/{reference:%Y/%m/%d}/met_forecast_1_0km_nordic_{reference:%Y%m%d}T00Z.nc'
    def envelope(body):
        if not body.decode().lstrip().startswith(('Dataset {','Attributes {')):raise ValueError('Unexpected MET response')
    get=lambda name,suffix,cap=1_000_000:cached_fetch(directory,name,base+suffix,limit=cap,validator=envelope).decode()
    dds=get('forecast.dds','.dds');das=get('forecast.das','.das')
    times=get('times.txt','.ascii?forecast_reference_time,time');axes=get('axes.txt','.ascii?x,y')
    field_metadata(das);geometry_metadata(das);time_metadata(dds,das,times,expected_reference=Decimal(int(reference.timestamp())))
    xs,ys=([float(v) for v in axis(axes,k,count)] for k,count in (('x',1796),('y',2321)))
    xf,xl,yf,yl=native_window(xs,ys,request['bbox'])
    native_times=[datetime.fromtimestamp(int(t),timezone.utc) for t in axis(times,'time',59)]
    selected=[i for i,t in enumerate(native_times) if utc(request['departure'])<=t<=utc(request['end'])]
    if len(selected)!=31:raise ValueError('Exact 31-hour native forecast window missing')
    coordinates=f'[{yf}:1:{yl}][{xf}:1:{xl}]';temporal=f'[{selected[0]}:1:{selected[-1]}]'
    query=','.join(name+coordinates for name in ('latitude','longitude','land_area_fraction'))
    get('coordinates.txt','.ascii?'+quote(query,safe=','),limit)
    query=','.join(name+temporal+coordinates for name in ('wind_speed_10m','wind_direction_10m'))+',forecast_reference_time'
    body=get('wind.txt','.ascii?'+quote(query,safe=','),limit)
    references=re.findall(r'^forecast_reference_time, ([^\n]+)$',body,re.M)
    if len(references)!=1 or Decimal(references[0])!=Decimal(int(reference.timestamp())):raise ValueError('Frozen wind model reference changed')
    report=dict(native_subset=dict(x_first=xf,x_last=xl,y_first=yf,y_last=yl,time_first=selected[0],time_last=selected[-1]),
        times=[native_times[i].isoformat() for i in selected],issued_at=None,source_qualification='unverified',routing_enabled=False)
    (directory/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');return report


def capture_land(output,request,limit):
    w,s,e,n=request['bbox'];query=f'[out:xml][timeout:180][maxsize:{limit}];way["natural"="coastline"]({s},{w},{n},{e});(._;>;);out meta;'
    def envelope(body):
        root=ET.fromstring(body)
        if root.tag!='osm' or root.find('remark') is not None:raise ValueError('Incomplete Overpass response')
    body=cached_fetch(Path(output)/'land','coastline.osm','https://overpass-api.de/api/interpreter',limit=limit,data=urlencode({'data':query}).encode(),timeout=210,validator=envelope)
    root=ET.fromstring(body)
    if root.tag!='osm' or root.find('remark') is not None:raise ValueError('Incomplete Overpass response')
    nodes={node.attrib['id'] for node in root.findall('node')};ways=root.findall('way')
    if not ways or any(not way.findall('nd') or any(ref.attrib['ref'] not in nodes for ref in way.findall('nd')) for way in ways):raise ValueError('Missing complete coastline source nodes')
    report=dict(source='OpenStreetMap contributors',license='ODbL-1.0',node_count=len(nodes),way_count=len(ways),
        closed_individual_ways=sum(way.findall('nd')[0].attrib['ref']==way.findall('nd')[-1].attrib['ref'] for way in ways),
        completeness='unknown',polygonization_required=True,notice='Mainland open chains must be assembled/clipped with verified land topology, never dropped or closed by an invented straight line.',routing_enabled=False)
    (Path(output)/'land/inventory.json').write_text(json.dumps(report,indent=2)+'\n');return report


def capture_marine(output,request,args):
    directory=Path(output)/'marine'
    manifest=directory/'manifest.json'
    if directory.exists() and (not manifest.exists() or {f['product'] for f in json.loads(manifest.read_text()).get('files',[])}!={'waves','current','wave-mask'}):
        saved=directory.with_name('marine-incomplete-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));directory.rename(saved)
        print('PARTIAL_MARINE_PRESERVED',saved.name,flush=True)
    if not manifest.exists():
        command=[sys.executable,'-B','-m','scripts.download_copernicus','--output',str(directory),'--bbox',*[str(v) for v in request['bbox']],
            '--start',request['departure'],'--end',request['end'],'--cache',str(args.cache),'--file-budget-gb',str(args.file_budget_gb),
            '--transfer-budget-gb',str(args.transfer_budget_gb),'--total-transfer-budget-gb',str(args.total_transfer_budget_gb)]
        environment=os.environ.copy()
        for key in ('COPERNICUSMARINE_SERVICE_USERNAME','COPERNICUSMARINE_SERVICE_PASSWORD'):environment.pop(key,None)
        subprocess.run(command,cwd=ROOT,env=environment,check=True,stdin=subprocess.DEVNULL)
    return inspect_marine(directory,request)


def inspect_marine(directory,request):
    import numpy as np
    import xarray as xr
    from scripts.audit_copernicus import coordinate
    manifest=json.loads((directory/'manifest.json').read_text());products={};common=None
    expected={'waves':WAVE_FIELDS,'current':CURRENT_FIELDS,'wave-mask':BATHY_FIELDS}
    if {f['product'] for f in manifest['files']}!=set(expected):raise ValueError('Incomplete marine capture; preserve it and resume through the existing cache')
    for entry in manifest['files']:
        path=directory/entry['filename']
        if path.name!=entry['filename'] or path.is_symlink() or digest(path)!=entry['sha256']:raise ValueError('Marine snapshot changed')
        with xr.open_dataset(path,engine='h5netcdf',decode_cf=True,mask_and_scale=True) as ds:
            validate_fields({name:v.attrs for name,v in ds.data_vars.items()},expected[entry['product']])
            lon,lat=coordinate(ds,'longitude'),coordinate(ds,'latitude')
            for axis_value,units in ((lon,'degrees_east'),(lat,'degrees_north')):
                if axis_value.attrs.get('units')!=units or len(axis_value)<2 or not np.isfinite(axis_value.values).all() or not (np.diff(axis_value.values)>0).all():raise ValueError('Unsupported native geographic axis')
            w,s,e,n=request['planning_area']
            if not (float(lon.min())<=w<e<=float(lon.max()) and float(lat.min())<=s<n<=float(lat.max())):raise ValueError('Marine source does not enclose the planning area')
            report={'coverage':dict(west=float(lon.min()),east=float(lon.max()),south=float(lat.min()),north=float(lat.max())),'variables':{name:dict(dimensions=list(ds[name].dims),shape=list(ds[name].shape),missing=int((~np.isfinite(ds[name].values)).sum()),count=int(ds[name].size),units=ds[name].attrs.get('units'),cell_methods=ds[name].attrs.get('cell_methods')) for name in expected[entry['product']]},'issued_at':None}
            if entry['product']!='wave-mask':
                names=[k for k,v in ds.coords.items() if v.attrs.get('standard_name')=='time']
                if len(names)!=1:raise ValueError('Unambiguous native time coordinate required')
                if not np.issubdtype(ds[names[0]].dtype,np.datetime64):raise ValueError('Decoded UTC forecast times required')
                times=[str(t)+'+00:00' for t in ds[names[0]].values.astype('datetime64[s]')]
                report['times']=times;common=set(times) if common is None else common&set(times)
            products[entry['product']]=report
    needed={(utc(request['departure'])+timedelta(hours=i)).isoformat() for i in range(31)}
    if not needed<=common:raise ValueError('Marine products lack the entire requested common time window')
    result=dict(products=products,common_times=sorted(common),model_run_compatibility='unverified',routing_enabled=False)
    (directory/'inventory.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--departure');p.add_argument('--public-only',action='store_true');p.add_argument('--request-file',type=Path)
    p.add_argument('--cache',type=Path,default=Path('/tmp/seaparser-copernicus-cache'));p.add_argument('--file-budget-gb',type=float,default=2);p.add_argument('--transfer-budget-gb',type=float,default=10);p.add_argument('--total-transfer-budget-gb',type=float,default=20)
    p.add_argument('--met-response-mb',type=int,default=32);p.add_argument('--land-response-mb',type=int,default=64);a=p.parse_args(argv)
    if a.met_response_mb<=0 or a.land_response_mb<=0:raise ValueError('Positive configurable response budgets required')
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=True)
    filename=a.output/'request.json'
    request=json.loads(filename.read_text()) if filename.exists() else json.loads(a.request_file.read_text()) if a.request_file else plan(a.departure)
    if a.request_file and json.loads(a.request_file.read_text())!=request:raise ValueError('Configured request differs from existing frozen request')
    if a.departure and utc(a.departure)!=utc(request['departure']):raise ValueError('Existing frozen request has another departure; use a new output directory')
    if request.get('case')!='vinga-uddevalla' or request.get('bbox')!=list(BBOX):raise ValueError('Existing request identity differs')
    if not filename.exists():filename.write_text(json.dumps(request,indent=2)+'\n')
    status={'request':request,'started_at':datetime.now(timezone.utc).isoformat(),'phases':{},'routing_enabled':False}
    tasks=[('met',lambda:capture_met(a.output,request,a.met_response_mb*1_000_000)),('land',lambda:capture_land(a.output,request,a.land_response_mb*1_000_000))]
    if not a.public_only:tasks.append(('marine',lambda:capture_marine(a.output,request,a)))
    for label,task in tasks:
        try:status['phases'][label]={'status':'captured','inventory':task()}
        except Exception as error:status['phases'][label]={'status':'blocked','error_type':type(error).__name__};print('CAPTURE_BLOCKED',label,type(error).__name__,flush=True)
        (a.output/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    status['ended_at']=datetime.now(timezone.utc).isoformat();status['exit_code']=0 if all(v['status']=='captured' for v in status['phases'].values()) else 1
    if not status['exit_code'] and not a.public_only:
        met=set(status['phases']['met']['inventory']['times']);marine=set(status['phases']['marine']['inventory']['common_times']);status['common_times']=sorted(met&marine)
        if len(status['common_times'])!=31:status['exit_code']=1;status['common_time_blocker']='Exact shared forecast window missing'
    (a.output/'status.json').write_text(json.dumps(status,indent=2)+'\n');print('CAPTURE_FINISHED',status['exit_code'],str(a.output/'status.json'),'SOURCE_CAPTURE_ONLY; ROUTING_NOT_QUALIFIED',flush=True)
    return status['exit_code']


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:print('CORRIDOR_CAPTURE_FAILED',type(error).__name__,file=sys.stderr);raise SystemExit(1)
