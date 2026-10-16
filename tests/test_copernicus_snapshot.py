"""Audits and payloads must decode the same bytes whose hashes they report."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import xarray as xr

from scripts.audit_copernicus import audit
from scripts.freeze_copernicus_reference import freeze


FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/vinga-copernicus'


class CopernicusSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'marine'
        shutil.copytree(FIXTURE, self.directory)
        self.original_open = xr.open_dataset
        path = self.directory / 'waves.nc'
        with xr.open_dataset(path, engine='h5netcdf') as ds:
            changed = ds.load()
        changed['VHM0'].values[:] = 9
        altered = Path(temporary.name) / 'changed.nc'
        changed.to_netcdf(altered, engine='h5netcdf')
        self.altered = altered.read_bytes()

    def on_open(self, ordinal, action):
        count = 0
        def open_dataset(*args, **kwargs):
            nonlocal count
            count += 1
            if count == ordinal:
                action()
            return self.original_open(*args, **kwargs)
        return patch('xarray.open_dataset', side_effect=open_dataset)

    def change_wave(self):
        (self.directory / 'waves.nc').write_bytes(self.altered)

    def test_audit_decodes_hashed_bytes_after_source_path_changes(self):
        expected = audit(self.directory)
        with self.on_open(1, self.change_wave):
            actual = audit(self.directory)
        expected.pop('audited_at')
        actual.pop('audited_at')
        self.assertEqual(actual, expected)

    def test_freeze_cannot_reopen_changed_file_under_audited_hash(self):
        expected = freeze(self.directory)
        # Three source products were audited; the next decode materializes payload.
        with self.on_open(4, self.change_wave):
            self.assertEqual(freeze(self.directory), expected)

    def test_freeze_cannot_replace_manifest_identity_after_audit_started(self):
        expected = freeze(self.directory)
        def change_manifest():
            path = self.directory / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest['files'][0]['version'] = 'unreviewed-replacement'
            path.write_text(json.dumps(manifest))
        with self.on_open(3, change_manifest):
            self.assertEqual(freeze(self.directory), expected)

    def test_oversized_source_is_rejected_before_any_decoder(self):
        (self.directory / 'waves.nc').write_bytes(b'x' * 10_000_001)
        with patch('xarray.open_dataset') as decoder:
            with self.assertRaisesRegex(ValueError, 'size budget'):
                audit(self.directory)
            decoder.assert_not_called()
