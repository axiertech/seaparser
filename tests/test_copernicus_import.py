"""Request selection and required offline NetCDF integration regressions."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from infrastructure.copernicus_fields import CURRENT_FIELDS, WAVE_FIELDS
from scripts.download_copernicus import selection


class RequestSelectionTests(unittest.TestCase):
    def catalogue(self, fields, depths=()):
        variables = [NS(short_name=n, standard_name=v[0], units=v[1][0], coordinates=list(depths))
                     for n, v in fields.items()]
        service = NS(service_name='arco-geo-series', variables=variables)
        part = NS(name='default', retired_date=None, services=[service])
        version = NS(label='202511', parts=[part])
        return NS(products=[NS(datasets=[NS(dataset_id='test', versions=[version])])])

    def test_pin_version_and_part_without_credentials(self):
        request = selection(self.catalogue(WAVE_FIELDS), 'test', WAVE_FIELDS)
        self.assertEqual(request['dataset_version'], '202511')
        self.assertEqual(request['dataset_part'], 'default')
        self.assertEqual(request['variables'], ['VHM0', 'VTM02', 'VMDR'])
        self.assertNotIn('username', request)
        self.assertNotIn('password', request)

    def test_shallow_single_current_depth(self):
        depth = NS(coordinate_id='depth', coordinate_unit='m', minimum_value=0.5)
        request = selection(self.catalogue(CURRENT_FIELDS, (depth,)), 'test', CURRENT_FIELDS)
        self.assertEqual((request['minimum_depth'], request['maximum_depth']), (0.5, 1.0))
        depth.coordinate_unit = 'unknown'
        with self.assertRaises(ValueError):
            selection(self.catalogue(CURRENT_FIELDS, (depth,)), 'test', CURRENT_FIELDS)

    def test_ambiguous_part_and_missing_field_rejected(self):
        catalogue = self.catalogue(WAVE_FIELDS)
        version = catalogue.products[0].datasets[0].versions[0]
        version.parts.append(version.parts[0])
        with self.assertRaises(ValueError):
            selection(catalogue, 'test', WAVE_FIELDS)
        with self.assertRaises(ValueError):
            selection(self.catalogue(CURRENT_FIELDS), 'test', WAVE_FIELDS)


class FrozenCopernicusFixtureTests(unittest.TestCase):
    def test_raw_files_recreate_the_checked_provider_payload(self):
        from scripts.freeze_copernicus_reference import freeze
        directory = Path(__file__).resolve().parents[1] / 'fixtures' / 'vinga-copernicus'
        expected = json.loads((directory / 'reference.json').read_text())
        self.assertEqual(freeze(directory), expected)


class NetCDFAuditTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import xarray as xr
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        lat = xr.DataArray([57.63, 57.645], dims=['lat'], attrs={'standard_name': 'latitude', 'units': 'degrees_north'})
        lon = xr.DataArray([11.59, 11.62], dims=['lon'], attrs={'standard_name': 'longitude', 'units': 'degrees_east'})
        time = xr.DataArray(np.arange(np.datetime64('2026-10-13T12'), np.datetime64('2026-10-13T17'), np.timedelta64(1, 'h')),
                            dims=['time'], attrs={'standard_name': 'time'})
        waves = xr.Dataset(coords={'lat': lat, 'lon': lon, 'time': time})
        for name, field in WAVE_FIELDS.items():
            val = 1 if name == 'VHM0' else (6 if name == 'VTM02' else 90)
            waves[name] = xr.DataArray(np.full((5, 2, 2), val, dtype=float), dims=['time', 'lat', 'lon'],
                                      attrs={'standard_name': field[0], 'units': field[1][0]})
        depth = xr.DataArray([0.5], dims=['depth'], attrs={'standard_name': 'depth', 'positive': 'down', 'units': 'm'})
        current = xr.Dataset(coords={'lat': lat, 'lon': lon, 'time': time, 'depth': depth})
        for name, field in CURRENT_FIELDS.items():
            current[name] = xr.DataArray(np.full((5, 1, 2, 2), -0.3 if name == 'uo' else 0.4),
                                        dims=['time', 'depth', 'lat', 'lon'],
                                        attrs={'standard_name': field[0], 'units': field[1][0]})
        mask = xr.Dataset(coords={'lat': lat, 'lon': lon})
        mask['mask'] = xr.DataArray([[1., 0.], [1., 1.]], dims=['lat', 'lon'],
                                   attrs={'standard_name': 'sea_binary_mask', 'units': '1'})
        for name, data in (('waves', waves), ('current', current), ('wave-mask', mask)):
            data.to_netcdf(self.directory / f'{name}.nc')
        self.refresh_manifest()

    def refresh_manifest(self):
        files = [{'filename': p.name, 'sha256': sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(self.directory.glob('*.nc'))]
        (self.directory / 'manifest.json').write_text(json.dumps({'schema': 1, 'files': files}))

    def test_offline_netcdf_fields_and_gaps_not_routing(self):
        from scripts.audit_copernicus import audit
        report = audit(self.directory)
        self.assertEqual(report['adapter_sample_checks'], 'passed')
        self.assertEqual(report['normalized_wave_gaps'], 5)
        self.assertEqual(report['normalized_current_gaps'], 0)
        self.assertEqual(report['current']['surface_depth_m'], 0.5)
        self.assertEqual(report['status'], 'regional_routing_unavailable')
        self.assertIn('regional_wind_forecast_missing', report['blockers'])
        self.assertIn('waves_model_issue_time_missing', report['blockers'])

    def test_hash_mismatch_rejected(self):
        from scripts.audit_copernicus import audit
        path = self.directory / 'waves.nc'
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            audit(self.directory)

    def test_cf_model_reference_time_does_not_certify_issuance(self):
        import numpy as np
        import xarray as xr
        from scripts.audit_copernicus import audit
        for label in ('waves', 'current'):
            path = self.directory / f'{label}.nc'
            with xr.open_dataset(path) as ds:
                product = ds.load()
            product['model_reference'] = xr.DataArray(np.datetime64('2026-10-13T06:00:00'),
                attrs={'standard_name': 'forecast_reference_time'})
            product.attrs['creation_date'] = '2026-10-13T07:00:00Z'
            product.to_netcdf(path)
        self.refresh_manifest()
        report = audit(self.directory)
        for label in ('waves', 'current'):
            self.assertEqual(report[label]['forecast_reference_time'], '2026-10-13T06:00:00Z')
            self.assertIsNone(report[label]['issued_at'])
            self.assertIn(f'{label}_model_issue_time_missing', report['blockers'])
        self.assertIn('cross_product_model_run_compatibility_not_verified', report['blockers'])
        self.assertEqual(report['status'], 'regional_routing_unavailable')

    def test_subsecond_validity_shift_cannot_be_hidden_by_truncation(self):
        import numpy as np
        import xarray as xr
        from scripts.audit_copernicus import audit
        path = self.directory / 'waves.nc'
        with xr.open_dataset(path) as ds:
            original = ds.load()
        for all_times in (False, True):
            with self.subTest(all_times=all_times):
                product = original.copy(deep=True)
                shifted = product.time.values.copy()
                if all_times:
                    shifted += np.timedelta64(250, 'ms')
                else:
                    shifted[2] += np.timedelta64(250, 'ms')
                product = product.assign_coords(time=xr.DataArray(shifted, dims=['time'],
                    attrs={'standard_name': 'time'}))
                product.to_netcdf(path)
                self.refresh_manifest()
                with self.assertRaisesRegex(ValueError, 'exact five hourly validity'):
                    audit(self.directory)

    def test_model_reference_precision_is_preserved_for_review(self):
        import numpy as np
        import xarray as xr
        from scripts.audit_copernicus import audit
        path = self.directory / 'waves.nc'
        with xr.open_dataset(path) as ds:
            product = ds.load()
        product['model_reference'] = xr.DataArray(np.datetime64('2026-10-13T06:00:00.250'),
            attrs={'standard_name': 'forecast_reference_time'})
        product.to_netcdf(path)
        self.refresh_manifest()
        report = audit(self.directory)
        self.assertEqual(report['waves']['forecast_reference_time'], '2026-10-13T06:00:00.250Z')
        self.assertIsNone(report['waves']['issued_at'])
        self.assertIn('waves_model_issue_time_missing', report['blockers'])

    def test_ambiguous_or_undecoded_model_reference_stays_unknown(self):
        import numpy as np
        import xarray as xr
        from scripts.audit_copernicus import audit
        path = self.directory / 'waves.nc'
        with xr.open_dataset(path) as ds:
            original = ds.load()
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous):
                product = original.copy(deep=True)
                value = np.datetime64('2026-10-13T06:00:00') if ambiguous else 123.0
                product['reference_a'] = xr.DataArray(value, attrs={'standard_name': 'forecast_reference_time'})
                if ambiguous:
                    product['reference_b'] = product['reference_a'].copy()
                product.to_netcdf(path)
                self.refresh_manifest()
                report = audit(self.directory)
                self.assertIsNone(report['waves']['forecast_reference_time'])
                self.assertIsNone(report['waves']['issued_at'])
                self.assertIn('waves_model_issue_time_missing', report['blockers'])

    def test_static_mask_cannot_be_regridded_implicitly(self):
        import xarray as xr
        from scripts.audit_copernicus import audit
        path = self.directory / 'wave-mask.nc'
        with xr.open_dataset(path) as ds:
            mask = ds.load()
        attrs = dict(mask['lon'].attrs)
        mask = mask.assign_coords(lon=xr.DataArray([11.60, 11.62], dims=['lon'], attrs=attrs))
        mask.to_netcdf(path)
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, 'exact native wave grid'):
            audit(self.directory)

    def test_wrong_wave_period_metadata_rejected(self):
        import xarray as xr
        from scripts.audit_copernicus import audit
        path = self.directory / 'waves.nc'
        with xr.open_dataset(path) as ds:
            waves = ds.load()
        waves['VTM02'].attrs['standard_name'] = 'sea_surface_wave_period_at_variance_spectral_density_maximum'
        waves.to_netcdf(path)
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, 'VTM02'):
            audit(self.directory)
