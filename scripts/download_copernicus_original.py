"""Fetch one named WAV producer file through Toolbox get, never subset.

Reuse the regional budget checks and content-verified snapshot cache. Source
object identity is not an assertion of model run, issue time or ARCO lineage.
"""
import argparse
import fcntl
import json
import logging
from math import isfinite
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts.copernicus_budget import BudgetError, DownloadBudget, cached_entry, digest, request_key

DATASET = 'cmems_mod_bal_wav_anfc_PT1H-i'
VERSION = '202311'
PREFIX = ('s3://mdl-native-11/native/BALTICSEA_ANALYSISFORECAST_WAV_003_010/'
          'cmems_mod_bal_wav_anfc_PT1H-i_202311/')


def fetch(marine, filename, output, cache, budget):
    if marine.__version__ != '2.5.0':
        raise ValueError('Reviewed Toolbox 2.5.0 required')
    if re.fullmatch(r'BAL-WAM_WAV[0-9]{8}(00|12)\.nc', filename) is None:
        raise ValueError('Exact reviewed WAV original filename required')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    request = dict(dataset_id=DATASET, dataset_version=VERSION, dataset_part='default',
                   filter='*/' + filename, no_directories=True,
                   disable_progress_bar=True, max_concurrent_requests=1)
    estimate = marine.get(**request, output_directory=output, dry_run=True)
    if estimate.number_of_files_to_download != 1 or len(estimate.files) != 1:
        raise ValueError('Exactly one original candidate required')
    remote = estimate.files[0]
    if (remote.filename != filename or not remote.s3_url.startswith(PREFIX)
            or not remote.s3_url.endswith('/' + filename)
            or '?' in remote.s3_url or '#' in remote.s3_url
            or re.fullmatch(r'(?:[0-9a-fA-F]+(?:-[0-9]+)?|"[0-9a-fA-F]+(?:-[0-9]+)?")', remote.etag) is None):
        raise ValueError('Unexpected original object identity')
    # Unlike subset estimators, Toolbox get reports bytes / 1024**2.
    byte_size = remote.file_size * 1024**2
    if not isfinite(byte_size) or byte_size <= 0 or not float(byte_size).is_integer():
        raise BudgetError('Positive integral original byte size required')
    total_bytes = estimate.total_size * 1024**2 if estimate.total_size is not None else None
    if total_bytes != byte_size:
        raise BudgetError('Original object and total transfer estimates differ')
    source = dict(s3_object=remote.s3_url, etag=remote.etag, bytes=byte_size,
                  last_modified_datetime=remote.last_modified_datetime)
    identity = dict(kind='original', dataset_id=DATASET, dataset_version=VERSION,
                    dataset_part='default', **source)
    key = request_key(identity)
    directory = cache / key
    directory.mkdir(mode=0o700, exist_ok=True)
    with (directory/'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = cached_entry(directory, identity, float('inf'))
        hit = record is not None
        if not hit:
            print(f'ORIGINAL_ESTIMATE result_bytes={byte_size:.0f} transfer_bytes={total_bytes:.0f}', flush=True)
            budget.check(SimpleNamespace(file_size=byte_size/1_048_000,
                                          data_transfer_size=total_bytes/1_048_000),
                         0, (output, directory))
            with tempfile.TemporaryDirectory(prefix='staging-', dir=directory) as temp:
                response = marine.get(**request, output_directory=Path(temp))
                path = Path(temp)/filename
                if (len(response.files) != 1 or response.number_of_files_to_download != 1
                        or not path.is_file() or path.stat().st_size != byte_size):
                    raise ValueError('Original download count or byte size mismatch')
                downloaded = response.files[0]
                if (downloaded.s3_url != remote.s3_url or downloaded.etag != remote.etag
                        or downloaded.last_modified_datetime != remote.last_modified_datetime):
                    raise ValueError('Original object changed during retrieval')
                record = dict(key=key, bytes=path.stat().st_size, sha256=digest(path),
                              cached_at_epoch=time.time(), retrieved_at=datetime.now(timezone.utc).isoformat(),
                              estimated_result_bytes=byte_size, estimated_transfer_bytes=total_bytes)
                path.replace(directory/'data.nc')
                metadata = directory/'entry.tmp'
                metadata.write_text(json.dumps(record, indent=2)+'\n')
                metadata.replace(directory/'entry.json')
        if record['bytes'] > budget.file_gb*1e9:
            raise BudgetError('Original cached file exceeds GB budget')
        if shutil.disk_usage(output).free < record['bytes'] + budget.reserve_gb*1e9:
            raise BudgetError('Insufficient disk space including reserve')
        path = output/filename
        shutil.copyfile(directory/'data.nc', path)
    manifest = dict(schema=1, scope='original_file_diagnostic', toolbox_version='2.5.0',
                    dataset_id=DATASET, dataset_version=VERSION, dataset_part='default',
                    filename=filename, source=source, sha256=record['sha256'],
                    actual_result_bytes=path.stat().st_size, retrieved_at=record['retrieved_at'],
                    cache_key=key, cache_hit=hit, estimated_result_bytes=byte_size,
                    estimated_transfer_bytes=total_bytes,
                    estimated_transfer_bytes_this_run=0 if hit else total_bytes,
                    budgets_gb=dict(file=budget.file_gb, transfer=budget.transfer_gb,
                                    total_transfer=budget.total_transfer_gb, disk_reserve=budget.reserve_gb),
                    model_run_id=None, issued_at=None, arco_lineage_verified=False)
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'ORIGINAL_COMPLETE cache_hit={hit} bytes={record["bytes"]} sha256={record["sha256"]}', flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filename', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/seaparser-copernicus-cache'))
    parser.add_argument('--file-budget-gb', type=float, default=2)
    parser.add_argument('--transfer-budget-gb', type=float, default=10)
    parser.add_argument('--total-transfer-budget-gb', type=float, default=20)
    parser.add_argument('--disk-reserve-gb', type=float, default=1)
    args = parser.parse_args()
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    for name in ('COPERNICUSMARINE_SERVICE_USERNAME', 'COPERNICUSMARINE_SERVICE_PASSWORD'):
        os.environ.pop(name, None)
    import copernicusmarine as marine
    return fetch(marine, args.filename, args.output, args.cache,
                 DownloadBudget(args.file_budget_gb, args.transfer_budget_gb,
                                args.total_transfer_budget_gb, args.disk_reserve_gb))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # All client details stay private. BudgetError contains local safe text.
        import sys
        reason = f': {error}' if isinstance(error, BudgetError) else ''
        print(f'ORIGINAL_FAILED {type(error).__name__}{reason}; planning gates unchanged', file=sys.stderr)
        sys.exit(1)
