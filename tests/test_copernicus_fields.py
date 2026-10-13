import unittest
from infrastructure.copernicus_fields import CURRENT_FIELDS, WAVE_FIELDS, current_node, validate_fields, wave_node


class CopernicusFieldTests(unittest.TestCase):
    def test_wave_from_bearing_and_tm02(self):
        height, period, east, north = wave_node(1.25, 6.5, 90, 1)
        self.assertEqual((height, period), (1.25, 6.5))
        self.assertAlmostEqual(east, 1)
        self.assertAlmostEqual(north, 0)
        self.assertEqual(wave_node(0, 2, 360, 1), (0, 2, 0, 1))

    def test_peak_period_is_not_tm02(self):
        attrs = {k: {'standard_name': v[0], 'units': v[1][0]} for k, v in WAVE_FIELDS.items()}
        validate_fields(attrs, WAVE_FIELDS)
        attrs['VTM02']['standard_name'] = 'sea_surface_wave_period_at_variance_spectral_density_maximum'
        with self.assertRaises(ValueError):
            validate_fields(attrs, WAVE_FIELDS)

    def test_land_ice_and_fill_values_remain_gaps(self):
        for wet in (0, None):
            self.assertIsNone(wave_node(1, 6, 90, wet))
        for node in ((None, 6, 90), (1, None, 90), (1, 6, None)):
            self.assertIsNone(wave_node(*node, 1))
        self.assertIsNone(current_node(None, 0.4))

    def test_invalid_values_rejected(self):
        for node in ((-1, 6, 90), (1, 0, 90), (1, 6, 361), (float('nan'), 6, 90)):
            with self.assertRaises(ValueError):
                wave_node(*node, 1)
        with self.assertRaises(ValueError):
            wave_node(1, 6, 90, 2)
        with self.assertRaises(ValueError):
            current_node(float('inf'), 0)

    def test_current_vectors_keep_sign_and_units(self):
        self.assertEqual(current_node(-0.3, 0.4), (-0.3, 0.4))
        attrs = {k: {'standard_name': v[0], 'units': 'm s-1'} for k, v in CURRENT_FIELDS.items()}
        validate_fields(attrs, CURRENT_FIELDS)
        attrs['uo']['units'] = 'knots'
        with self.assertRaises(ValueError):
            validate_fields(attrs, CURRENT_FIELDS)
