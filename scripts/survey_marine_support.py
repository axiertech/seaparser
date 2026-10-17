"""Offline inventory of native marine cells, without creating a routing adapter.

Value completeness is distinct from validity masks, temporal semantics, model
provenance, land coverage and navigability. No data are interpolated or filled.
"""
import argparse
from io import BytesIO
import json
from hashlib import sha256
from pathlib import Path

from infrastructure.copernicus_fields import WAVE_FIELDS,CURRENT_FIELDS,MASK_FIELDS,validate_fields
from scripts.audit_copernicus import coordinate


def survey(path, product, wave_mask=None):
    import numpy as np
    import xarray as xr
    if wave_mask is not None and product!='waves':raise ValueError('Wave mask cannot qualify current nodes')
    fields={'waves':WAVE_FIELDS,'current':CURRENT_FIELDS}[product]
    with Path(path).open('rb') as stream:data=stream.read(10_000_001)
    if len(data)>10_000_000:raise ValueError('Marine survey file budget exceeded')
    with xr.open_dataset(BytesIO(data),engine='h5netcdf',decode_cf=True,mask_and_scale=True) as ds:
        if any(v.size>100_000 for v in ds.variables.values()):raise ValueError('Decoded survey array budget exceeded')
        validate_fields({n:ds[n].attrs for n in fields},fields)
        lon,lat,time=(coordinate(ds,name) for name in ('longitude','latitude','time'))
        for axis,units in ((lon,'degrees_east'),(lat,'degrees_north')):
            if axis.attrs.get('units')!=units or len(axis)<2 or not np.isfinite(axis.values).all() or not (np.diff(axis.values)>0).all():
                raise ValueError('Finite increasing native geographic axes required')
        times=time.values.astype('datetime64[s]')
        if (time.encoding.get('calendar','standard') not in ('standard','gregorian','proleptic_gregorian')
                or len(times)<2 or len(times)>25 or np.isnat(times).any()
                or not np.array_equal(time.values,times) or not (np.diff(times)==np.timedelta64(1,'h')).all()):
            raise ValueError('Exact hourly Gregorian time coordinates required')
        valid=np.ones((len(time),len(lat),len(lon)),dtype=bool);counts={}
        for name in fields:
            field=ds[name]
            if product=='current':
                depth=coordinate(ds,'depth')
                if len(depth)!=1 or depth.attrs.get('units')!='m' or depth.attrs.get('positive')!='down' or not np.isfinite(depth.values).all() or float(depth.values[0])<0:
                    raise ValueError('One explicit nonnegative downward depth in metres required')
                field=field.isel({depth.name:0})
            if set(field.dims)!={time.name,lat.name,lon.name}:
                raise ValueError('Unexpected native field dimensions')
            values=field.transpose(time.name,lat.name,lon.name).values
            good=np.isfinite(values)
            if name=='VHM0':good &= values>=0
            if name=='VTM02':good &= values>0
            if name=='VMDR':good &= (values>=0)&(values<=360)
            counts[name]={'total':int(values.size),'missing_or_invalid':int(np.sum(~good))}
            valid &= good
        mask_hash=None;wet=None
        if wave_mask is not None:
            with Path(wave_mask).open('rb') as stream:mask_data=stream.read(10_000_001)
            if len(mask_data)>10_000_000:raise ValueError('Mask survey byte budget exceeded')
            with xr.open_dataset(BytesIO(mask_data),engine='h5netcdf',decode_cf=True,mask_and_scale=True) as mask_ds:
                if any(v.size>100_000 for v in mask_ds.variables.values()):raise ValueError('Decoded mask array budget exceeded')
                validate_fields({n:mask_ds[n].attrs for n in MASK_FIELDS},MASK_FIELDS)
                mlon,mlat=(coordinate(mask_ds,n) for n in ('longitude','latitude'))
                if not np.array_equal(mlon.values,lon.values) or not np.array_equal(mlat.values,lat.values):
                    raise ValueError('Exact own wave-mask native coordinates required')
                values=mask_ds['mask'].transpose(mlat.name,mlon.name).values
                if not np.isin(values,[0,1]).all():raise ValueError('Finite binary wave mask required')
                wet=values==1;mask_hash=sha256(mask_data).hexdigest()
        from infrastructure.copernicus_adapter import _local_axes
        try:
            _local_axes(lat.values.tolist(),lon.values.tolist());geometry_compatible=True
        except ValueError:
            geometry_compatible=False
        cells=[]
        for j in range(len(lat)-1):
            for i in range(len(lon)-1):
                complete=bool(valid[:,j:j+2,i:i+2].all())
                ring=[[float(lon.values[x]),float(lat.values[y])] for y,x in ((j,i),(j,i+1),(j+1,i+1),(j+1,i),(j,i))]
                cells.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[ring]},
                    'properties':{'product':product,'native_cell':[j,i],'all_time_values_complete':complete,
                        'validity_mask_qualified':False,'wave_mask_all_corners_wet':bool(wet[j:j+2,i:i+2].all()) if wet is not None else None,
                        'navigability':'not_assessed'}})
        return {'schema':1,'product':product,'source_sha256':sha256(data).hexdigest(),'source_qualification':'unverified',
            'scope':'native_value_completeness_only','routing_enabled':False,'result_qualification':'diagnostic_only',
            'issued_at':None,'model_run_id':None,'time_start':str(times[0])+'Z','time_end':str(times[-1])+'Z',
            'time_count':len(time),'latitude':lat.values.tolist(),'longitude':lon.values.tolist(),
            'depth_m':float(depth.values[0]) if product=='current' else None,
            'wave_mask_sha256':mask_hash,'wave_mask_native_alignment_verified':wet is not None,
            'wave_mask_wet_nodes':int(wet.sum()) if wet is not None else None,
            'existing_adapter_geometry_compatible':geometry_compatible,
            'field_counts':counts,'node_count':len(lat)*len(lon),'cell_count':len(cells),
            'all_time_value_complete_cells':sum(c['properties']['all_time_values_complete'] for c in cells),
            'cell_methods':{n:ds[n].attrs.get('cell_methods') for n in fields},
            'time_bounds':time.attrs.get('bounds') or time.encoding.get('bounds'),
            'cells':{'type':'FeatureCollection','features':cells},
            'blockers':['validity_masks_not_qualified','temporal_support_unverified','model_issue_time_unverified',
                'cross_product_model_run_compatibility_unverified','wind_and_land_route_support_not_expanded']+([] if geometry_compatible else ['local_rectilinear_representation_exceeds_existing_tolerance'])}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path)
    p.add_argument('--product',choices=('waves','current'),required=True);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--wave-mask',type=Path)
    a=p.parse_args();r=survey(a.file,a.product,a.wave_mask);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('SURVEY_COMPLETE',r['product'],r['node_count'],'nodes',r['all_time_value_complete_cells'],'value-complete cells of',r['cell_count'])
