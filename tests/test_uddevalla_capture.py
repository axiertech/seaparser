"""Acquisition must be reproducible, preserve failures and never imply routing."""
from datetime import datetime,timezone,timedelta
from io import BytesIO
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import fetch_uddevalla as f
from scripts.share_public_capture import bundle

class CorridorCaptureTests(unittest.TestCase):
    def test_time_window_and_detour_extent(self):
        p=f.plan(now=datetime(2026,10,18,7,15,tzinfo=timezone.utc))
        self.assertEqual(p['departure'],'2026-10-18T09:00:00+00:00')
        self.assertEqual((f.utc(p['end'])-f.utc(p['departure'])).total_seconds(),30*3600)
        for name in ('start','target'):
            self.assertTrue(p['bbox'][0]<p[name]['longitude']<p['bbox'][2]);self.assertTrue(p['bbox'][1]<p[name]['latitude']<p['bbox'][3])
        self.assertFalse(p['routing_enabled'])
    def test_hash_checked_cache_never_repeats_a_successful_request(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(f.MET_OPENER,'open',return_value=BytesIO(b'actual source bytes')) as opened:
            a=f.cached_fetch(tmp,'source.txt','https://thredds.met.no/frozen',limit=100)
            self.assertEqual(a,f.cached_fetch(tmp,'source.txt','https://thredds.met.no/frozen',limit=100));self.assertEqual(opened.call_count,1)
            Path(tmp,'source.txt').write_bytes(b'changed')
            with self.assertRaises(ValueError):f.cached_fetch(tmp,'source.txt','https://thredds.met.no/frozen',limit=100)
            self.assertEqual(opened.call_count,1)
    def test_bad_or_oversized_response_is_not_admitted(self):
        for raw,validator in ((b'error body',lambda body:(_ for _ in ()).throw(ValueError())),(b'x'*101,None)):
            with tempfile.TemporaryDirectory() as tmp,patch.object(f.MET_OPENER,'open',return_value=BytesIO(raw)):
                with self.assertRaises(ValueError):f.cached_fetch(tmp,'source','https://thredds.met.no/test',limit=100,validator=validator)
                self.assertFalse(Path(tmp,'source').exists());self.assertFalse(Path(tmp,'sources.json').exists())
    def test_one_source_failure_does_not_suppress_other_sources_or_claim_a_route(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'capture_met',side_effect=OSError()),patch.object(f,'capture_land',return_value={'captured':True}) as land:
            self.assertEqual(f.main(['--output',tmp,'--public-only']),1);self.assertEqual(land.call_count,1)
            report=json.loads(Path(tmp,'status.json').read_text());self.assertFalse(report['routing_enabled']);self.assertEqual(report['phases']['met']['status'],'blocked')
    def test_public_ci_bundle_cannot_include_credentials_or_marine_auth_data(self):
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'request.json').write_text('{}');(root/'met').mkdir();(root/'met/wind.txt').write_text('public nodes')
            (root/'marine').mkdir();(root/'marine/private.txt').write_text('private');(root/'app.env').write_text('secret')
            with tarfile.open(fileobj=BytesIO(bundle(root)),mode='r:gz') as archive:self.assertEqual(set(archive.getnames()),{'request.json','met/wind.txt'})
    def test_land_retry_never_downloads_wind_or_marine(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'capture_met') as met,patch.object(f,'capture_marine') as marine,patch.object(f,'capture_land',return_value={'captured':True}):
            self.assertEqual(f.main(['--output',tmp,'--land-only']),0)
            met.assert_not_called();marine.assert_not_called()
    def test_land_server_memory_and_response_budgets_are_independent(self):
        from urllib.parse import parse_qs
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'cached_fetch',return_value=b'<osm><node id="1"/><way><nd ref="1"/></way></osm>') as fetch:
            Path(tmp,'land').mkdir()
            f.capture_land(tmp,f.plan(),1000)
            self.assertEqual(fetch.call_args.kwargs['limit'],1000)
            self.assertIn('[maxsize:536870912]',parse_qs(fetch.call_args.kwargs['data'].decode())['data'][0])

    def test_extended_window_keeps_exact_hours_and_rejects_truncation(self):
        request=json.loads(Path('settings/trelleborg-stromstad-capture.json').read_text())
        self.assertEqual(len(f.requested_times(request)),50)
        self.assertEqual(f.requested_times(request)[-1],datetime(2026,10,21,10,tzinfo=timezone.utc))
        self.assertIs(f.validate_request(request),request)
        for end in ('2026-10-21T11:00:00Z','2026-10-19T08:00:00Z','2026-10-19T10:30:00Z'):
            with self.subTest(end=end),self.assertRaises(ValueError):f.requested_times({**request,'end':end})
        for key,value in (('bbox',[float('nan'),55.2,13.5,59.15]),('planning_area',[8,55.3,13.4,59.05]),('routing_enabled',True)):
            with self.subTest(key=key),self.assertRaises(ValueError):f.validate_request({**request,key:value})

    def test_long_wind_capture_chunks_partition_requested_times(self):
        request=json.loads(Path('settings/trelleborg-stromstad-capture.json').read_text())
        reference=f.utc(request['reference_time'])
        all_times=tuple(int((reference+timedelta(hours=i)).timestamp()) for i in range(59))
        def fetch(directory,name,url,**kwargs):
            Path(directory).mkdir(parents=True,exist_ok=True)
            return ('Dataset {\nforecast_reference_time, '+str(int(reference.timestamp()))+'\n').encode()
        def axis(text,name,count):return all_times if name=='time' else (0,1000)
        with tempfile.TemporaryDirectory() as tmp,patch.object(f,'cached_fetch',side_effect=fetch) as fetched, \
             patch.object(f,'axis',side_effect=axis),patch.object(f,'native_window',return_value=(0,1,0,1)), \
             patch.object(f,'field_metadata'),patch.object(f,'geometry_metadata'),patch.object(f,'time_metadata'):
            result=f.capture_met(tmp,request,64000000)
            self.assertEqual(len(result['wind_files']),9)
            self.assertEqual([t for chunk in result['wind_files'] for t in chunk['times']],result['times'])
            self.assertEqual(result['wind_files'][0]['filename'],'wind-09-14.txt')
            self.assertEqual(result['wind_files'][-1]['filename'],'wind-57-58.txt')
            self.assertEqual(len(result['wind_files'][-1]['times']),2)
            self.assertTrue(all(call.kwargs['limit']<=64000000 for call in fetched.call_args_list))
