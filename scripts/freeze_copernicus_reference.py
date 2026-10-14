"""Freeze an audited download manifest and NetCDF values as provider payload JSON."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path

from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from scripts.audit_copernicus import audit


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


def freeze(directory):
    import xarray as xr

    directory = Path(directory)
    report = audit(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    by_label = {entry['product']: entry for entry in manifest['files']}
    static_entry = by_label.get('static') or by_label.get('wave-mask')
    entries = {'waves': by_label['waves'], 'current': by_label['current'], 'static': static_entry}
    audit_products = {'waves': report['waves'], 'current': report['current']}
    products = {}
    for label, entry in entries.items():
        if entry is None:
            raise ValueError('Static wet mask is required')
        path = directory / entry['filename']
        with xr.open_dataset(path, engine='h5netcdf', decode_cf=True, mask_and_scale=True) as ds:
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
                metadata['data'] = {name: _grid(ds[name].values)
                                    for name in ('VHM0', 'VTM02', 'VMDR')}
            elif label == 'current':
                metadata['times'] = [datetime.fromisoformat(str(value)).isoformat() + 'Z'
                                     for value in ds.time.values.astype('datetime64[s]')]
                metadata['depth_m'] = [float(value) for value in ds.depth.values]
                metadata['data'] = {name: _grid(ds[name].isel(depth=0).values)
                                    for name in ('uo', 'vo')}
            else:
                metadata['depth_units'] = ds['deptho'].attrs.get('units')
                metadata['depth_standard_name'] = ds['deptho'].attrs.get('standard_name')
                metadata['data'] = {name: [[_json_value(value) for value in row]
                                           for row in ds[name].values]
                                    for name in ('deptho', 'mask')}
        products[label] = metadata
    payload = {
        'schema': 1,
        'bundle_id': 'copernicus-baltic-vinga-reference',
        'bundle_version': 'waves-202311_current-202411_static-202311',
        'products': products,
    }
    CopernicusMarineAdapter().normalize(payload)
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
