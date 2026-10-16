"""Materialized wind coordinates must use the metadata bytes actually audited."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.audit_met_metadata import bounded_read, read_wind_sample


ROOT = Path(__file__).resolve().parents[1] / 'fixtures'


class METSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('met-nordic-metadata', 'met-nordic-wind-sample'):
            shutil.copytree(ROOT / name, self.root / name)
        self.metadata = self.root / 'met-nordic-metadata'
        self.wind = self.root / 'met-nordic-wind-sample'

    def during_wind_manifest(self, action):
        def read(directory, filename, **kwargs):
            if Path(directory) == self.wind and filename == 'manifest.json':
                action()
            return bounded_read(directory, filename, **kwargs)
        return patch('scripts.audit_met_metadata.bounded_read', side_effect=read)

    def change_maps(self, metadata_name, old, new):
        for path in (self.metadata / metadata_name, self.wind / 'native-wind-land.txt'):
            text = path.read_text()
            self.assertIn(old, text)
            path.write_text(text.replace(old, new))
        manifest_path = self.wind / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        data = (self.wind / 'native-wind-land.txt').read_bytes()
        manifest.update(bytes=len(data), sha256=sha256(data).hexdigest())
        manifest_path.write_text(json.dumps(manifest))

    def test_changed_axis_and_matching_new_wind_maps_cannot_use_old_metadata_hash(self):
        with self.during_wind_manifest(lambda: self.change_maps('native-axes.txt', '-595322.0', '-595321.0')):
            with self.assertRaisesRegex(ValueError, 'native axes'):
                read_wind_sample(self.wind, self.metadata)

    def test_changed_time_and_matching_new_wind_maps_cannot_use_old_metadata_hash(self):
        with self.during_wind_manifest(lambda: self.change_maps('met-time-coordinates.txt',
                                                               '1.7918928E9', '1.7918929E9')):
            with self.assertRaisesRegex(ValueError, 'frozen validity'):
                read_wind_sample(self.wind, self.metadata)

    def test_removing_audited_coordinate_files_does_not_replace_in_memory_snapshot(self):
        expected = read_wind_sample(self.wind, self.metadata)
        def remove():
            (self.metadata / 'native-axes.txt').unlink()
            (self.metadata / 'met-time-coordinates.txt').unlink()
        with self.during_wind_manifest(remove):
            self.assertEqual(read_wind_sample(self.wind, self.metadata), expected)
