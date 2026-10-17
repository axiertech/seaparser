"""Freeze an audited download manifest and NetCDF values as provider payload JSON."""
import argparse
from datetime import datetime
from io import BytesIO
import json
import math
from pathlib import Path

from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from scripts.audit_copernicus import audit_snapshot


SOURCE_URLS = {
    'waves': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description',
    'current': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_PHY_003_006/description',
    'static': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description',
}
LICENSE_URL = 'https://marine.copernicus.eu/user-corner/service-commitments-and-license'


def _json_value(value):
    if hasattr(value, 'item'):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    raise ValueError('Unsupported NetCDF sample')


def _grid(values):
    return [[[_json_value(value) for value in row] for row in plane] for plane in values]


def _materialize_products(sources, entries, audit_products):
    import xarray as xr
    products = {}
    for label, entry in entries.items():
        if entry is None:
            raise ValueError('Static wet mask is required')
        with xr.open_dataset(BytesIO(sources[entry['filename']]), engine='h5netcdf',
                             decode_cf=True, mask_and_scale=True) as ds:
            metadata = {
                'dataset_id': entry['dataset_id'], 'version': entry['version'],
                'source': 'Copernicus Marine Baltic forecast, product version pinned in manifest',
                'issued_at': audit_products[label]['issued_at'] if label in audit_products else None,
                'retrieved_at': entry['retrieved_at'],
                'source_url': entry.get('source_url') or SOURCE_URLS[label],
                'license_url': entry.get('license_url') or LICENSE_URL,
                'source_sha256': entry['sha256'],
                'latitude': [float(value) for value in ds.latitude.values],
                'longitude': [float(value) for value in ds.longitude.values],
                'variables': {name: {'standard_name': field.attrs.get('standard_name'),
                                     'units': field.attrs.get('units')}
                              for name, field in ds.data_vars.items()},
            }
            if label == 'waves':
                metadata['times'] = [datetime.fromisoformat(str(value)).isoformat() + 'Z'
                                     for value in ds.time.values.astype('datetime64[s]')]
                metadata['data'] = {name: _grid(ds[name].transpose('time', 'latitude', 'longitude').values)
                                    for name in ('VHM0', 'VTM02', 'VMDR')}
            elif label == 'current':
                metadata['times'] = [datetime.fromisoformat(str(value)).isoformat() + 'Z'
                                     for value in ds.time.values.astype('datetime64[s]')]
                metadata['depth_m'] = [float(value) for value in ds.depth.values]
                metadata['data'] = {name: _grid(ds[name].isel(depth=0).transpose('time', 'latitude', 'longitude').values)
                                    for name in ('uo', 'vo')}
            else:
                metadata['depth_units'] = ds['deptho'].attrs.get('units')
                metadata['depth_standard_name'] = ds['deptho'].attrs.get('standard_name')
                metadata['data'] = {name: [[_json_value(value) for value in row]
                                           for row in ds[name].transpose('latitude', 'longitude').values]
                                    for name in ('deptho', 'mask')}
        products[label] = metadata
    return products


def freeze_with_audit(directory):
    """Create payload and report together; no detached audit input is accepted."""
    import xarray as xr

    directory = Path(directory)
    report, manifest, sources = audit_snapshot(directory)
    by_label = {entry['product']: entry for entry in manifest['files']}
    static_entry = by_label.get('static') or by_label.get('wave-mask')
    entries = {'waves': by_label['waves'], 'current': by_label['current'], 'static': static_entry}
    audit_products = {'waves': report['waves'], 'current': report['current']}
    products = _materialize_products(sources, entries, audit_products)
    payload = {
        'schema': 1,
        'bundle_id': 'copernicus-baltic-vinga-reference',
        'bundle_version': 'waves-202311_current-202411_static-202311',
        'products': products,
    }
    CopernicusMarineAdapter().normalize(payload)
    return payload, report


def freeze_native_with_audit(directory, *, radius_m):
    """Reuse the field materializer for the larger, independently hashed bundle.

    This does not apply development metadata assumptions or enable routing.
    """
    from hashlib import sha256
    from scripts.inspect_expanded_forecast import inspect
    from scripts.manifest_json import manifest_json
    directory=Path(directory)
    report=inspect(directory)
    hashes=report['source_hashes'];sources={}
    for filename in ('waves.nc','current.nc','wave-mask.nc'):
        with (directory/filename).open('rb') as stream:data=stream.read(10_000_001)
        if len(data)>10_000_000 or sha256(data).hexdigest()!=hashes[filename]:
            raise ValueError('Captured native marine bytes differ from frozen bundle')
        sources[filename]=data
    with (directory/'marine-download-manifest.json').open('rb') as stream:download_data=stream.read(512001)
    with (directory/'wave-subset-manifest.json').open('rb') as stream:wave_data=stream.read(512001)
    with (directory/'parent-wave-original-manifest.json').open('rb') as stream:parent_data=stream.read(512001)
    for name,data in (('marine-download-manifest.json',download_data),('wave-subset-manifest.json',wave_data),('parent-wave-original-manifest.json',parent_data)):
        if len(data)>512000 or sha256(data).hexdigest()!=hashes[name]:raise ValueError('Native source manifest changed')
    downloaded=manifest_json(download_data);wave=manifest_json(wave_data);parent=manifest_json(parent_data)
    by_name={e['product']:e for e in downloaded['files']}
    entries={'waves':dict(filename='waves.nc',dataset_id=parent['dataset_id'],version=parent['dataset_version'],
        retrieved_at=wave['retrieved_at'],sha256=wave['sha256']),
        'current':by_name['current'],'static':by_name['wave-mask']}
    products=_materialize_products(sources,entries,{'waves':{'issued_at':None},'current':{'issued_at':None}})
    payload=dict(schema=1,bundle_id='copernicus-baltic-vinga-expanded-reference',
        bundle_version='original-waves-202311_current-202411_static-202311',products=products)
    CopernicusMarineAdapter().normalize(payload,native_radius_m=radius_m)
    return payload,report


def freeze(directory):
    payload, _ = freeze_with_audit(directory)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = freeze(args.directory)
    args.output.write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')) + '\n')
    print('FROZEN_COPERNICUS_REFERENCE=validated; issue_time and wind remain explicit blockers')


if __name__ == '__main__':
    main()
