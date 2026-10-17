"""Analytical source subsets and cell completeness; no network or routing shortcuts."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from infrastructure.copernicus_fields import WAVE_FIELDS
from scripts.copernicus_budget import digest,request_key
from scripts.extract_cached_wave import extract
from scripts.survey_marine_support import survey


class MarineExpansionTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import xarray as xr
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        ds=xr.Dataset(coords={
            'lat':xr.DataArray([57.60,57.62,57.64,57.66],dims='lat',attrs={'standard_name':'latitude','units':'degrees_north'}),
            'lon':xr.DataArray([11.55,11.58,11.61,11.64],dims='lon',attrs={'standard_name':'longitude','units':'degrees_east'}),
            'time':xr.DataArray(np.arange(np.datetime64('2026-10-17T01'),np.datetime64('2026-10-17T04'),np.timedelta64(1,'h')),dims='time',attrs={'standard_name':'time'})})
        for name,field in WAVE_FIELDS.items():
            values=np.ones((3,4,4),dtype=np.float32)*(6 if name=='VTM02' else 90 if name=='VMDR' else 1)
            if name=='VHM0':
                values=np.array([[[1+k+j/10+i/100 for i in range(4)] for j in range(4)] for k in range(3)],dtype=np.float32)
            ds[name]=xr.DataArray(values,dims=('time','lat','lon'),attrs={'standard_name':field[0],'units':field[1][0]})
        path=self.root/'original.nc';ds.to_netcdf(path,engine='h5netcdf');self.source=ds
        source={'s3_object':'s3://analytical-reference/source.nc','etag':'abcd','bytes':float(path.stat().st_size),'last_modified_datetime':None}
        identity=dict(kind='original',dataset_id='cmems_mod_bal_wav_anfc_PT1H-i',dataset_version='202311',dataset_part='default',**source)
        key=request_key(identity);cache=self.root/'cache'/key;cache.mkdir(parents=True)
        path.rename(cache/'data.nc');self.cached=cache/'data.nc'
        record=dict(key=key,bytes=self.cached.stat().st_size,sha256=digest(self.cached),cached_at_epoch=time.time(),
                    retrieved_at='2026-10-17T10:00:00Z',estimated_result_bytes=100,estimated_transfer_bytes=100)
        (cache/'entry.json').write_text(json.dumps(record))
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps(dict(scope='original_file_diagnostic',
            dataset_id=identity['dataset_id'],dataset_version=identity['dataset_version'],dataset_part='default',
            source=source,cache_key=key,sha256=record['sha256'])))

    def extract(self,**changes):
        args=dict(manifest_path=self.manifest,cache=self.root/'cache',output=self.root/'out',
                  bbox=[11.57,57.61,11.62,57.65],start='2026-10-17T01:00:00Z',end='2026-10-17T03:00:00Z')
        return extract(**(args|changes))

    def test_exact_values_and_producer_times_survive_local_subset(self):
        import numpy as np
        import xarray as xr
        report=self.extract()
        self.assertEqual(report['dimensions'],dict(time=3,latitude=2,longitude=2))
        self.assertEqual(report['estimated_transfer_bytes_this_run'],0)
        self.assertIsNone(report['issued_at']);self.assertFalse(report['arco_lineage_verified'])
        with xr.open_dataset(self.root/'out/waves.nc',engine='h5netcdf') as actual:
            for name in WAVE_FIELDS:
                np.testing.assert_array_equal(actual[name].values,self.source[name].values[:,1:3,1:3])
            np.testing.assert_array_equal(actual.time.values,self.source.time.values)
        result=survey(self.root/'out/waves.nc','waves')
        self.assertEqual(result['all_time_value_complete_cells'],1)
        self.assertEqual(result['time_count'],3)
        self.assertFalse(result['routing_enabled'])
        self.assertFalse(result['cells']['features'][0]['properties']['validity_mask_qualified'])

    def test_corrupt_cache_and_incomplete_time_are_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError,'complete bounded time'):self.extract(end='2026-10-17T04:00:00Z')
        self.assertFalse((self.root/'out').exists())
        self.cached.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'hash/identity'):self.extract()
        self.assertFalse((self.root/'out').exists())

    def test_a_single_missing_corner_removes_full_window_value_completeness(self):
        import xarray as xr
        self.extract();path=self.root/'out/waves.nc'
        with xr.open_dataset(path,engine='h5netcdf') as original:ds=original.load()
        ds['VHM0'].values[1,0,0]=float('nan');ds.to_netcdf(self.root/'gap.nc',engine='h5netcdf')
        r=survey(self.root/'gap.nc','waves')
        self.assertEqual(r['field_counts']['VHM0']['missing_or_invalid'],1)
        self.assertEqual(r['all_time_value_complete_cells'],0)
        self.assertFalse(r['routing_enabled'])

    def test_estimate_only_never_downloads_or_copies_weather(self):
        from scripts.download_copernicus import main
        from tests.test_copernicus_import import RequestSelectionTests
        catalogue=RequestSelectionTests().catalogue(WAVE_FIELDS)
        catalogue.products[0].datasets[0].dataset_id='cmems_mod_bal_wav_anfc_PT1H-i'
        calls=[]
        def subset(**kw):
            self.assertTrue(kw.get('dry_run'));calls.append(kw)
            return NS(file_size=.02,data_transfer_size=100)
        marine=NS(__version__='2.5.0',describe=lambda **kw:catalogue,subset=subset)
        with patch.dict('sys.modules',copernicusmarine=marine),patch('scripts.download_copernicus.socket.getaddrinfo'),patch(
            'scripts.copernicus_budget.shutil.disk_usage',return_value=NS(free=30_000_000_000)):
            main(['--output',str(self.root/'plan'),'--cache',str(self.root/'plan-cache'),'--products','waves','--estimate-only'])
        self.assertEqual(len(calls),1)
        self.assertFalse(list(self.root.rglob('plan*/*.nc')))
        self.assertEqual(json.loads((self.root/'plan/manifest.json').read_text())['files'][0]['status'],'estimate_only')


    def test_wave_mask_must_use_own_grid_and_cannot_qualify_current(self):
        import xarray as xr
        self.extract();path=self.root/'out/waves.nc'
        mask=xr.Dataset(coords={'latitude':xr.DataArray([57.62,57.64],dims='latitude',attrs={'standard_name':'latitude','units':'degrees_north'}),
                                'longitude':xr.DataArray([11.58,11.61],dims='longitude',attrs={'standard_name':'longitude','units':'degrees_east'})})
        mask['mask']=xr.DataArray([[1,0],[1,1]],dims=('latitude','longitude'),attrs={'standard_name':'sea_binary_mask','units':'1'})
        mp=self.root/'mask.nc';mask.to_netcdf(mp,engine='h5netcdf')
        report=survey(path,'waves',mp)
        self.assertTrue(report['wave_mask_native_alignment_verified'])
        self.assertFalse(report['cells']['features'][0]['properties']['wave_mask_all_corners_wet'])
        with self.assertRaisesRegex(ValueError,'cannot qualify current'):survey(path,'current',mp)
        mask=mask.assign_coords(longitude=mask.longitude+.001)
        mask.longitude.attrs={'standard_name':'longitude','units':'degrees_east'}
        mask.to_netcdf(self.root/'shift.nc',engine='h5netcdf')
        with self.assertRaisesRegex(ValueError,'Exact own wave-mask'):survey(path,'waves',self.root/'shift.nc')


class FrozenExpandedForecastTests(unittest.TestCase):
    def test_actual_expanded_bundle_has_separate_grids_and_preserved_blockers(self):
        from scripts.inspect_expanded_forecast import inspect,ROOT
        report=inspect(ROOT/'fixtures/vinga-expanded-20261017')
        expected=json.loads((ROOT/'artifacts/expanded-forecast-support/report.json').read_text())
        self.assertEqual(report,expected)
        self.assertEqual(report['wind']['native_node_count'],132)
        self.assertEqual(report['wind']['time_count'],12)
        for product in ('waves','current'):
            self.assertEqual(report[product]['node_count'],16)
            self.assertEqual(report[product]['all_time_value_complete_cells'],9)
            self.assertFalse(report[product]['existing_adapter_geometry_compatible'])
        self.assertNotEqual(report['waves']['latitude'],report['current']['latitude'])
        self.assertTrue(report['waves']['wave_mask_native_alignment_verified'])
        self.assertIsNone(report['current']['wave_mask_sha256'])
        self.assertFalse(report['full_space_time_support_verified'])
        self.assertFalse(report['routing_enabled'])
        self.assertTrue(all(x is None for x in report['source_issued_at'].values()))
        self.assertEqual(report['unchanged_runtime']['development_support_radius_m'],900)

    def test_legacy_reference_pin_is_not_silently_replaced_by_later_source(self):
        from scripts.audit_met_metadata import read_wind_sample
        from scripts.inspect_expanded_forecast import ROOT
        root=ROOT/'fixtures/vinga-expanded-20261017'
        with self.assertRaisesRegex(ValueError,'Model reference differs'):
            read_wind_sample(root/'met-nordic-wind-sample',root/'met-nordic-metadata')

    def test_existing_met_snapshot_is_reused_without_network(self):
        from scripts.capture_met_window import capture
        with tempfile.TemporaryDirectory() as temp,patch('scripts.capture_met_window.MET_OPENER.open') as request:
            with self.assertRaisesRegex(ValueError,'reused'):capture(temp,'2026-10-17')
            request.assert_not_called()
