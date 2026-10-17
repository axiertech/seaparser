"""Independent temporal/coordinate witnesses for the offline WAV comparison."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
import xarray as xr

from infrastructure.copernicus_fields import WAVE_FIELDS
from scripts.compare_wave_original import compare


class CompareOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=self.root/'original.nc';self.arco=self.root/'arco.nc'
        epoch=1792195200
        self.source=xr.Dataset(coords={'time':('time',epoch+np.arange(1,6)*3600,
                                               {'units':'seconds since 1970-01-01','calendar':'standard'}),
                                       'lat':[57.62,57.64],'lon':[11.59,11.62]})
        self.target=xr.Dataset(coords={'time':('time',epoch+np.arange(5)*3600,
                                               {'units':'seconds since 1970-01-01 00:00:00','calendar':'standard'}),
                                       'latitude':[57.62,57.64],'longitude':[11.59,11.62]})
        for i,(name,(standard,units)) in enumerate(WAVE_FIELDS.items()):
            attrs={'standard_name':standard,'units':units[0],'_FillValue':-9999999.}
            values=np.broadcast_to(np.arange(1,6)[:,None,None]+i*10,(5,2,2)).astype('float32').copy()
            self.source[name]=xr.DataArray(values,dims=('time','lat','lon'),attrs=attrs)
            self.target[name]=xr.DataArray(values.copy(),dims=('time','latitude','longitude'),
                                           attrs=dict(attrs,cell_methods='time: mean'))

    def save(self):
        self.source.to_netcdf(self.original,engine='h5netcdf')
        self.target.to_netcdf(self.arco,engine='h5netcdf')

    def test_shifted_numeric_equality_does_not_qualify_lineage_or_time_support(self):
        self.save();result=compare(self.original,self.arco)
        same,shifted=result['hypotheses']
        self.assertEqual(same['fields']['VHM0']['compared_valid_values'],16)
        self.assertEqual(same['fields']['VHM0']['exact_equal_values'],0)
        self.assertEqual(same['fields']['VHM0']['max_absolute_difference'],1.)
        self.assertFalse(same['complete_time_coverage'])
        self.assertTrue(shifted['complete_time_coverage'])
        self.assertEqual(shifted['fields']['VHM0']['exact_equal_values'],20)
        self.assertFalse(result['arco_lineage_verified'])
        self.assertFalse(result['publication_time_verified'])
        self.assertFalse(result['time_support_qualified'])

    def test_missing_values_are_not_equal_scientific_samples(self):
        self.source.VHM0.values[0,0,0]=-9999999
        self.target.VHM0.values[0,0,0]=-9999999
        self.save();field=compare(self.original,self.arco)['hypotheses'][1]['fields']['VHM0']
        self.assertEqual(field['excluded_missing_values'],1)
        self.assertEqual(field['compared_valid_values'],19)
        self.assertEqual(field['exact_equal_values'],19)

    def test_nearby_coordinate_is_rejected_without_interpolation(self):
        self.target=self.target.assign_coords(latitude=[57.620001,57.64]);self.save()
        with self.assertRaisesRegex(ValueError,'Exact unique'):
            compare(self.original,self.arco)

    def test_same_time_match_does_not_imply_hour_shift(self):
        for name in WAVE_FIELDS:
            self.target[name].values[:]-=1
        self.save();same,shifted=compare(self.original,self.arco)['hypotheses']
        for name in WAVE_FIELDS:
            self.assertEqual(same['fields'][name]['exact_equal_values'],16)
            self.assertEqual(same['fields'][name]['max_absolute_difference'],0.)
            self.assertEqual(shifted['fields'][name]['exact_equal_values'],0)

    def test_packed_or_different_unit_fields_are_not_raw_compared(self):
        self.source.VHM0.attrs['scale_factor']=.01;self.save()
        with self.assertRaisesRegex(ValueError,'unpacked float32'):
            compare(self.original,self.arco)

    def test_fractional_timestamps_are_not_rounded_into_matches(self):
        self.target=self.target.assign_coords(time=self.target.time.astype('float64')+.5)
        self.target.time.attrs=dict(self.source.time.attrs)
        self.save()
        with self.assertRaisesRegex(ValueError,'whole-second'):
            compare(self.original,self.arco)
