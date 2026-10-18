"""Acquisition must be reproducible, preserve failures and never imply routing."""
from datetime import datetime,timezone
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
