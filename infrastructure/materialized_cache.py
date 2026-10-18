"""Bounded, content-addressed local JSON cache; never forecast freshness evidence."""
from contextlib import contextmanager
from hashlib import file_digest, sha256
import fcntl
import json
import os
from pathlib import Path
import shutil
import tempfile


def fingerprint(files):
    """Hash every source byte, including metadata, on every invocation."""
    result = {}
    for name, path in sorted(files.items()):
        path = Path(path)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024**2:
            raise ValueError('Unsupported materialization source')
        with path.open('rb') as stream:
            result[name] = file_digest(stream, 'sha256').hexdigest()
    return result


class MaterializedCache:
    def __init__(self, directory, *, max_entry_bytes=64*1024**2,
                 max_cache_bytes=256*1024**2, reserve_bytes=256*1024**2):
        if min(max_entry_bytes, max_cache_bytes, reserve_bytes) <= 0:
            raise ValueError('Positive cache budgets required')
        self.directory = Path(directory)
        self.entry_budget, self.cache_budget, self.reserve = max_entry_bytes, max_cache_bytes, reserve_bytes

    @contextmanager
    def _locked(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def get_or_create(self, identity, build):
        """One writer, atomic admission, checked digest; corruption fails closed."""
        key = sha256(json.dumps(identity, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        with self._locked():
            path = self.directory / (key + '.json')
            if path.exists():
                if path.is_symlink() or path.stat().st_size > self.entry_budget:
                    raise ValueError('Invalid materialized cache entry')
                envelope = json.loads(path.read_bytes())
                encoded = envelope['data'].encode()
                if envelope['key'] != key or sha256(encoded).hexdigest() != envelope['sha256']:
                    raise ValueError('Materialized cache integrity check failed')
                return json.loads(encoded), 'hit'
            # Refuse before expensive materialization if even the configured maximum cannot fit.
            if shutil.disk_usage(self.directory).free < self.reserve + self.entry_budget:
                raise ValueError('Insufficient materialized cache disk reserve')
            data = build()
            encoded = json.dumps(data, separators=(',', ':'), allow_nan=False)
            envelope = json.dumps({'key': key, 'sha256': sha256(encoded.encode()).hexdigest(), 'data': encoded},
                                  separators=(',', ':'), allow_nan=False).encode()
            used = sum(p.stat().st_size for p in self.directory.iterdir() if p.is_file())
            if len(envelope) > self.entry_budget or used + len(envelope) > self.cache_budget:
                raise ValueError('Materialized cache byte budget exceeded')
            if shutil.disk_usage(self.directory).free < self.reserve + len(envelope):
                raise ValueError('Insufficient materialized cache disk reserve')
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.directory, prefix='.staging-', delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(envelope); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary is not None and temporary.exists(): temporary.unlink()
            return json.loads(encoded), 'miss'
