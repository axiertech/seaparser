"""Real regional endpoint gaps cannot turn into routes or fabricated metrics."""
import json
from pathlib import Path
import unittest
import numpy as np
import xarray as xr
from scripts.build_uddevalla import marine_probe

ROOT=Path(__file__).resolve().parents[1]

class UddevallaPreflightTests(unittest.TestCase):
    def test_real_frozen_case_blocks_every_target_time_and_has_no_export(self):
        data=json.loads((ROOT/'fixtures/vinga-uddevalla-preflight.json').read_text())
        self.assertEqual(len(data['valid_times']),31)
        self.assertEqual(data['route_status'],'blocked_at_data_preflight')
        self.assertFalse(data['routing_performed']);self.assertFalse(data['gpx_available'])
        self.assertIsNone(data['travel_seconds']);self.assertIsNone(data['comfort_exposure'])
        self.assertGreater(data['straight_line_distance_m'],80000)
        for product in ('waves','current'):
            target=data['probes']['target'][product]['samples']
            self.assertEqual(len(target),31)
            self.assertTrue(all(x['value'] is None and x['missing_corners']==1 for x in target))
            self.assertTrue(all(x['value'] is not None for x in data['probes']['start'][product]['samples']))
        self.assertEqual(len(data['coastline_display']['features']),250)
        self.assertTrue(all(f['geometry']['type']=='LineString' for f in data['coastline_display']['features']))
        self.assertEqual(data['source_sha256']['met/wind.txt'],'608f78b24ae5b439d28d51b8f7b4e2756d341afcfbac214e32d2857d913c2bb6')
        self.assertEqual(data['source_sha256']['land/coastline.osm'],'ffabbf8c6fdf537b651b033190dde341b16d5694db1a29824a28cfe87f08c2e7')
    def test_current_gap_is_not_nearest_neighbour_or_zero_and_real_zero_is_valid(self):
        ds=xr.Dataset({'uo':(('time','latitude','longitude'),np.array([[[0.,2.],[4.,6.]]])),
                       'vo':(('time','latitude','longitude'),np.zeros((1,2,2)))},coords={'time':[0],'latitude':[57.,58.],'longitude':[11.,12.]})
        point={'longitude':11.5,'latitude':57.5}
        self.assertEqual(marine_probe(ds,None,'current',point)['samples'][0]['value'],[3.,0.])
        ds['uo'][0,0,1]=np.nan
        result=marine_probe(ds,None,'current',point)['samples'][0]
        self.assertIsNone(result['value']);self.assertEqual(result['missing_corners'],1)

if __name__=='__main__':unittest.main()
