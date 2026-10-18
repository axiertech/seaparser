"""Safe serialization of existing frozen readers, before marine normalization."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from infrastructure.materialized_cache import MaterializedCache, fingerprint
from infrastructure.native_wind import NativeWindSample
from scripts.build_uddevalla import wind_sample
from scripts.freeze_copernicus_reference import freeze_coastal_with_audit

ROOT = Path(__file__).resolve().parents[1]


def _tokens(value):
    if isinstance(value, (tuple, list)): return [_tokens(v) for v in value]
    return str(value)


def _decimals(value):
    if isinstance(value, list): return tuple(_decimals(v) for v in value)
    return Decimal(value)


def coastal_inputs(directory, request, *, cache_directory=None, diagnostics=None):
    directory = Path(directory)
    if cache_directory is None:
        sample = wind_sample(directory / 'met', request)
        payload, audit = freeze_coastal_with_audit(directory / 'marine', request)
        if diagnostics is not None: diagnostics['materialization_cache'] = 'disabled'
        return sample, payload, audit
    names = ('request.json', 'met/inventory.json', 'met/sources.json', 'met/forecast.dds',
             'met/forecast.das', 'met/times.txt', 'met/axes.txt', 'met/coordinates.txt', 'met/wind.txt',
             'marine/manifest.json')
    files = {name: directory / name for name in names}
    manifest = json.loads((directory / 'marine/manifest.json').read_text())
    for entry in manifest['files']:
        name = entry['filename']
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError('Local marine source filename required')
        files['marine/' + name] = directory / 'marine' / name
    # Reader dependencies are part of the identity; a changed validation cannot reuse old admission.
    for name in ('application/coastal_inputs.py', 'infrastructure/materialized_cache.py', 'requirements.lock',
                 'infrastructure/native_wind.py',
                 'infrastructure/copernicus_fields.py', 'scripts/build_uddevalla.py',
                 'scripts/audit_met_metadata.py', 'scripts/freeze_copernicus_reference.py',
                 'scripts/fetch_uddevalla.py', 'scripts/audit_copernicus.py',
                 'scripts/copernicus_budget.py', 'scripts/manifest_json.py'):
        files['reader/' + name] = ROOT / name
    identity = {'schema': 1, 'sources': fingerprint(files), 'request': request}

    def build():
        sample = wind_sample(directory / 'met', request)
        payload, audit = freeze_coastal_with_audit(directory / 'marine', request)
        result = {'projection': sample.projection, 'times': [t.isoformat() for t in sample.times],
                  'model_reference_time': sample.model_reference_time.isoformat(),
                  'source_hashes': sample.source_hashes, 'payload': payload, 'audit': audit}
        for name in ('x_m', 'y_m', 'speed_m_s', 'direction_from_degrees', 'land_fraction'):
            result[name] = _tokens(getattr(sample, name))
        if fingerprint(files) != identity['sources']:
            raise ValueError('Sources changed during materialization')
        return result

    data, status = MaterializedCache(cache_directory).get_or_create(identity, build)
    sample = NativeWindSample(data['projection'], *(_decimals(data[n]) for n in ('x_m', 'y_m')),
        tuple(datetime.fromisoformat(t) for t in data['times']),
        *(_decimals(data[n]) for n in ('speed_m_s', 'direction_from_degrees', 'land_fraction')),
        datetime.fromisoformat(data['model_reference_time']), tuple(tuple(p) for p in data['source_hashes']))
    if diagnostics is not None: diagnostics['materialization_cache'] = status
    return sample, data['payload'], data['audit']
