"""Storage dimension order cannot move marine values between geographic nodes."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import xarray as xr

from scripts.freeze_copernicus_reference import freeze

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/vinga-copernicus'


class CopernicusAxisOrderTests(unittest.TestCase):
    def test_storage_permutations_preserve_each_products_geographic_values(self):
        expected = freeze(FIXTURE)
        for label, filename, fields in (
                ('waves', 'waves.nc', ('VHM0', 'VTM02', 'VMDR')),
                ('current', 'current.nc', ('uo', 'vo')),
                ('static', 'wave-mask.nc', ('mask', 'deptho'))):
            with self.subTest(product=label), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / 'marine'
                shutil.copytree(FIXTURE, directory)
                path = directory / filename
                with xr.open_dataset(path, engine='h5netcdf') as ds:
                    changed = ds.load()
                for name in fields:
                    # Reverse every dimension, including time and depth where present.
                    changed[name] = changed[name].transpose(*reversed(changed[name].dims))
                changed.to_netcdf(path, engine='h5netcdf')
                manifest_path = directory / 'manifest.json'
                manifest = json.loads(manifest_path.read_text())
                for entry in manifest['files']:
                    if entry['filename'] == filename:
                        entry['sha256'] = sha256(path.read_bytes()).hexdigest()
                manifest_path.write_text(json.dumps(manifest))
                actual = freeze(directory)
                for product in expected['products']:
                    self.assertEqual(actual['products'][product]['data'], expected['products'][product]['data'])
                    self.assertEqual(actual['products'][product]['latitude'], expected['products'][product]['latitude'])
                    self.assertEqual(actual['products'][product]['longitude'], expected['products'][product]['longitude'])
                    self.assertIsNone(actual['products'][product]['issued_at'])
