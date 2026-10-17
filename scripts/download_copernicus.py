"""Bounded Vinga fetch using existing Toolbox credentials; no routing or DB.

Run via download-copernicus.sh for a wall-clock bound and private exit log.
The only optional runtime dependency is the already installed Toolbox 2.5.0.
"""
import argparse
from datetime import datetime, timezone
import json
import logging
import socket
import os
import shutil
import tempfile
import time
import fcntl
from math import isfinite
from pathlib import Path
import sys

from scripts.copernicus_budget import BudgetError, DownloadBudget, cached_entry, digest, request_key

from infrastructure.copernicus_fields import BATHY_FIELDS, CURRENT_FIELDS, WAVE_FIELDS, validate_fields


REQUESTS = (
    ('waves', 'cmems_mod_bal_wav_anfc_PT1H-i', WAVE_FIELDS),
    ('current', 'cmems_mod_bal_phy_anfc_PT1H-i', CURRENT_FIELDS),
    ('wave-mask', 'cmems_mod_bal_wav_anfc_static', BATHY_FIELDS),
)
START, END = '2026-10-13T12:00:00Z', '2026-10-13T16:00:00Z'
BBOX = dict(minimum_longitude=11.58, maximum_longitude=11.63,
            minimum_latitude=57.62, maximum_latitude=57.65)
SOURCE_URLS = {
    'waves': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description',
    'current': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_PHY_003_006/description',
    'wave-mask': 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description',
}


