"""Real frozen regional inputs retain native values and never certify unknown runs."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from application.regional_forecast import inspect_regional_inputs
from scripts.regional_forecast import load_regional_inputs

ROOT = Path(__file__).resolve().parents[1]
DEPARTURE = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)


class RegionalForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load_regional_inputs(ROOT / 'fixtures')

    def fixtures(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ('met-nordic-metadata', 'met-nordic-wind-sample', 'vinga-copernicus'):
            shutil.copytree(ROOT / 'fixtures' / name, root / name)
        return root

    def test_real_native_nodes_times_and_marine_values_reach_application(self):
        wind = self.inputs.wind
        self.assertEqual((len(wind.times), len(wind.y_m), len(wind.x_m)), (5, 8, 7))
        self.assertEqual(wind.speed_m_s[0][0][0], Decimal('12.970281'))
        self.assertEqual(wind.direction_from_degrees[0][0][0], Decimal('159.0'))
        self.assertEqual(wind.speed_m_s[4][7][6], Decimal('15.915022'))
        self.assertEqual(wind.direction_from_degrees[4][7][6], Decimal('159.0'))
        self.assertEqual(wind.times[0], DEPARTURE)
        self.assertEqual(wind.model_reference_time, datetime(2026, 10, 13, tzinfo=timezone.utc))
        self.assertEqual(len(wind.source_hashes), 6)
        self.assertEqual(len(self.inputs.marine_source_hashes), 3)
        self.assertEqual({p.metadata.product for p in self.inputs.marine.products}, {'waves', 'current'})
        with self.assertRaises(FrozenInstanceError):
            wind.projection = 'EPSG:4326'
        with self.assertRaises(TypeError):
            wind.speed_m_s[0][0][0] = 0

    def test_shared_validity_does_not_authorize_either_route_goal(self):
        report = inspect_regional_inputs(self.inputs, DEPARTURE)
        self.assertTrue(report['common_validity']['departure_supported'])
        self.assertEqual(report['status'], 'data_unavailable')
        self.assertIsNone(report['fastest_candidate'])
        self.assertIsNone(report['comfortable_candidate'])
        self.assertEqual(report['cross_product_run_compatibility'], 'unverified')
        self.assertFalse(report['wind']['land_fraction_is_validity_mask'])
        for product in report['marine'].values():
            self.assertIsNone(product['run_identity'])
            self.assertIsNone(product['model_reference_time'])
            self.assertIsNone(product['issued_at'])
        for reason in ('wind_native_geometry_unqualified', 'wind_vector_frame_unqualified',
                       'model_issue_time_unverified', 'cross_product_model_run_compatibility_unverified',
                       'current_native_wet_mask_unverified'):
            self.assertIn(reason, report['blockers'])

    def test_last_time_and_before_first_time_are_not_supported(self):
        for departure in (datetime(2026, 10, 13, 11, tzinfo=timezone.utc), self.inputs.wind.times[-1]):
            with self.subTest(departure=departure):
                report = inspect_regional_inputs(self.inputs, departure)
                self.assertFalse(report['common_validity']['departure_supported'])
                self.assertIn('departure_outside_common_validity', report['blockers'])
        with self.assertRaises(ValueError):
            inspect_regional_inputs(self.inputs, DEPARTURE.replace(tzinfo=None))

    def test_detached_flags_and_dates_never_supply_marine_run(self):
        root = self.fixtures()
        path = root / 'vinga-copernicus' / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest.update(forecast_issued_at='2026-10-13T00:00:00Z',
                        forecast_reference_time='2026-10-13T00:00:00Z', run_verified=True)
        path.write_text(json.dumps(manifest))
        # Detached reference JSON cannot replace the actual NetCDF samples.
        (root / 'vinga-copernicus' / 'reference.json').write_text('{"verified":true}')
        report = inspect_regional_inputs(load_regional_inputs(root), DEPARTURE)
        self.assertEqual(report, inspect_regional_inputs(self.inputs, DEPARTURE))

    def test_changed_source_bytes_fail_before_application(self):
        for directory, filename in (('met-nordic-wind-sample', 'native-wind-land.txt'),
                                    ('vinga-copernicus', 'waves.nc')):
            with self.subTest(filename=filename):
                root = self.fixtures()
                path = root / directory / filename
                path.write_bytes(path.read_bytes() + b'changed')
                with self.assertRaises(ValueError):
                    load_regional_inputs(root)

    def test_cli_report_is_reproducible(self):
        results = [subprocess.run([sys.executable, '-B', '-m', 'scripts.regional_forecast',
                                  '--departure', '2026-10-13T12:00:00Z'],
                                 cwd=ROOT, capture_output=True, text=True, check=True).stdout
                   for _ in range(2)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(json.loads(results[0]), inspect_regional_inputs(self.inputs, DEPARTURE))

    def test_identity_includes_native_values_not_only_axes_and_source_labels(self):
        wind = self.inputs.wind
        # A changed interior value retains dimensions and every source label.
        rows = list(wind.speed_m_s[0])
        rows[0] = (Decimal('13.5'),) + rows[0][1:]
        altered = replace(wind, speed_m_s=(tuple(rows),) + wind.speed_m_s[1:])
        report = inspect_regional_inputs(replace(self.inputs, wind=altered), DEPARTURE)
        self.assertNotEqual(report['input_sha256'], inspect_regional_inputs(self.inputs, DEPARTURE)['input_sha256'])
        self.assertEqual(report['status'], 'data_unavailable')

    def test_missing_sources_fail_closed_without_disclosing_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-m', 'scripts.regional_forecast',
                                     '--fixtures', directory, '--departure', '2026-10-13T12:00:00Z'],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr.strip(), 'REGIONAL_INPUTS_UNAVAILABLE FileNotFoundError')
