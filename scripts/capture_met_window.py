"""Capture one bounded archived MET native window, preserving unknown issuance.

Transport only; the existing strict metadata/sample reader validates the same
DDS/DAS, axes and field semantics before this snapshot is admitted.
"""
import argparse
from datetime import date,datetime,timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request
from scripts.probe_forecast_metadata import MET_OPENER
from scripts.audit_met_metadata import read_wind_sample


def capture(output, reference_date):
    day=date.fromisoformat(reference_date)
    if day>datetime.now(timezone.utc).date():raise ValueError('Archived reference date required')
    output=Path(output)
    if output.exists():raise ValueError('Existing snapshot must be reused, never fetched again')
    base=f'https://thredds.met.no/thredds/dodsC/metpparchive/{day:%Y/%m/%d}/met_forecast_1_0km_nordic_{day:%Y%m%d}T00Z.nc'
    xf,xl,yf,yl,tf,tl=690,700,507,518,1,12
    coords=f'[{yf}:1:{yl}][{xf}:1:{xl}]'
    queries={'met-forecast.dds':'.dds','met-forecast.das':'.das',
        'met-time-coordinates.txt':'.ascii?'+quote('forecast_reference_time,time',safe=','),
        'native-axes.txt':'.ascii?x,y',
        'vinga-latlon.txt':'.ascii?'+quote(','.join(n+coords for n in ('latitude','longitude')),safe=','),
        'native-wind-land.txt':'.ascii?'+quote(','.join(n+f'[{tf}:1:{tl}]'+coords for n in ('wind_speed_10m','wind_direction_10m'))+',land_area_fraction'+coords+',forecast_reference_time',safe=',')}
    metadata=output/'met-nordic-metadata';wind=output/'met-nordic-wind-sample'
    metadata.mkdir(parents=True);wind.mkdir()
    entries=[];wind_entry=None;total=0
    for name,suffix in queries.items():
        url=base+suffix;limit=128000 if name=='native-wind-land.txt' else 512000
        limit=min(limit,1000000-total)
        if limit<=0:raise ValueError('MET total response byte budget exhausted')
        req=Request(url,headers={'User-Agent':'SeaParser-source-audit/0.1 (+https://seaparser.com)','Accept-Encoding':'identity'})
        with MET_OPENER.open(req,timeout=15) as response:data=response.read(limit+1)
        total+=len(data)
        if len(data)>limit or total>1000000 or not data.decode().lstrip().startswith('Attributes {' if name.endswith('.das') else 'Dataset {'):
            raise ValueError('MET response envelope or byte budget failed')
        destination=wind if name=='native-wind-land.txt' else metadata
        (destination/name).write_bytes(data)
        entry=dict(filename=name,url=url,bytes=len(data),sha256=sha256(data).hexdigest())
        if name=='native-wind-land.txt':wind_entry=entry
        else:entries.append(entry)
    now=datetime.now(timezone.utc).isoformat()
    subset=dict(x_first=xf,x_last=xl,y_first=yf,y_last=yl)
    (metadata/'manifest.json').write_text(json.dumps(dict(schema=1,scope='metadata_only',files=entries,
        coordinate_subset=subset,observed_at=now,issued_at=None),indent=2)+'\n')
    (wind/'manifest.json').write_text(json.dumps(dict(schema=1,scope='raw_native_wind_sample_not_routing_qualified',
        **wind_entry,observed_at=now,subset=subset|dict(time_first=tf,time_last=tl),issued_at=None,
        attribution='Norwegian Meteorological Institute, met.no',
        license_url='https://www.met.no/en/free-meteorological-data/Licensing-and-crediting'),indent=2)+'\n')
    expected=Decimal(int(datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).timestamp()))
    snapshot=read_wind_sample(wind,metadata,expected_reference=expected)
    return dict(bytes=total,time_count=len(snapshot[3]),node_count=len(snapshot[2]['x'])*len(snapshot[2]['y']),
                model_reference_time=day.isoformat()+'T00:00:00Z',issued_at=None,source_qualification='unverified')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--reference-date',required=True)
    a=p.parse_args()
    try:print('MET_WINDOW_CAPTURED',json.dumps(capture(a.output,a.reference_date)))
    except Exception as e:
        print('MET_WINDOW_BLOCKED',type(e).__name__);raise SystemExit(1)
