"""Known real voyage, lossless original reserve digest and explicit GPX status."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

from application.coastal_presentation import restore_estimates
from application.planning import canonical
from presentation.gpx import export_gpx,export_estimated_coastal_gpx

ROOT=Path(__file__).resolve().parents[1]


class CoastalPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.view=json.loads((ROOT/'fixtures/coastal-voyage.json').read_text())

    def test_every_original_source_position_time_value_and_connection_is_recoverable(self):
        restored=[];count=0
        for original in self.view['reserve_evidence']['segments']:
            segment=deepcopy(original)
            for sample in segment['samples']:
                sample['estimates']=restore_estimates(self.view,sample);count+=len(sample['estimates'])
                for key in ('longitude','latitude','estimate_refs'):sample.pop(key)
            restored.append(segment)
        self.assertEqual(count,8232)
        # Computed independently from the preserved full voyage before compaction.
        self.assertEqual(sha256(canonical(restored).encode()).hexdigest(),
                         'f6a577c38dd2a9ad27767dcbaba51baa49fdc487796b7a68c74100ffbb1b8d9e')
        self.assertTrue(all(m['issued_at'] is None for m in self.view['provenance']['source_metadata']))

    def test_known_simulated_voyage_is_not_relabelled_as_verified(self):
        route=self.view['routes'][0]
        self.assertEqual(route['segment_count'],592);self.assertEqual(len(route['path']),593)
        self.assertAlmostEqual(route['distance_m'],88955.89821967899)
        self.assertEqual(route['travel_seconds'],34452.631393)
        self.assertEqual(route['weather_segment_status'],'not_available')
        self.assertFalse(route['weather_limits_verified'])

    def test_estimated_gpx_is_self_contained_and_old_verified_gate_stays_closed(self):
        content=export_estimated_coastal_gpx(self.view,'water-0');root=ET.fromstring(content)
        ns={'g':'http://www.topografix.com/GPX/1/1','sp':'https://seaparser.com/ns/estimate/1'}
        self.assertEqual(root.findtext('g:metadata/g:extensions/sp:weather_limits_verified',namespaces=ns),'false')
        self.assertIn('HÖG OSÄKERHET',root.findtext('g:metadata/g:name',namespaces=ns))
        evidence=json.loads(root.findtext('g:metadata/g:extensions/sp:evidence_json',namespaces=ns))
        self.assertEqual(evidence['reserve_evidence'],self.view['reserve_evidence'])
        self.assertEqual(evidence['provenance'],self.view['provenance'])
        self.assertEqual(len(root.findall('g:rte/g:rtept',ns)),34)
        self.assertEqual(root.findall('g:trk',ns),[])
        with self.assertRaises(ValueError):export_gpx({'alternatives':[{'id':'water-0','status':'arrived',
            'weather_segment_status':'not_available','arrival_weather_status':'passed_at_arrival'}]},'water-0')
        for mutate in ('status','arrival','qualification'):
            bad=deepcopy(self.view)
            if mutate=='status':bad['routes'][0]['status']='data_unavailable'
            elif mutate=='arrival':bad['routes'][0]['arrival_weather_status']='failed'
            else:bad['result_qualification']='verified'
            with self.assertRaises(ValueError):export_estimated_coastal_gpx(bad,'water-0')
