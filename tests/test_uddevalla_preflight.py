"""Real regional endpoint gaps cannot turn into routes or fabricated metrics."""
import json
from pathlib import Path
import unittest
from hashlib import sha256
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
import xarray as xr
from scripts.build_uddevalla import marine_probe,wind_sample

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

    def test_changed_frozen_wind_bytes_fail_without_repeating_source_capture(self):
        with TemporaryDirectory() as name:
            directory=Path(name);index={}
            for filename in ('forecast.dds','forecast.das','times.txt','axes.txt','coordinates.txt','wind.txt'):
                content=b'frozen test bytes';(directory/filename).write_bytes(content)
                index[filename]={'bytes':len(content),'sha256':sha256(content).hexdigest()}
            (directory/'sources.json').write_text(json.dumps(index));(directory/'inventory.json').write_text('{}')
            (directory/'wind.txt').write_bytes(b'changed test bytes')
            with patch('scripts.fetch_uddevalla.capture_met',side_effect=AssertionError('No repeated capture')):
                with self.assertRaisesRegex(ValueError,'Frozen MET source bytes changed'):
                    wind_sample(directory,{})


class ChunkedWindReaderTests(unittest.TestCase):
    def test_native_chunks_preserve_values_and_reject_time_gap(self):
        from datetime import datetime,timedelta,timezone
        from decimal import Decimal
        from scripts import build_uddevalla as reader
        reference=datetime(2026,10,19,tzinfo=timezone.utc)
        times=[reference+timedelta(hours=i) for i in (9,10,11)]
        request={'reference_time':reference.isoformat(),'departure':times[0].isoformat(),'end':times[-1].isoformat()}
        chunks=[{'filename':'wind-09-10.txt','times':[t.isoformat() for t in times[:2]]},
                {'filename':'wind-11-11.txt','times':[times[2].isoformat()]}]
        with TemporaryDirectory() as tmp:
            root=Path(tmp);index={}
            files={name:'metadata' for name in ('forecast.dds','forecast.das','times.txt','axes.txt','coordinates.txt')}
            for chunk in chunks:
                content=chunk['filename']+'\n';nt=len(chunk['times'])
                for name in ('wind_speed_10m','wind_direction_10m'):
                    content+=f'{name}.{name}[{nt}][2][2]\n'
                    for t in range(nt):
                        content+=f'[{t}][0], 1.0000, 2\n[{t}][1], 3, 4\n'
                    content+='\n'
                files[chunk['filename']]=content
            for name,content in files.items():
                data=content.encode();(root/name).write_bytes(data)
                index[name]={'bytes':len(data),'sha256':sha256(data).hexdigest()}
            (root/'sources.json').write_text(json.dumps(index))
            inventory={'times':[t.isoformat() for t in times],'wind_files':chunks,
                       'native_subset':{'x_first':0,'x_last':1,'y_first':0,'y_last':1}}
            (root/'inventory.json').write_text(json.dumps(inventory))
            def axis(text,name,count):
                if name.endswith('.time'):
                    selected=times[:2] if text.startswith('wind-09') else times[2:]
                    return tuple(Decimal(int(t.timestamp())) for t in selected)
                return (Decimal(0),Decimal(1000))
            with patch.object(reader,'axis',side_effect=axis),patch.object(reader,'matrix',return_value=((0,0),(0,0))), \
                 patch.object(reader,'field_metadata'),patch.object(reader,'geometry_metadata'),patch.object(reader,'time_metadata'):
                sample=wind_sample(root,request)
                self.assertEqual(sample.times,tuple(times))
                self.assertEqual(len(sample.speed_m_s),3)
                self.assertEqual(str(sample.speed_m_s[2][0][0]),'1.0000')
                inventory['wind_files'][1]['times']=[times[1].isoformat()]
                (root/'inventory.json').write_text(json.dumps(inventory))
                with self.assertRaisesRegex(ValueError,'exactly partition'):wind_sample(root,request)

if __name__=='__main__':unittest.main()
