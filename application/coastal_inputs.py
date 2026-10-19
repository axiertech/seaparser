"""Safe serialization of existing frozen readers, before marine normalization."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import base64
import zlib

from infrastructure.materialized_cache import MaterializedCache, fingerprint
from infrastructure.native_wind import NativeWindSample,DecimalRow
from scripts.build_uddevalla import wind_sample
from scripts.freeze_copernicus_reference import freeze_coastal_with_audit

ROOT = Path(__file__).resolve().parents[1]
MAX_WIND_FIELD_BYTES = 64*1024**2
MAX_MARINE_PAYLOAD_BYTES = 128*1024**2


def _tokens(value):
    if isinstance(value, (tuple, list)): return [_tokens(v) for v in value]
    return str(value)


def _decimals(value):
    if isinstance(value, list): return tuple(_decimals(v) for v in value)
    return Decimal(value)


def _compress_json(value,limit):
    data=json.dumps(value,separators=(',',':'),allow_nan=False).encode()
    if len(data)>limit:raise ValueError('Compact field decoded byte budget exceeded')
    return base64.b64encode(zlib.compress(data)).decode('ascii')


def _expand_json(value,limit):
    decoder=zlib.decompressobj()
    data=decoder.decompress(base64.b64decode(value,validate=True),limit+1)
    if len(data)>limit or not decoder.eof or decoder.unused_data:
        raise ValueError('Compact field decoded byte budget or framing exceeded')
    return json.loads(data)


def _packed_decimals(value):
    """Lossless row strings avoid per-node Python allocations in JSON."""
    rows=[[row.tokens if isinstance(row,DecimalRow) else DecimalRow.from_values(row).tokens
           for row in plane] for plane in value]
    return _compress_json(rows,MAX_WIND_FIELD_BYTES)


def _unpacked_decimals(value):
    rows=_expand_json(value,MAX_WIND_FIELD_BYTES)
    return tuple(tuple(DecimalRow(row,row.count(',')+1) for row in plane) for plane in rows)


def coastal_inputs(directory, request, *, cache_directory=None, diagnostics=None):
    directory = Path(directory)
    if cache_directory is None:
        sample = wind_sample(directory / 'met', request)
        payload, audit = freeze_coastal_with_audit(directory / 'marine', request)
        if diagnostics is not None: diagnostics['materialization_cache'] = 'disabled'
        return sample, payload, audit
    names = ('request.json', 'met/inventory.json', 'met/sources.json', 'met/forecast.dds',
             'met/forecast.das', 'met/times.txt', 'met/axes.txt', 'met/coordinates.txt',
             'marine/manifest.json')
    files = {name: directory / name for name in names}
    index = json.loads((directory / 'met/sources.json').read_text())
    for name in index:
        if not isinstance(name,str) or Path(name).name!=name:raise ValueError('Local MET source filename required')
        files['met/' + name] = directory / 'met' / name
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
    identity = {'schema': 3, 'sources': fingerprint(files), 'request': request}
    built_inputs=[]

    def build():
        sample = wind_sample(directory / 'met', request)
        payload, audit = freeze_coastal_with_audit(directory / 'marine', request)
        result = {'projection': sample.projection, 'times': [t.isoformat() for t in sample.times],
                  'model_reference_time': sample.model_reference_time.isoformat(),
                  'source_hashes': sample.source_hashes,
                  'payload': _compress_json(payload,MAX_MARINE_PAYLOAD_BYTES), 'audit': audit}
        for name in ('x_m', 'y_m', 'land_fraction'):
            result[name] = _tokens(getattr(sample, name))
        for name in ('speed_m_s','direction_from_degrees'):
            result[name] = _packed_decimals(getattr(sample,name))
        if fingerprint(files) != identity['sources']:
            raise ValueError('Sources changed during materialization')
        built_inputs.extend((sample,payload,audit))
        return result

    data, status = MaterializedCache(cache_directory).get_or_create(identity, build, reuse_built=True)
    if diagnostics is not None: diagnostics['materialization_cache'] = status
    if status=='miss':return tuple(built_inputs)
    sample = NativeWindSample(data['projection'], *(_decimals(data[n]) for n in ('x_m', 'y_m')),
        tuple(datetime.fromisoformat(t) for t in data['times']),
        *(_unpacked_decimals(data[n]) for n in ('speed_m_s', 'direction_from_degrees')), _decimals(data['land_fraction']),
        datetime.fromisoformat(data['model_reference_time']), tuple(tuple(p) for p in data['source_hashes']))
    return sample, _expand_json(data['payload'],MAX_MARINE_PAYLOAD_BYTES), data['audit']