def selection(catalogue, dataset_id, fields):
    """Pin one catalogue version/part/service; reject uncertain field schemas."""
    datasets = [d for p in catalogue.products for d in p.datasets if d.dataset_id == dataset_id]
    if len(datasets) != 1 or not datasets[0].versions:
        raise ValueError('Requested dataset/version not uniquely available')
    version = datasets[0].versions[0]
    matches = []
    for part in version.parts:
        for service in part.services:
            if service.service_name not in ('arco-geo-series', 'static-arco'):
                continue
            variables = {v.short_name: {'standard_name': v.standard_name, 'units': v.units}
                         for v in service.variables}
            try:
                validate_fields(variables, fields)
            except ValueError:
                continue
            matches.append((part, service))
    if len(matches) != 1:
        raise ValueError('Native field service/part ambiguous or unavailable')
    part, service = matches[0]
    kwargs = dict(dataset_id=dataset_id, dataset_version=version.label,
                  dataset_part=part.name, service=service.service_name, variables=list(fields))
    if fields == CURRENT_FIELDS:
        depths = [c for v in service.variables if v.short_name in fields
                  for c in v.coordinates if c.coordinate_id == 'depth']
        if len(depths) != 2 or any(c.coordinate_unit != 'm' for c in depths):
            raise ValueError('Surface depth coordinate unavailable')
        shallow = []
        explicit_axes = []
        for coordinate in depths:
            values = getattr(coordinate, 'values', None)
            minimum = getattr(coordinate, 'minimum_value', None)
            if values is not None:
                if (not values or len(values) > 1000 or any(type(v) not in (int,float) or not isfinite(v) or v < 0 for v in values)
                        or len(set(values)) != len(values)):
                    raise ValueError('Invalid explicit depth axis')
                explicit_axes.append(tuple(sorted(values)))
                if minimum is not None and minimum != min(values):
                    raise ValueError('Conflicting depth coordinate metadata')
                minimum = min(values)
            if type(minimum) not in (int,float) or not isfinite(minimum) or minimum < 0:
                raise ValueError('Unverified surface depth')
            shallow.append(float(minimum))
        if shallow[0] != shallow[1] or (explicit_axes and (len(explicit_axes) != 2 or explicit_axes[0] != explicit_axes[1])):
            raise ValueError('Incompatible current depth coordinates')
        if explicit_axes and len(explicit_axes[0])>1 and explicit_axes[0][1] <= shallow[0]+.5:
            raise ValueError('Surface selection would include multiple native depth levels')
        kwargs.update(minimum_depth=shallow[0], maximum_depth=shallow[0] + .5,
                      vertical_axis='depth')
    return kwargs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--estimate-only', action='store_true', help='Validate cache and budgets, report estimates; never download or copy weather files')
    parser.add_argument('--products', nargs='+', choices=[r[0] for r in REQUESTS],
                        default=[r[0] for r in REQUESTS])
    parser.add_argument('--bbox', type=float, nargs=4, metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'),
                        default=[11.58, 57.62, 11.63, 57.65])
    parser.add_argument('--start', default=START)
    parser.add_argument('--end', default=END)
    parser.add_argument('--minimum-depth', type=float)
    parser.add_argument('--maximum-depth', type=float)
    parser.add_argument('--variables', nargs='+', help='Subset of the selected products reviewed variables')
    parser.add_argument('--file-budget-gb', type=float, default=2)
    parser.add_argument('--transfer-budget-gb', type=float, default=10)
    parser.add_argument('--total-transfer-budget-gb', type=float, default=20)
    parser.add_argument('--disk-reserve-gb', type=float, default=1)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/seaparser-copernicus-cache'))
    parser.add_argument('--cache-max-age-hours', type=float, default=6)
    args = parser.parse_args(argv)
    os.umask(0o077)
    budget = DownloadBudget(args.file_budget_gb, args.transfer_budget_gb,
                            args.total_transfer_budget_gb, args.disk_reserve_gb)
    west, south, east, north = args.bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Finite ordered geographic bounds required')
    start, end = (datetime.fromisoformat(v.replace('Z', '+00:00')) for v in (args.start, args.end))
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError('Explicit ordered timezone-aware time bounds required')
    if not isfinite(args.cache_max_age_hours) or args.cache_max_age_hours < 0:
        raise ValueError('Finite nonnegative cache age required')
    if (args.minimum_depth is None) != (args.maximum_depth is None):
        raise ValueError('Both depth bounds required')
    if args.minimum_depth is not None and (
            'current' not in args.products or not isfinite(args.minimum_depth)
            or not isfinite(args.maximum_depth) or not 0 <= args.minimum_depth <= args.maximum_depth):
        raise ValueError('Ordered finite current depth bounds required')
    allowed = set().union(*(set(fields) for label, _, fields in REQUESTS if label in args.products))
    if args.variables is not None and (not set(args.variables) <= allowed or any(
            not set(args.variables).intersection(fields)
            for label, _, fields in REQUESTS if label in args.products)):
        raise ValueError('Reviewed variables required for each selected product')
    bbox = dict(minimum_longitude=west, maximum_longitude=east,
                minimum_latitude=south, maximum_latitude=north)
    args.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    transferred_bytes = 0
    # Prevent client exception logs or signed URLs from entering the audit log.
    logging.disable(logging.CRITICAL)
    import copernicusmarine as marine
    if marine.__version__ != '2.5.0':
        raise ValueError('This request was reviewed against Toolbox 2.5.0')
    socket.getaddrinfo('stac.marine.copernicus.eu', 443)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    manifest = {'schema': 1, 'toolbox_version': marine.__version__, 'bbox': bbox,
                'start': args.start, 'end': args.end, 'files': [],
                'budgets_gb': dict(file=budget.file_gb, transfer=budget.transfer_gb,
                                   total_transfer=budget.total_transfer_gb, disk_reserve=budget.reserve_gb),
                 'attribution': 'Generated using E.U. Copernicus Marine Service Information; DOI: 10.48670/moi-00010, 10.48670/moi-00011',
                'forecast_issued_at': None,
                'issuance_status': 'unknown; valid times do not identify the model run'}
    for label, dataset_id, fields in REQUESTS:
        if label not in args.products:
            continue
        catalogue = marine.describe(dataset_id=dataset_id, disable_progress_bar=True, raise_on_error=True)
        request = selection(catalogue, dataset_id, fields)
        request.update(bbox, coordinates_selection_method='strict-inside',
                       output_directory=args.output, output_filename=f'{label}.nc',
                       file_format='netcdf', disable_progress_bar=True, raise_if_updating=True)
        if label != 'wave-mask':
            request.update(start_datetime=start.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'),
                           end_datetime=end.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'))
        if label == 'current' and args.minimum_depth is not None:
            request.update(minimum_depth=args.minimum_depth, maximum_depth=args.maximum_depth)
        if args.variables is not None:
            request['variables'] = [v for v in request['variables'] if v in args.variables]
        key = request_key(request)
        cached = args.cache / key
        cached.mkdir(mode=0o700, exist_ok=True)
        path = args.output / f'{label}.nc'
        # Serialize identical requests through cache admission, including across processes.
        with (cached / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            cache_record = cached_entry(cached, request, args.cache_max_age_hours * 3600)
            if args.estimate_only:
                if cache_record is None:
                    estimate = marine.subset(**request, dry_run=True)
                    file_bytes, transfer_bytes = budget.check(estimate, transferred_bytes, (args.output, cached))
                    hit = False
                else:
                    file_bytes, transfer_bytes = cache_record['estimated_result_bytes'], 0
                    if cache_record['bytes'] > budget.file_gb * 1e9:
                        raise BudgetError('Cached result exceeds file GB budget')
                    if shutil.disk_usage(args.output).free < cache_record['bytes'] + budget.reserve_gb * 1e9:
                        raise BudgetError('Insufficient output disk space including reserve')
                    hit = True
                transferred_bytes += transfer_bytes
                manifest['files'].append({'product':label,'status':'estimate_only','cache_hit':hit,'cache_key':key,
                    'estimated_result_bytes':file_bytes,'estimated_transfer_bytes_this_run':transfer_bytes,
                    'request':{k:v for k,v in request.items() if k != 'output_directory'}})
                (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
                print(f'PLANNED {label} cache_hit={hit} result_bytes={file_bytes:.0f} transfer_bytes={transfer_bytes:.0f}',flush=True)
                continue
            if cache_record is None:
                estimate = marine.subset(**request, dry_run=True)
                print(f'ESTIMATE {label} toolbox_result_mb={estimate.file_size} '
                      f'toolbox_transfer_mb={estimate.data_transfer_size} '
                      f'file_budget_gb={budget.file_gb} transfer_budget_gb={budget.transfer_gb}', flush=True)
                file_bytes, transfer_bytes = budget.check(estimate, transferred_bytes,
                                                         (args.output, cached))
                # Staging prevents failed/interrupted downloads from becoming cache hits.
                with tempfile.TemporaryDirectory(prefix='staging-', dir=cached) as staging:
                    download_request = dict(request, output_directory=Path(staging), output_filename='data.nc')
                    marine.subset(**download_request)
                    source = Path(staging) / 'data.nc'
                    if not source.is_file() or source.stat().st_size > budget.file_gb * 1e9:
                        raise BudgetError('Missing or oversized NetCDF output')
                    cache_record = dict(key=key, bytes=source.stat().st_size, sha256=digest(source),
                                        cached_at_epoch=time.time(),
                                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                                        toolbox_estimated_file_mb=estimate.file_size,
                                        toolbox_estimated_transfer_mb=estimate.data_transfer_size,
                                        estimated_result_bytes=file_bytes,
                                        estimated_transfer_bytes=transfer_bytes)
                    source.replace(cached / 'data.nc')
                    metadata = cached / 'entry.tmp'
                    metadata.write_text(json.dumps(cache_record, indent=2) + '\n')
                    metadata.replace(cached / 'entry.json')
                transferred_bytes += transfer_bytes
                cache_hit = False
            else:
                cache_hit = True
            if cache_record['bytes'] > budget.file_gb * 1e9:
                raise BudgetError('Cached result exceeds file GB budget')
            if shutil.disk_usage(args.output).free < cache_record['bytes'] + budget.reserve_gb * 1e9:
                raise BudgetError('Insufficient output disk space including reserve')
            shutil.copyfile(cached / 'data.nc', path)
            print(f"{'CACHE_HIT' if cache_hit else 'FETCHED'} {label} "
                  f"result_bytes={cache_record['bytes']} "
                  f"estimated_transfer_bytes_this_run={0 if cache_hit else cache_record['estimated_transfer_bytes']:.0f}",
                  flush=True)
        entry = {'product': label, 'dataset_id': dataset_id, 'version': request['dataset_version'],
                 'part': request['dataset_part'], 'service': request['service'],
                 'filename': path.name, 'sha256': cache_record['sha256'],
                 'retrieved_at': cache_record['retrieved_at'],
                 'cache_hit': cache_hit, 'cache_key': key,
                 'estimated_result_bytes': cache_record['estimated_result_bytes'],
                 'estimated_transfer_bytes': cache_record['estimated_transfer_bytes'],
                 'estimated_transfer_bytes_this_run': 0 if cache_hit else cache_record['estimated_transfer_bytes'],
                 'actual_result_bytes': path.stat().st_size,
                 'source_url': SOURCE_URLS[label],
                 'license_url': 'https://marine.copernicus.eu/user-corner/service-commitments-and-license',
                 'request': {k: v for k, v in request.items() if k != 'output_directory'}}
        manifest['files'].append(entry)
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"{'ESTIMATE_COMPLETE' if args.estimate_only else 'DOWNLOAD_COMPLETE'} estimated_weather_transfer_bytes_this_run={transferred_bytes:.0f}; "
          'diagnostic only; audit and source qualification required before planning')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Exception type is sufficient for diagnostics; never print auth-bearing messages.
        reason = f': {error}' if isinstance(error, BudgetError) else ''
        print(f'FETCH_FAILED {type(error).__name__}{reason}; no regional routing enabled', file=sys.stderr)
        sys.exit(1)
