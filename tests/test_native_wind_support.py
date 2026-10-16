"""Frozen source identities, whole space/time inventories, and fail-closed gates."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

from application.native_wind_support import SOURCE_FRAME, SourceSphereSegment, closed_cell_indices, inspect_native_segment
from scripts.native_wind_segment import inspect_file
from scripts.regional_forecast import load_native_wind

ROOT=Path(__file__).resolve().parents[1]
D=Decimal


def segment(**changes):
    return replace(SourceSphereSegment(D('57.63'),D('11.60'),D('57.64'),D('11.61'),
        datetime(2026,10,13,12,20,tzinfo=timezone.utc),
        datetime(2026,10,13,14,40,tzinfo=timezone.utc),SOURCE_FRAME),**changes)


class NativeWindSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wind=load_native_wind(ROOT/'fixtures')

    def test_known_six_boxes_and_all_24_raw_nodes(self):
        r=inspect_native_segment(self.wind,segment())
        self.assertTrue(r['raw_inventory_complete'])
        self.assertEqual(r['adjacent_node_boxes'],[[k,j,2] for k in (0,1,2) for j in (2,3)])
        self.assertEqual(len(r['raw_nodes']),24)
        self.assertEqual({tuple(n['index']) for n in r['raw_nodes']},
                         {(k,j,i) for k in range(4) for j in (2,3,4) for i in (2,3)})
        for node in r['raw_nodes']:
            k,j,i=node['index']
            self.assertEqual(node['speed_m_s'],str(self.wind.speed_m_s[k][j][i]))
            self.assertEqual(node['direction_from_degrees'],str(self.wind.direction_from_degrees[k][j][i]))
            self.assertEqual(node['land_fraction'],str(self.wind.land_fraction[j][i]))
        self.assertEqual(r['source_hashes'],dict(self.wind.source_hashes))
        self.assertEqual(r['routing_status'],'data_unavailable')
        self.assertIsNone(r['fastest_candidate'])
        self.assertIsNone(r['comfortable_candidate'])
        self.assertIsNone(r['provider_wind_validity_mask'])
        self.assertIsNone(r['wind_safety_envelope'])
        self.assertIsNone(r['source_to_wgs84_datum_error_m'])
        self.assertIsNone(r['source_coordinate_serialization_error_m'])
        self.assertFalse(r['local_route_geometry_binding_verified'])
        self.assertFalse(r['provider_interpolation_stencil_verified'])
        self.assertFalse(r['land_fraction_is_validity_mask'])
        self.assertTrue(set(self.wind.planning_blockers)<=set(r['planning_blockers']))
        self.assertEqual(r,inspect_native_segment(self.wind,segment()))

    def test_closed_spatial_and_temporal_boundaries_include_both_neighbors(self):
        self.assertEqual(closed_cell_indices((0,1,2,3),1,1),(0,1))
        self.assertEqual(closed_cell_indices((0,1,2,3),Fraction(1,2),Fraction(5,2)),(0,1,2))
        t=self.wind.times
        self.assertEqual(closed_cell_indices(t,t[1],t[2]),(0,1,2))
        r=inspect_native_segment(self.wind,segment(start_time=t[1],end_time=t[2]))
        self.assertEqual({c[0] for c in r['adjacent_node_boxes']},{0,1,2})
        self.assertEqual({n['valid_at'] for n in r['raw_nodes']},{v.isoformat() for v in t[:4]})

    def test_outside_space_or_time_returns_no_clipped_support(self):
        for change,reason in [({'end_longitude':D('11.8')},'projected_box_outside_serialized_native_grid'),
                              ({'end_time':self.wind.times[-1]+timedelta(seconds=1)},'segment_outside_nominal_time_support'),
                              ({'start_time':self.wind.times[0]-timedelta(seconds=1)},'segment_outside_nominal_time_support')]:
            r=inspect_native_segment(self.wind,segment(**change))
            self.assertFalse(r['raw_inventory_complete'])
            self.assertIn(reason,r['inventory_failures'])
            self.assertEqual(r['adjacent_node_boxes'],[])
            self.assertEqual(r['raw_nodes'],[])

    def test_last_nominal_time_can_bound_segment_but_not_qualify_arrival(self):
        r=inspect_native_segment(self.wind,segment(end_time=self.wind.times[-1]))
        self.assertTrue(r['nominal_time_box_inside'])
        self.assertTrue(r['raw_inventory_complete'])
        self.assertFalse(r['arrival_before_last_sample'])
        self.assertIsNone(r['mean_window_placement'])
        self.assertEqual(r['routing_status'],'data_unavailable')

    def test_budget_exhaustion_never_returns_truncated_success(self):
        r=inspect_native_segment(self.wind,segment(),max_cells=5)
        self.assertEqual(r['intersecting_box_count'],6)
        self.assertEqual(r['adjacent_node_boxes'],[])
        self.assertEqual(r['raw_nodes'],[])
        self.assertFalse(r['raw_inventory_complete'])
        self.assertEqual(r['inventory_failures'],['source_cell_budget_exceeded'])

    def test_missing_off_path_support_corner_is_preserved_not_skipped(self):
        speed=[[[v for v in row] for row in plane] for plane in self.wind.speed_m_s]
        speed[0][2][2]=None
        changed=replace(self.wind,speed_m_s=tuple(tuple(tuple(row) for row in plane) for plane in speed))
        r=inspect_native_segment(changed,segment())
        self.assertFalse(r['raw_inventory_complete'])
        self.assertIn('missing_or_nonfinite_raw_node',r['inventory_failures'])
        node=next(n for n in r['raw_nodes'] if n['index']==[0,2,2])
        self.assertIsNone(node['speed_m_s'])
        self.assertEqual(node['direction_from_degrees'],str(self.wind.direction_from_degrees[0][2][2]))
        self.assertEqual(len(r['raw_nodes']),24)

    def test_source_values_hashes_path_and_budget_are_bound_to_report_identity(self):
        baseline=inspect_native_segment(self.wind,segment())
        changed_hash=replace(self.wind,source_hashes=self.wind.source_hashes+(('extra-source','0'*64),))
        changed_value=replace(self.wind,model_reference_time=self.wind.model_reference_time+timedelta(seconds=1))
        for wind in (changed_hash,changed_value):
            actual=inspect_native_segment(wind,segment())
            self.assertNotEqual(actual['source_input_sha256'],baseline['source_input_sha256'])
            self.assertNotEqual(actual['report_sha256'],baseline['report_sha256'])
        for actual in (inspect_native_segment(self.wind,segment(end_longitude=D('11.611'))),
                       inspect_native_segment(self.wind,segment(),max_cells=6)):
            self.assertNotEqual(actual['report_sha256'],baseline['report_sha256'])

    def test_wgs84_local_unknown_frame_and_invalid_time_are_rejected(self):
        for changes in ({'coordinate_frame':'EPSG:4326'},{'coordinate_frame':'local-aeqd'},
                        {'start_time':self.wind.times[-1]}, {'start_time':datetime(2026,10,13,12)},
                        {'start_latitude':True},{'start_latitude':57.63}):
            with self.assertRaises((ValueError,TypeError)):
                inspect_native_segment(self.wind,segment(**changes))
        for budget in (0,True,513):
            with self.assertRaises(ValueError):
                inspect_native_segment(self.wind,segment(),max_cells=budget)

    def test_cli_input_uses_exact_decimals_and_rejects_ambiguous_keys(self):
        report=inspect_file(ROOT/'fixtures',ROOT/'fixtures/met-source-sphere-segment.json')
        self.assertEqual(report,inspect_native_segment(self.wind,segment()))
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'segment.json'
            raw=(ROOT/'fixtures/met-source-sphere-segment.json').read_text()
            path.write_text(raw.replace('"start_latitude": 57.630,','"start_latitude": 57.630, "start_latitude": 57.640,'))
            with self.assertRaisesRegex(ValueError,'Duplicate segment key'):
                inspect_file(ROOT/'fixtures',path)
            path.write_text(' '*8193)
            with self.assertRaisesRegex(ValueError,'exceeds budget'):
                inspect_file(ROOT/'fixtures',path)
