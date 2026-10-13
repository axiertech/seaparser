"""A target-field certificate does not certify omitted source support."""
from dataclasses import replace
from datetime import timedelta
from fractions import Fraction
import json
from pathlib import Path
import unittest

from prototype.forecast_data import DataUnavailable
from prototype.model import Vector
from prototype.weather import WeatherPolicy
from test_forecast_data import ADAPTER, fixture, START


REFERENCE = json.loads((Path(__file__).resolve().parents[2] /
                        'fixtures/regridding-counterexamples.json').read_text())


def wind_dataset(knots, *, invalid_cells=()):
    """Synthetic normalized components, constant in north and time."""
    base = ADAPTER.normalize(fixture())
    wind = base.products[0]
    coverage = replace(wind.metadata.coverage, min_east_m=0, max_east_m=1)
    wind = replace(wind, metadata=replace(wind.metadata, coverage=coverage),
                   east_m=tuple(float(x) for x, _ in knots),
                   values=[[[[float(u), 0] for _, u in knots] for _ in range(2)] for _ in range(2)],
                   invalid_cells=invalid_cells)
    return replace(base, products=(wind, *base.products[1:]))


def certificate(dataset):
    return dataset.certify_weather_segment(Vector(0, 0), START, Vector(1, 0),
                                            START + timedelta(seconds=100), WeatherPolicy(10, 1))


class RegriddingCounterexampleTests(unittest.TestCase):
    def test_endpoint_resampling_loses_known_source_peak(self):
        example = REFERENCE['wind']
        knots = tuple((Fraction(x), Fraction(u)) for x, u in example['native_knots'])
        source = wind_dataset(knots)
        target = wind_dataset(tuple(zip(map(Fraction, example['target_endpoints']),
                                        map(Fraction, example['target_endpoint_values']))))
        # Independent piecewise-linear reference: midpoint is the native knot 20.
        self.assertEqual(knots[1], (Fraction(1, 2), Fraction(20)))
        self.assertEqual(knots[1][1] ** 2, Fraction(example['native_peak_squared']))
        for x in (0, 1):
            self.assertEqual(source.products[0].interpolate(Vector(x, 0), START), (0, 0))
        self.assertEqual(source.products[0].interpolate(Vector(.5, 0), START), (20, 0))
        self.assertEqual(target.products[0].interpolate(Vector(.5, 0), START), (0, 0))
        target_check = certificate(target)
        self.assertEqual(target_check.status, 'verified')
        self.assertTrue(all(Fraction(b.wind_squared_upper) == Fraction(example['target_upper_squared'])
                            for b in target_check.bounds if b.product == 'wind'))
        source_check = certificate(source)
        self.assertEqual(source_check.status, 'exceeded')
        self.assertEqual(source_check.witness.wind_components_m_s, (20, 0))

    def test_endpoint_resampling_loses_closed_interior_mask(self):
        example = REFERENCE['mask']
        low, high = map(Fraction, example['invalid_closed_interval'])
        witness = Fraction(example['invalid_interior_witness'])
        self.assertLess(low, witness)
        self.assertLess(witness, high)
        source = wind_dataset(((0, 0), (low, 0), (high, 0), (1, 0)), invalid_cells=((0, 0, 1),))
        target = wind_dataset(((0, 0), (1, 0)))
        for x in map(Fraction, example['valid_target_endpoints']):
            self.assertEqual(source.products[0].interpolate(Vector(float(x), 0), START), (0, 0))
        # GridProduct predicates refer to the stored binary coordinates, including edges.
        for x in (low, witness, high):
            with self.subTest(x=x), self.assertRaises(DataUnavailable):
                source.products[0].interpolate(Vector(float(x), 0), START)
        self.assertEqual(certificate(target).status, 'verified')
        source_check = certificate(source)
        self.assertEqual(source_check.status, 'unverified')
        self.assertEqual(source_check.failure_kind, 'data_unavailable')
        self.assertIsNone(source_check.witness)
        self.assertEqual(REFERENCE['routing_status'], 'data_unavailable')
