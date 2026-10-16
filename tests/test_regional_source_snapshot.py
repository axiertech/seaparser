"""Regional marine values and model references must describe one audited read."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import xarray as xr

from scripts.regional_forecast import load_regional_inputs


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'


class RegionalSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('met-nordic-metadata', 'met-nordic-wind-sample', 'vinga-copernicus'):
            shutil.copytree(FIXTURES / name, self.root / name)
        self.marine = self.root / 'vinga-copernicus'
        self.expected = load_regional_inputs(self.root)
        self.original_open = xr.open_dataset

    def after_regional_source_read(self, action):
        count = 0
        def open_dataset(*args, **kwargs):
            nonlocal count
            count += 1
            # Three diagnostic decodes, then three regional source-audit decodes.
            if count == 6:
                action()
            return self.original_open(*args, **kwargs)
        return patch('xarray.open_dataset', side_effect=open_dataset)

    def test_replaced_wave_and_manifest_cannot_mix_old_references_with_new_values(self):
        with xr.open_dataset(self.marine / 'waves.nc', engine='h5netcdf') as ds:
            changed = ds.load()
        changed['VHM0'].values[:] = 9
        changed['model_reference'] = xr.DataArray(np.datetime64('2026-10-13T06:00:00'),
            attrs={'standard_name': 'forecast_reference_time'})
        altered = self.root / 'altered.nc'
        changed.to_netcdf(altered, engine='h5netcdf')
        data = altered.read_bytes()
        def replace():
            (self.marine / 'waves.nc').write_bytes(data)
            path = self.marine / 'manifest.json'
            manifest = json.loads(path.read_text())
            for entry in manifest['files']:
                if entry['filename'] == 'waves.nc':
                    entry['sha256'] = sha256(data).hexdigest()
            path.write_text(json.dumps(manifest))
        with self.after_regional_source_read(replace):
            actual = load_regional_inputs(self.root)
        self.assertEqual(actual, self.expected)
        hashes = dict(actual.marine_source_hashes)
        for product in actual.marine.products:
            name = 'waves.nc' if product.metadata.product == 'waves' else 'current.nc'
            self.assertEqual(product.metadata.source_sha256, hashes[name])
            self.assertIsNone(product.metadata.issued_at)

    def test_materialization_uses_captured_sources_after_files_are_removed(self):
        def remove():
            for name in ('manifest.json', 'waves.nc', 'current.nc', 'wave-mask.nc'):
                (self.marine / name).unlink()
        with self.after_regional_source_read(remove):
            self.assertEqual(load_regional_inputs(self.root), self.expected)
