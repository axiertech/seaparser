"""Regression tests for real frozen MET wind on a Vinga-local route segment."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import unittest

from infrastructure.land import FORWARD, to_geo
from infrastructure.met_wind_segments import (
    NativeMetWind, VingaRouteSegment, _closed_cells, direction_from_to_components,
)
from prototype.model import Vector
from scripts.native_met_wind_segment import reproduce
from scripts.regional_forecast import load_native_wind

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'
START = datetime(2026, 10, 13, 12, 20, tzinfo=timezone.utc)
END = datetime(2026, 10, 13, 12, 30, tzinfo=timezone.utc)


class NativeMetWindSegmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = load_native_wind(FIXTURES)
        cls.wind = NativeMetWind(cls.sample)
        cls.segment = VingaRouteSegment(Vector(-100, 0), Vector(100, 0), START, END)

    def test_meteorological_from_bearings_convert_to_true_to_components(self):
        self.assertEqual(direction_from_to_components(10, 0), Vector(0, -10))
        east = direction_from_to_components(10, 90)
        self.assertAlmostEqual(east.east, -10, places=12)
        self.assertAlmostEqual(east.north, 0, places=12)

    def test_359_1_component_interpolation_does_not_flip_direction(self):
        west = direction_from_to_components(8, 359)
        east = direction_from_to_components(8, 1)
        average = Vector((west.east + east.east) / 2, (west.north + east.north) / 2)
        self.assertAlmostEqual(average.east, 0, places=12)
        self.assertLess(average.north, -7.99)

    def test_actual_frozen_sample_has_independent_hand_calculated_reference(self):
        vector = self.wind.at(11.605, 57.633, datetime(2026, 10, 13, 12, 30,
                                                     tzinfo=timezone.utc))
        self.assertAlmostEqual(vector.east, -4.6156826132, places=8)
        self.assertAlmostEqual(vector.north, 12.3390776063, places=8)
        self.assertAlmostEqual(vector.speed, 13.1741171302, places=8)

    def test_route_frame_vector_transform_is_identity_at_aeqd_origin(self):
        true = self.wind.at_vinga_local(Vector(0, 0), END)
        geographic = self.wind.at(11.605, 57.633, END)
        self.assertAlmostEqual(true.east, geographic.east, delta=1e-7)
        self.assertAlmostEqual(true.north, geographic.north, delta=1e-7)

    def test_source_lcc_transform_matches_independent_fixed_reference(self):
        x, y = self.wind._xy(11.605, 57.633)
        self.assertAlmostEqual(x, -202842.0310241585, delta=1e-6)
        self.assertAlmostEqual(y, -592265.6168214144, delta=1e-6)

    def test_off_origin_wind_vector_maps_to_route_frame_differential(self):
        from pyproj import Geod
        point = Vector(700, 400)
        lon, lat = to_geo(point)
        true = self.wind.at(lon, lat, END)
        mapped = self.wind.at_vinga_local(point, END)
        geod = Geod(ellps='WGS84')
        bearing = true.course
        lon2, lat2, _ = geod.fwd(lon, lat, bearing, true.speed * .1)
        x2, y2 = FORWARD.transform(lon2, lat2, errcheck=True)
        reference = Vector((x2 - point.east) / .1, (y2 - point.north) / .1)
        self.assertAlmostEqual(mapped.east, reference.east, delta=2e-5)
        self.assertAlmostEqual(mapped.north, reference.north, delta=2e-5)

    def test_out_of_spatial_and_time_support_are_rejected_without_extrapolation(self):
        for args in ((11.605, 57.633, datetime(2026, 10, 13, 11, 59, tzinfo=timezone.utc)),
                     (11.7, 57.633, END)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.wind.at(*args)

    def test_missing_corner_is_not_filled(self):
        planes = [[list(row) for row in plane] for plane in self.sample.speed_m_s]
        planes[0][3][2] = None
        broken = replace(self.sample, speed_m_s=tuple(tuple(tuple(row) for row in plane)
                                                       for plane in planes))
        with self.assertRaisesRegex(ValueError, 'Missing native interpolation node'):
            NativeMetWind(broken).at(11.605, 57.633, START)

    def test_full_segment_corner_envelope_certifies_within_model_only(self):
        report = self.wind.bound_segment(self.segment, max_wind_m_s=18)
        self.assertEqual(report['status'], 'within_interpolation_model')
        self.assertLessEqual(Decimal(report['upper_bound_m_s']), Decimal('18'))
        self.assertEqual(report['provider_mask'], 'unknown')
        self.assertEqual(report['overall_planning_qualification'], 'blocked')
        self.assertGreater(report['intersecting_cells'], 0)

    def test_limit_equality_and_closed_cell_boundary(self):
        report = self.wind.bound_segment(self.segment, max_wind_m_s=13.442178)
        self.assertEqual(report['status'], 'within_interpolation_model')
        self.assertEqual(_closed_cells((Decimal(0), Decimal(1), Decimal(2)),
                                       Decimal(1), Decimal(1)), (0, 1))

    def test_real_frozen_wind_proves_test_cap_exceeded_on_segment(self):
        report = self.wind.bound_segment(self.segment, max_wind_m_s=10)
        self.assertEqual(report['status'], 'observed_exceedance')
        self.assertGreater(Decimal(report['upper_bound_m_s']), Decimal('10'))

    def test_high_off_path_corner_makes_bound_insufficient_not_pass(self):
        speeds = [[list(row) for row in plane] for plane in self.sample.speed_m_s]
        # The broad segment enclosure includes this cell corner; direct path
        # observations remain below 18 m/s, so this can only make the bound unsure.
        speeds[0][2][2] = Decimal('19')
        changed = replace(self.sample, speed_m_s=tuple(tuple(tuple(row) for row in plane)
                                                         for plane in speeds))
        report = NativeMetWind(changed).bound_segment(self.segment, max_wind_m_s=18)
        self.assertEqual(report['status'], 'insufficient_evidence')

    def test_coordinate_box_covers_independent_route_points(self):
        from pyproj import CRS, Transformer
        from infrastructure.native_wind import NATIVE_PROJECTION
        report = self.wind.bound_segment(self.segment, max_wind_m_s=18)
        box = report['source_grid_enclosure_m']
        crs = CRS.from_proj4(NATIVE_PROJECTION)
        forward = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
        for f in (0, .125, .5, .875, 1):
            point = Vector(-100 + 200 * f, 0)
            lon, lat = to_geo(point)
            x, y = forward.transform(lon, lat, errcheck=True)
            self.assertLessEqual(Decimal(box['x'][0]), Decimal(str(x)))
            self.assertGreaterEqual(Decimal(box['x'][1]), Decimal(str(x)))
            self.assertLessEqual(Decimal(box['y'][0]), Decimal(str(y)))
            self.assertGreaterEqual(Decimal(box['y'][1]), Decimal(str(y)))

    def test_reproducible_case_keeps_missing_issue_time_and_marine_gates(self):
        result = reproduce(FIXTURES)
        self.assertEqual(result['status'], 'diagnostic_only')
        self.assertIsNone(result['issued_at'])
        self.assertEqual(result['marine_run_compatibility'], 'unverified')
        self.assertEqual(result['hard_wind_checks']['10']['status'], 'observed_exceedance')
        self.assertEqual(result['hard_wind_checks']['18']['status'], 'within_interpolation_model')
        self.assertEqual(result['synthetic_components']['current'], 'not used')


if __name__ == '__main__':
    unittest.main()
