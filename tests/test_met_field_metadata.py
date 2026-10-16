"""Changed source semantics cannot be accepted just by refreshing a hash."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_met_metadata import audit, read_wind_sample


ROOT = Path(__file__).resolve().parents[1]


class METFieldMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'metadata'
        shutil.copytree(ROOT / 'fixtures/met-nordic-metadata', self.directory)

    def modify(self, field, old, new):
        path = self.directory / 'met-forecast.das'
        text = (ROOT / 'fixtures/met-nordic-metadata/met-forecast.das').read_text()
        start = text.index('    ' + field + ' {\n')
        end = text.index('    }', start)
        block = text[start:end]
        self.assertIn(old, block)
        path.write_text(text[:start] + block.replace(old, new, 1) + text[end:])
        manifest_path = self.directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest['files']:
            if entry['filename'] == path.name:
                data = path.read_bytes()
                entry.update(bytes=len(data), sha256=sha256(data).hexdigest())
        manifest_path.write_text(json.dumps(manifest))

    def test_changed_units_are_rejected_before_reading_wind_values(self):
        for field, old, new in (('wind_speed_10m', 'm/s', 'knots'),
                                ('wind_direction_10m', 'degree', 'radian'),
                                ('land_area_fraction', '1', 'percent')):
            with self.subTest(field=field):
                self.modify(field, f'String units "{old}";', f'String units "{new}";')
                with self.assertRaisesRegex(ValueError, 'field attributes'):
                    # A missing wind directory proves metadata fails before value I/O.
                    read_wind_sample(self.directory / 'missing-wind', self.directory)

    def test_changed_meaning_mapping_and_coordinate_links_are_rejected(self):
        cases = (('wind_direction_10m', 'wind_from_direction', 'wind_to_direction'),
                 ('wind_speed_10m', 'wind_speed', 'wind_speed_of_gust'),
                 ('land_area_fraction', 'land_area_fraction', 'sea_binary_mask'),
                 ('wind_speed_10m', 'projection_lcc', 'unknown_crs'),
                 ('wind_direction_10m', 'longitude latitude', 'grid_longitude grid_latitude'))
        for field, old, new in cases:
            with self.subTest(field=field, changed=old):
                self.modify(field, f'"{old}"', f'"{new}"')
                with self.assertRaisesRegex(ValueError, 'field attributes'):
                    audit(self.directory)

    def test_missing_duplicate_or_retyped_attribute_is_rejected(self):
        original = 'String units "m/s";'
        for replacement in ('', original + '\n        ' + original, 'Float32 units "m/s";'):
            with self.subTest(replacement=replacement):
                self.modify('wind_speed_10m', original, replacement)
                with self.assertRaisesRegex(ValueError, 'field attributes'):
                    audit(self.directory)

    def test_unreviewed_scaling_missing_and_averaging_semantics_are_rejected(self):
        for declaration in ('Float32 scale_factor 0.1;', 'Float32 add_offset 10;',
                            'Float32 _FillValue 9999;', 'Float32 missing_value 9999;',
                            'String cell_methods "time: maximum";'):
            with self.subTest(declaration=declaration):
                self.modify('wind_speed_10m', 'String units "m/s";',
                            'String units "m/s";\n        ' + declaration)
                with self.assertRaisesRegex(ValueError, 'field attributes'):
                    audit(self.directory)
