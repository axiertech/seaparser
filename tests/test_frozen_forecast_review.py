"""Known frozen source values, publication separation, and review security."""
from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from presentation.frozen_forecast_html import render_frozen_forecast
from scripts.export_frozen_forecast import build_review
from scripts.freeze_copernicus_reference import freeze_with_audit

ROOT = Path(__file__).resolve().parents[1]


class FrozenForecastReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = build_review(ROOT / 'fixtures')

    def test_known_source_values_and_native_grids_remain_separate(self):
        wind, wave, current = self.review['products']
        self.assertEqual(wind['fields']['speed']['values'][0][0][0], 12.970281)
        self.assertEqual(wind['fields']['speed']['values'][-1][-1][-1], 15.915022)
        self.assertEqual(wind['x'], [-205442.2 + 1000*i for i in range(7)])
        self.assertEqual(len(wind['y']), 8)
        self.assertEqual(wind['times'][0], '2026-10-13T12:00:00+00:00')
        self.assertEqual(wind['times'][-1], '2026-10-13T16:00:00+00:00')
        self.assertEqual(wave['fields']['VHM0']['values'][0][0][0], 1.2349779605865479)
        self.assertEqual(current['fields']['uo']['values'][0][0][0], -0.2828807234764099)
        self.assertEqual(current['fields']['vo']['values'][-1][-1][-1], 0.20651660859584808)
        self.assertNotEqual(wave['x'], current['x'])
        self.assertNotEqual(wave['y'], current['y'])
        self.assertEqual(wave['mask'], [[1, 1], [1, 1]])
        self.assertIsNone(current['mask'])
        self.assertIsNone(wind['mask'])
        self.assertEqual(len(wind['land_fraction']), 8)
        self.assertEqual(len(wind['latitude']), 8)
        for p in self.review['products']:
            self.assertIsNone(p['issued_at'])
            self.assertIsNone(p['run_identity'])
            for f in p['fields'].values():
                self.assertEqual(len(f['values']), len(p['times']))
                self.assertTrue(all(len(plane) == len(p['y']) for plane in f['values']))
                self.assertTrue(all(len(row) == len(p['x']) for plane in f['values'] for row in plane))
        self.assertIsNone(wave['model_reference_time'])
        self.assertIsNone(current['model_reference_time'])
        self.assertIsNone(self.review['run_compatibility'])
        self.assertFalse(self.review['routing_qualified'])

    def test_every_displayed_source_hash_matches_frozen_bytes(self):
        for p in self.review['products']:
            for name, expected in p['source_hashes'].items():
                directory = ('met-nordic-wind-sample' if name == 'native-wind-land.txt' else
                             'met-nordic-metadata' if p['id'] == 'wind' else 'vinga-copernicus')
                self.assertEqual(sha256((ROOT/'fixtures'/directory/name).read_bytes()).hexdigest(), expected)

    def test_changed_source_fails_before_rendering(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixtures = Path(temporary)
            for directory in ('met-nordic-metadata', 'met-nordic-wind-sample', 'vinga-copernicus'):
                shutil.copytree(ROOT/'fixtures'/directory, fixtures/directory)
            path = fixtures/'vinga-copernicus/current.nc'
            path.write_bytes(path.read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                build_review(fixtures)

    def test_standalone_document_has_hash_csp_and_escaped_json(self):
        review = dict(self.review, note='</script><script>bad()</script>$SCRIPT')
        page = render_frozen_forecast(review)
        self.assertNotIn('<script>bad()', page)
        self.assertIn('\\u003c/script\\u003e', page)
        self.assertIn('$SCRIPT', page)  # Data is never treated as a template.
        for source in re.findall(r'<(?:style|script)(?: [^>]*)?>(.*?)</(?:style|script)>', page, re.S):
            self.assertIn('sha256-' + b64encode(sha256(source.encode()).digest()).decode(), page)
        parsed = json.loads(re.search(r'<script id="review-data" type="application/json">(.*?)</script>',page,re.S)[1])
        self.assertEqual(parsed, review)
        self.assertNotRegex(page, r'<(?:script|link|img|iframe)\b[^>]*(?:src|href)=')
        self.assertIn("default-src 'none'", page)
        self.assertIn('Frysta historiska prov', page)
        self.assertEqual(render_frozen_forecast(self.review), render_frozen_forecast(self.review))

    def test_refuses_claim_of_routing_qualification(self):
        with self.assertRaises(ValueError):
            render_frozen_forecast(dict(self.review, routing_qualified=True))

    def test_marine_time_mean_claims_preserve_the_actual_source_difference(self):
        _,wave,current=self.review['products']
        self.assertEqual(wave['source_time_means'],{'VHM0':'time: mean','VTM02':'time: mean','VMDR':'time: mean'})
        self.assertEqual(current['source_time_means'],{'uo':None,'vo':None})
        self.assertIn('Källan beskriver inte tidsmedlet',current['semantics'])
        self.assertNotIn('Källan anger tidsmedel',current['semantics'])

    def test_graphical_segment_is_bound_to_same_wind_snapshot_and_raw_values(self):
        wind=self.review['products'][0]
        report=self.review['segment_review']
        self.assertEqual(report['source_hashes'],wind['source_hashes'])
        self.assertEqual(report['intersecting_box_count'],12)
        self.assertEqual(len(report['raw_nodes']),36)
        self.assertFalse(report['physical_source_support_qualified'])
        for node in report['raw_nodes']:
            k,j,i=node['index']
            self.assertEqual(float(node['speed_m_s']),wind['fields']['speed']['values'][k][j][i])
            self.assertEqual(float(node['direction_from_degrees']),wind['fields']['direction']['values'][k][j][i])

    def test_segment_materialization_does_not_reopen_already_captured_wind_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixtures=Path(temporary)
            for name in ('met-nordic-metadata','met-nordic-wind-sample','vinga-copernicus'):
                shutil.copytree(ROOT/'fixtures'/name,fixtures/name)
            def remove_then_freeze(directory):
                for name in ('met-nordic-metadata','met-nordic-wind-sample'):
                    shutil.rmtree(fixtures/name)
                return freeze_with_audit(directory)
            with patch('scripts.export_frozen_forecast.freeze_with_audit',side_effect=remove_then_freeze):
                actual=build_review(fixtures)
            self.assertEqual(actual['segment_review'],self.review['segment_review'])
            self.assertEqual(actual['products'][0],self.review['products'][0])

    def test_checked_artifact_is_reproducible_from_current_sources(self):
        path = ROOT / 'artifacts/vinga-frozen-review/index.html'
        page = render_frozen_forecast(self.review)
        self.assertEqual(path.read_text(), page)
        receipt = json.loads(path.with_suffix('.receipt.json').read_text())
        self.assertEqual(receipt['sha256'], sha256(page.encode()).hexdigest())
        self.assertFalse(receipt['published'])
