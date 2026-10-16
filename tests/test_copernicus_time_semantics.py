"""Changed temporal meaning cannot be accepted by refreshing a raw-file hash."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import h5netcdf
from scripts.audit_copernicus import audit

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/vinga-copernicus'


class MarineTimeSemanticsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'marine'
        shutil.copytree(FIXTURE, self.directory)

    def change(self, filename, variable, attribute, value):
        path = self.directory / filename
        shutil.copyfile(FIXTURE / filename, path)
        with h5netcdf.File(path, 'a') as dataset:
            attrs = dataset.variables[variable].attrs
            if value is None:
                del attrs[attribute]
            else:
                attrs[attribute] = value
        manifest_path = self.directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest['files']:
            if entry['filename'] == filename:
                entry['sha256'] = sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))

    def test_changed_or_missing_wave_mean_is_rejected(self):
        for name in ('VHM0', 'VTM02', 'VMDR'):
            for method in ('time: maximum', None):
                with self.subTest(field=name, method=method):
                    self.change('waves.nc', name, 'cell_methods', method)
                    with self.assertRaisesRegex(ValueError, 'temporal semantics'):
                        audit(self.directory)

    def test_added_current_mean_and_unreviewed_time_domains_are_rejected(self):
        changes = [('current.nc', name, 'cell_methods', 'time: mean')
                   for name in ('uo', 'vo')]
        changes += [(filename, 'time', attribute, 'time_bounds')
                    for filename in ('waves.nc', 'current.nc')
                    for attribute in ('bounds', 'climatology')]
        for filename, variable, attribute, value in changes:
            with self.subTest(filename=filename, variable=variable, attribute=attribute):
                # Keep independent source files pristine between mutations.
                for source in ('waves.nc', 'current.nc'):
                    shutil.copyfile(FIXTURE / source, self.directory / source)
                shutil.copyfile(FIXTURE / 'manifest.json', self.directory / 'manifest.json')
                self.change(filename, variable, attribute, value)
                with self.assertRaisesRegex(ValueError, 'temporal semantics'):
                    audit(self.directory)

    def test_real_mean_semantics_are_reported_without_invented_time_bounds(self):
        report = audit(self.directory)
        self.assertEqual(report['waves']['temporal_support'], 'unverified')
        self.assertIsNone(report['waves']['time_bounds'])
        for name in ('VHM0', 'VTM02', 'VMDR'):
            self.assertEqual(report['waves']['variables'][name]['cell_methods'], 'time: mean')
        self.assertEqual(report['current']['temporal_support'], 'unverified')
        self.assertIsNone(report['current']['time_bounds'])
        for name in ('uo', 'vo'):
            self.assertIsNone(report['current']['variables'][name]['cell_methods'])
        self.assertIsNone(report['waves']['issued_at'])
        self.assertEqual(report['status'], 'regional_routing_unavailable')
