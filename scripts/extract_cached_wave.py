"""Derive a bounded native WAV subset from an already hash-verified original.

No network, interpolation, relabeling of times, or routing adapter. Original
producer time labels and unknown run/issuance/ARCO lineage remain separate.
"""
import argparse
from datetime import datetime, timezone
import json
from hashlib import sha256
from io import BytesIO
from math import isfinite
from pathlib import Path

from infrastructure.copernicus_fields import WAVE_FIELDS, validate_fields
from scripts.copernicus_budget import cached_entry, digest
from scripts.manifest_json import manifest_json


def extract(manifest_path, cache, output, bbox, start, end):
    import numpy as np
    import xarray as xr
    west,south,east,north=bbox
    if (any(not isfinite(v) for v in bbox) or not 11.4 <= west < east <= 11.8
            or not 57.5 <= south < north <= 57.8 or east-west > .2 or north-south > .2):
        raise ValueError('Bounded reviewed Vinga region required')
    times=[datetime.fromisoformat(t.replace('Z','+00:00')) for t in (start,end)]
    if any(t.tzinfo is None for t in times) or not 0 < (times[1]-times[0]).total_seconds() <= 86400:
        raise ValueError('Explicit ordered window of at most one day required')
    with Path(manifest_path).open('rb') as stream:manifest_data=stream.read(512001)
    if len(manifest_data)>512000:raise ValueError('Original manifest budget exceeded')
    manifest=manifest_json(manifest_data)
    if (manifest.get('scope')!='original_file_diagnostic' or manifest.get('dataset_id')!='cmems_mod_bal_wav_anfc_PT1H-i'
            or manifest.get('dataset_version')!='202311' or manifest.get('dataset_part')!='default'):
        raise ValueError('Reviewed original WAV manifest required')
    identity=dict(kind='original',dataset_id=manifest['dataset_id'],dataset_version=manifest['dataset_version'],
                  dataset_part=manifest['dataset_part'],**manifest['source'])
    directory=Path(cache)/manifest['cache_key']
    record=cached_entry(directory,identity,float('inf'))
    if record is None or record['sha256']!=manifest['sha256']:
        raise ValueError('Original cache hash/identity mismatch')
    with (directory/'data.nc').open('rb') as stream:data=stream.read(200_000_001)
    if len(data)>200_000_000 or sha256(data).hexdigest()!=record['sha256']:
        raise ValueError('Original captured bytes exceed budget or mismatch cache hash')
    with xr.open_dataset(BytesIO(data),engine='h5netcdf',decode_cf=False) as raw:
        validate_fields({n:raw[n].attrs for n in WAVE_FIELDS},WAVE_FIELDS)
        for name in WAVE_FIELDS:
            if raw[name].dims!=('time','lat','lon') or any(k in raw[name].attrs for k in ('scale_factor','add_offset','_Unsigned')):
                raise ValueError('Reviewed unpacked original axes required')
        if raw.lat.attrs.get('units')!='degrees_north' or raw.lon.attrs.get('units')!='degrees_east':
            raise ValueError('Native geographic coordinate units required')
        for name in ('lat','lon'):
            axis=raw[name].values
            if axis.ndim!=1 or not np.isfinite(axis).all() or not (np.diff(axis)>0).all():
                raise ValueError('Finite increasing native coordinate axes required')
        decoded=xr.decode_cf(raw[['time']]).time.values
        requested=[np.datetime64(t.astimezone(timezone.utc).replace(tzinfo=None),'s') for t in times]
        if (decoded.dtype.kind!='M' or np.isnat(decoded).any() or not np.array_equal(decoded,decoded.astype('datetime64[s]'))
                or not (np.diff(decoded)==np.timedelta64(1,'h')).all()):
            raise ValueError('Unambiguous increasing decoded Gregorian times required')
        indices={'lon':np.flatnonzero((raw.lon.values>=west)&(raw.lon.values<=east)),
                 'lat':np.flatnonzero((raw.lat.values>=south)&(raw.lat.values<=north)),
                 'time':np.flatnonzero((decoded>=requested[0])&(decoded<=requested[1]))}
        if (any(len(indices[n])<2 for n in indices) or len(indices['time'])>25
                or len(indices['lat'])*len(indices['lon'])>10000
                or decoded[indices['time'][0]]!=requested[0] or decoded[indices['time'][-1]]!=requested[1]):
            raise ValueError('Requested complete bounded time support and native nodes required')
        subset=raw[list(WAVE_FIELDS)].isel(**indices).load()
        # Renaming coordinates is lossless; values and producer time labels remain untouched.
        subset=subset.rename({'lat':'latitude','lon':'longitude'})
        output=Path(output);output.mkdir(parents=True,exist_ok=False)
        path=output/'waves.nc';subset.to_netcdf(path,engine='h5netcdf')
    report=dict(schema=1,scope='local_original_native_subset',source_qualification='unverified',
        result_qualification='diagnostic_only',issued_at=None,model_run_id=None,arco_lineage_verified=False,
        parent_manifest_sha256=sha256(manifest_data).hexdigest(),parent_original_sha256=record['sha256'],
        parent_cache_key=manifest['cache_key'],retrieved_at=record['retrieved_at'],
        derived_at=datetime.now(timezone.utc).isoformat(),bbox=list(bbox),start=start,end=end,
        variables=list(WAVE_FIELDS),dimensions=dict(subset.sizes),filename=path.name,
        sha256=digest(path),actual_result_bytes=path.stat().st_size,estimated_transfer_bytes_this_run=0,
        time_label_policy='Unchanged producer CF time coordinates; no ARCO offset or issue time inferred',
        attribution='Generated using E.U. Copernicus Marine Service Information; DOI: 10.48670/moi-00010',
        license_url='https://marine.copernicus.eu/user-corner/service-commitments-and-license')
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--cache',type=Path,default=Path('/tmp/seaparser-copernicus-cache'))
    p.add_argument('--bbox',type=float,nargs=4,required=True);p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    args=p.parse_args();r=extract(args.manifest,args.cache,args.output,args.bbox,args.start,args.end)
    print('LOCAL_SUBSET_COMPLETE',r['dimensions'],'bytes',r['actual_result_bytes'],'transfer_bytes',0)
