"""Offline WAV original/ARCO comparison; numeric matches never prove lineage.

Report exact native coordinate/value matches at equal times and the explicit
+1-hour producer-label hypothesis. Never regrid, infer issued_at, or plan routes.
"""
import argparse
import json
from pathlib import Path

from infrastructure.copernicus_fields import WAVE_FIELDS
from scripts.copernicus_budget import digest


def compare(original, arco):
    import numpy as np
    import xarray as xr
    with xr.open_dataset(original, engine='h5netcdf', decode_cf=False) as source, xr.open_dataset(
            arco, engine='h5netcdf', decode_cf=False) as target:
        for ds, lat, lon in ((source,'lat','lon'), (target,'latitude','longitude')):
            if any(name not in ds for name in (*WAVE_FIELDS, lat, lon, 'time')):
                raise ValueError('Reviewed WAV variables and native coordinates required')
            if ds.time.attrs.get('calendar', 'standard') not in ('standard','gregorian','proleptic_gregorian'):
                raise ValueError('Reviewed Gregorian time coordinates required')
            for name in WAVE_FIELDS:
                if ds[name].dims != ('time',lat,lon):
                    raise ValueError('Reviewed WAV dimension order required')
                if (ds[name].dtype != np.dtype('float32') or any(
                        k in ds[name].attrs for k in ('scale_factor','add_offset','_Unsigned'))
                        or ds[name].attrs.get('standard_name') != WAVE_FIELDS[name][0]
                        or ds[name].attrs.get('units') not in WAVE_FIELDS[name][1]):
                    raise ValueError('Reviewed unpacked float32 CF fields required')
        decoded = [xr.decode_cf(ds[['time']]).time.values for ds in (source,target)]
        if any(t.ndim != 1 or t.size == 0 or t.dtype.kind != 'M'
               or np.any(np.isnat(t)) or not np.array_equal(t,t.astype('datetime64[s]'))
               for t in decoded):
            raise ValueError('Nonempty whole-second decoded time axes required')
        st,tt = (t.astype('datetime64[s]') for t in decoded)
        if any(np.any(np.diff(t) <= np.timedelta64(0, 's')) for t in (st,tt)):
            raise ValueError('Strictly increasing valid-time coordinates required')
        indices = {}
        for native, subset in (('lat','latitude'),('lon','longitude')):
            index = []
            for value in target[subset].values:
                hits = np.flatnonzero(source[native].values == value)
                if len(hits) != 1:
                    raise ValueError('Exact unique native coordinate match required; no nearest-node fallback')
                index.append(int(hits[0]))
            indices[native] = index
        hypotheses = []
        for offset in (0,3600):
            pairs = []
            for ti, t in enumerate(tt):
                hits = np.flatnonzero(st == t + np.timedelta64(offset,'s'))
                if len(hits) == 1:
                    pairs.append((ti,int(hits[0])))
            fields = {}
            for name in WAVE_FIELDS:
                count = equal = fill = 0
                max_difference = None
                for ti,si in pairs:
                    a = source[name].isel(time=si,lat=indices['lat'],lon=indices['lon']).values
                    b = target[name].isel(time=ti).values
                    valid = np.isfinite(a) & np.isfinite(b)
                    for value,array in ((source[name].attrs.get('_FillValue'),a),
                                        (target[name].attrs.get('_FillValue'),b)):
                        if value is not None:
                            valid &= array != value
                    fill += int(np.sum(~valid))
                    count += int(np.sum(valid))
                    equal += int(np.sum((a == b) & valid))
                    if np.any(valid):
                        diff = float(np.max(np.abs(a[valid].astype(float)-b[valid].astype(float))))
                        max_difference = diff if max_difference is None else max(max_difference,diff)
                fields[name] = dict(compared_valid_values=count,exact_equal_values=equal,
                                     excluded_missing_values=fill,max_absolute_difference=max_difference)
            hypotheses.append(dict(original_time_minus_arco_seconds=offset,
                                    matched_times=[dict(arco=str(tt[ti]),original=str(st[si])) for ti,si in pairs],
                                    complete_time_coverage=len(pairs)==len(tt),fields=fields))
        metadata = {}
        for label,ds,times in (('original',source,st),('arco',target,tt)):
            metadata[label] = dict(dimensions=dict(ds.sizes),
                                   time_start=str(times[0]),time_end=str(times[-1]),
                                   creation_date=ds.attrs.get('creation_date'),
                                   time_bounds=ds.time.attrs.get('bounds'),
                                   cell_methods={n:ds[n].attrs.get('cell_methods') for n in WAVE_FIELDS},
                                   reference_variables=[n for n in ds.variables if ds[n].attrs.get('standard_name')
                                                        in ('forecast_reference_time','forecast_period')],
                                   global_attribute_names=list(ds.attrs))
        return dict(schema=1,scope='offline_original_arco_comparison',
                    original_sha256=digest(original),arco_sha256=digest(arco),
                    exact_native_coordinate_match=True,original_indices=indices,
                    metadata=metadata,hypotheses=hypotheses,
                    original_model_run_verified=False,publication_time_verified=False,
                    arco_lineage_verified=False,time_support_qualified=False,
                    qualification='diagnostic evidence only; equality does not identify run or revision')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--arco',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=compare(args.original,args.arco)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('COMPARISON_COMPLETE; planning qualification unchanged')


if __name__=='__main__':
    main()
