"""Download budgets and immutable, hash-checked local subset cache.

Toolbox 2.5.0 NetCDF estimators divide by 1048e3; CLI budgets use decimal GB.
Cache reuse is an explicit snapshot reuse, never evidence of forecast freshness.
"""
from dataclasses import dataclass
from hashlib import file_digest, sha256
import json
from math import isfinite
from pathlib import Path
import shutil
import time


class BudgetError(ValueError):
    """Safe local diagnostic, without client URLs or credentials."""


@dataclass(frozen=True)
class DownloadBudget:
    file_gb: float = 2
    transfer_gb: float = 10
    total_transfer_gb: float = 20
    reserve_gb: float = 1

    def __post_init__(self):
        if any(not isfinite(v) or v <= 0 for v in (
                self.file_gb, self.transfer_gb, self.total_transfer_gb, self.reserve_gb)):
            raise BudgetError('Finite positive GB budgets required')

    def check(self, estimate, transferred_bytes, directories):
        values = (estimate.file_size, estimate.data_transfer_size)
        if any(v is None or not isfinite(v) or v < 0 for v in values):
            raise BudgetError('Finite nonnegative file and transfer estimates required')
        file_bytes, transfer_bytes = (v * 1_048_000 for v in values)
        if file_bytes > self.file_gb * 1e9:
            raise BudgetError('Estimated result file exceeds file GB budget')
        if transfer_bytes > self.transfer_gb * 1e9:
            raise BudgetError('Estimated transfer exceeds per-request GB budget')
        if transferred_bytes + transfer_bytes > self.total_transfer_gb * 1e9:
            raise BudgetError('Estimated transfer exceeds session GB budget')
        # Cache staging plus result copy, with headroom for temporary output.
        for directory in directories:
            if shutil.disk_usage(directory).free < 2 * file_bytes + self.reserve_gb * 1e9:
                raise BudgetError('Insufficient free disk space including reserve')
        return file_bytes, transfer_bytes


def digest(path):
    with Path(path).open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def request_key(request):
    identity = {k: v for k, v in request.items()
                if k not in ('output_directory', 'output_filename', 'disable_progress_bar')}
    return sha256(json.dumps({'toolbox': '2.5.0', 'request': identity},
                             sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cached_entry(directory, request, max_age_seconds, now=None):
    """Reject damaged, incomplete or expired snapshots; do not infer model run."""
    now = time.time() if now is None else now
    try:
        entry = json.loads((directory / 'entry.json').read_text())
        for key in ('retrieved_at', 'estimated_result_bytes', 'estimated_transfer_bytes'):
            if key not in entry:
                return None
        path = directory / 'data.nc'
        age = now - entry['cached_at_epoch']
        if (entry['key'] != request_key(request) or not 0 <= age <= max_age_seconds
                or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']):
            return None
        return entry
    except (OSError, ValueError, KeyError, TypeError):
        return None
