"""Offline raw-source support inventory for an explicitly source-sphere segment."""
import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from application.native_wind_support import (
    SourceLocalSegment, SourceSphereSegment, inspect_native_segment, inspect_source_local_segment,
)
from infrastructure.native_wind_geometry import SOURCE_LOCAL_FRAME
from scripts.regional_forecast import load_native_wind


def read_segment(path):
    """Read one bounded, unambiguous mathematical review path, without weather I/O."""
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate segment key')
            result[key]=value
        return result
    with path.open('rb') as stream:
        data=stream.read(8193)
    if len(data)>8192:
        raise ValueError('Segment input exceeds budget')
    raw=json.loads(data,parse_float=Decimal,object_pairs_hook=unique)
    local=isinstance(raw,dict) and raw.get('coordinate_frame')==SOURCE_LOCAL_FRAME
    names=({'start_east_m','start_north_m','end_east_m','end_north_m'} if local else
           {'start_latitude','start_longitude','end_latitude','end_longitude'})
    expected=names|{'coordinate_frame','start_time','end_time'}
    if not isinstance(raw,dict) or set(raw)!=expected:
        raise ValueError('Explicit source-sphere segment fields required')
    for key in ('start_time','end_time'):
        raw[key]=datetime.fromisoformat(raw[key].replace('Z','+00:00'))
    return (SourceLocalSegment if local else SourceSphereSegment)(**raw)


def inspect_file(fixtures, path, max_cells=512):
    segment=read_segment(path)
    inspect=(inspect_source_local_segment if isinstance(segment,SourceLocalSegment) else inspect_native_segment)
    return inspect(load_native_wind(fixtures),segment,max_cells=max_cells)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=Path(__file__).resolve().parents[1]/'fixtures')
    parser.add_argument('--segment',required=True,type=Path)
    parser.add_argument('--max-cells',type=int,default=512)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    report=inspect_file(args.fixtures,args.segment,args.max_cells)
    args.output.write_text(json.dumps(report,default=str,sort_keys=True,indent=2)+'\n')
    print('NATIVE_SEGMENT_INVENTORY='+report['report_sha256']+'; routing remains data_unavailable')


if __name__=='__main__':
    main()
