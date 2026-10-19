"""Persistent cache admission, corruption and source-bound exact reader reuse."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from application.coastal_inputs import coastal_inputs, _packed_decimals, _unpacked_decimals, _packed_marine, _unpacked_marine
from infrastructure.materialized_cache import MaterializedCache, fingerprint
from infrastructure.native_wind import NativeWindSample


class MaterializedCacheTests(unittest.TestCase):
    def test_plane_cache_preserves_full_payload_and_exact_total_decoded_budget(self):
        import base64,zlib,copy
        payload={'schema':1,'products':{
            'waves':{'issued_at':None,'times':['historical'],'data':{'VHM0':[[[None,-0.0],[1.25,3.5]],[[7.,8.],[9.,10.]]]}},
            'static':{'depth_units':'m','data':{'mask':[[1,0],[None,1]]}}}}
        original=json.dumps(payload,separators=(',',':'),allow_nan=False)
        packed=_packed_marine(payload)
        self.assertEqual(packed['decoded_bytes'],len(original.encode()))
        self.assertEqual(json.dumps(_unpacked_marine(packed),separators=(',',':'),allow_nan=False),original)
        self.assertEqual(json.dumps(payload,separators=(',',':')),original) # packing never mutates the source
        self.assertEqual(len(packed['fields']['waves']['VHM0']),2)
        with patch('application.coastal_inputs.MAX_MARINE_PAYLOAD_BYTES',len(original.encode())):
            self.assertEqual(_unpacked_marine(_packed_marine(payload)),payload)
        with patch('application.coastal_inputs.MAX_MARINE_PAYLOAD_BYTES',len(original.encode())-1):
            with self.assertRaisesRegex(ValueError,'byte budget'):_packed_marine(payload)
            with self.assertRaisesRegex(ValueError,'byte budget'):_unpacked_marine(packed)
        for kind in ('truncated','trailing','missing','bytes','placeholder'):
            changed=copy.deepcopy(packed)
            if kind in ('truncated','trailing'):
                raw=base64.b64decode(changed['fields']['waves']['VHM0'][0])
                changed['fields']['waves']['VHM0'][0]=base64.b64encode(raw[:-1] if kind=='truncated' else raw+b'trailing').decode()
            elif kind=='missing':del changed['fields']['waves']['VHM0']
            elif kind=='bytes':changed['decoded_bytes']-=1
            else:
                metadata=json.loads(zlib.decompress(base64.b64decode(changed['metadata'])))
                metadata['products']['waves']['data']['VHM0']=[0]
                changed['metadata']=base64.b64encode(zlib.compress(json.dumps(metadata).encode())).decode()
            with self.subTest(kind=kind),self.assertRaises(ValueError):_unpacked_marine(changed)

    def test_compact_rows_preserve_scale_sign_exponent_and_numeric_array_values(self):
        import numpy as np
        values=tuple(Decimal(v) for v in ('1.0000','1','-0.00','0.00','1E+2','1.0000'))
        packed=_packed_decimals(((values,values),))
        result=_unpacked_decimals(json.loads(json.dumps(packed)))
        self.assertEqual([[str(v) for v in row] for row in result[0]],[[str(v) for v in values]]*2)
        np.testing.assert_array_equal(np.array(result,dtype=float),np.array(((values,values),),dtype=float))
        self.assertEqual(result,((values,values),))
        self.assertEqual(result[0][0][-2:],values[-2:])

    def test_compact_fields_reject_truncation_trailing_data_and_decoded_budget_overrun(self):
        import base64,zlib
        packed=_packed_decimals((((Decimal('1.000'),)*10,),))
        raw=base64.b64decode(packed)
        for bad in (raw[:-1],raw+b'trailing'):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'framing'):
                _unpacked_decimals(base64.b64encode(bad).decode())
        with patch('application.coastal_inputs.MAX_WIND_FIELD_BYTES',10):
            with self.assertRaisesRegex(ValueError,'byte budget'):_unpacked_decimals(packed)
            with self.assertRaisesRegex(ValueError,'byte budget'):_packed_decimals((((Decimal('1.000'),)*10,),))

    def test_hit_skips_builder_and_corruption_never_silently_rebuilds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = MaterializedCache(tmp)
            data = {'issued_at': None, 'values': [None, 0., 1.2345678901234567]}
            self.assertEqual(cache.get_or_create({'source': 'a'}, lambda: data), (data, 'miss'))
            def forbidden(): self.fail('A hit must not materialize again')
            self.assertEqual(cache.get_or_create({'source': 'a'}, forbidden), (data, 'hit'))
            path = next(Path(tmp).glob('*.json')); entry = json.loads(path.read_text())
            entry['data'] = '{}'; path.write_text(json.dumps(entry))
            with self.assertRaisesRegex(ValueError, 'integrity'): cache.get_or_create({'source': 'a'}, forbidden)

    def test_source_hash_uses_bytes_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source'; path.write_text('a')
            first = fingerprint({'source': path}); path.write_text('b')
            self.assertNotEqual(first, fingerprint({'source': path}))
            link = Path(tmp) / 'link'; link.symlink_to(path)
            with self.assertRaises(ValueError): fingerprint({'source': link})

    def test_byte_budget_disk_reserve_and_failed_build_do_not_admit_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = MaterializedCache(tmp, max_entry_bytes=250, max_cache_bytes=300)
            with self.assertRaisesRegex(ValueError, 'byte budget'): cache.get_or_create('large', lambda: 'x'*400)
            self.assertFalse(list(Path(tmp).glob('*.json')))
            with patch('infrastructure.materialized_cache.shutil.disk_usage') as usage:
                usage.return_value.free = 0
                with self.assertRaisesRegex(ValueError, 'disk reserve'): cache.get_or_create('disk', lambda: self.fail())
            def failure(): raise RuntimeError('Reader rejected source')
            with self.assertRaises(RuntimeError): cache.get_or_create('failed', failure)
            self.assertFalse(list(Path(tmp).glob('.staging-*')))
            cache.get_or_create('first', lambda: 'x'*20)
            with self.assertRaisesRegex(ValueError, 'byte budget'): cache.get_or_create('second', lambda: 'x'*20)

    def test_persistent_inputs_preserve_decimal_tokens_metadata_and_source_invalidation(self):
        when = datetime(2026, 10, 18, tzinfo=timezone.utc)
        sample = NativeWindSample('test', (Decimal('1.0000'), Decimal('2')), (Decimal('3'), Decimal('4')),
            (when,), (((Decimal('0.000000000000000000001'), Decimal('9.01234567890123456789')),
                       (Decimal('1E+2'), Decimal('2.3000'))),),
            (((Decimal('0'), Decimal('90')), (Decimal('180'), Decimal('360'))),),
            ((Decimal('0'), Decimal('1')), (Decimal('1'), Decimal('0'))), when, (('wind.txt', 'abc'),))
        payload = {'products': {'current': {'issued_at': None, 'value': [None, 1.1]}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'data'; cache = Path(tmp) / 'cache'
            for name in ('request.json', 'met/inventory.json', 'met/sources.json', 'met/forecast.dds',
                         'met/forecast.das', 'met/times.txt', 'met/axes.txt', 'met/coordinates.txt', 'met/wind.txt',
                         'marine/manifest.json', 'marine/waves.nc', 'marine/current.nc', 'marine/wave-mask.nc'):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('frozen')
            (root/'met/sources.json').write_text(json.dumps({'wind.txt':{}}))
            manifest = {'files': [{'filename': name} for name in ('waves.nc', 'current.nc', 'wave-mask.nc')]}
            (root/'marine/manifest.json').write_text(json.dumps(manifest))
            with patch('application.coastal_inputs.wind_sample', return_value=sample) as wind, \
                 patch('application.coastal_inputs.freeze_coastal_with_audit', return_value=(payload, {'routing_enabled': False})) as marine:
                first = coastal_inputs(root, {}, cache_directory=cache)
                diagnostics = {}; second = coastal_inputs(root, {}, cache_directory=cache, diagnostics=diagnostics)
                self.assertEqual(first, second); self.assertEqual(second[0], sample)
                self.assertEqual(str(second[0].speed_m_s[0][1][1]), '2.3000')
                self.assertIsNone(second[1]['products']['current']['issued_at'])
                self.assertEqual(diagnostics['materialization_cache'], 'hit')
                self.assertEqual(wind.call_count, 1); self.assertEqual(marine.call_count, 1)
                (root/'met/forecast.das').write_text('changed')
                coastal_inputs(root, {}, cache_directory=cache)
                self.assertEqual(wind.call_count, 2)
                (root/'marine/current.nc').rename(root/'marine/current-v2.nc')
                manifest['files'][1]['filename'] = 'current-v2.nc'
                (root/'marine/manifest.json').write_text(json.dumps(manifest))
                coastal_inputs(root, {}, cache_directory=cache)
                self.assertEqual(wind.call_count, 3)
                (root/'marine/current-v2.nc').write_text('changed source at manifest-selected filename')
                coastal_inputs(root, {}, cache_directory=cache)
                self.assertEqual(wind.call_count, 4)
