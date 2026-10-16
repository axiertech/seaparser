"""ASCII decimals versus diagnostic IEEE binary32 rounding; no source recovery."""
from fractions import Fraction
from pathlib import Path
from struct import pack, unpack
import unittest

from scripts.audit_met_metadata import axis, audit
from scripts.regional_forecast import load_regional_inputs

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/met-nordic-metadata'


def binary32(value):
    return Fraction.from_float(unpack('!f', pack('!f', float(value)))[0])


class METCoordinatePrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit(FIXTURE)
        text = (FIXTURE / 'native-axes.txt').read_text()
        cls.x, cls.y = axis(text, 'x', 1796), axis(text, 'y', 2321)

    def test_full_axis_rounding_differs_from_exact_ascii_grid(self):
        dds = (FIXTURE / 'met-forecast.dds').read_text()
        self.assertIn('Float32 x[x = 1796];', dds)
        self.assertIn('Float32 y[y = 2321];', dds)
        rounded = [binary32(value) for value in self.x]
        self.assertEqual(max(abs(Fraction(a) - b) for a, b in zip(self.x, rounded)), Fraction(1, 80))
        steps = [b - a for a, b in zip(rounded, rounded[1:])]
        self.assertEqual(min(steps), Fraction(63999, 64))
        self.assertEqual(max(steps), Fraction(64001, 64))
        self.assertTrue(all(b - a == 1000 for a, b in zip(self.x, self.x[1:])))
        self.assertTrue(all(Fraction(value) == binary32(value) for value in self.y))

    def test_wind_subset_retains_source_decimals_without_silent_rounding(self):
        wind = load_regional_inputs(FIXTURE.parent).wind
        self.assertEqual(wind.x_m, self.x[692:699])
        self.assertEqual(wind.y_m, self.y[509:517])
        self.assertEqual({binary32(x) - Fraction(x) for x in wind.x_m}, {Fraction(-1, 320)})
        self.assertTrue(all(binary32(y) == Fraction(y) for y in wind.y_m))
        self.assertEqual(dict(wind.source_hashes)['native-axes.txt'], self.report['source_hashes']['native-axes.txt'])
        self.assertIn('wind_native_geometry_unqualified', wind.planning_blockers)
