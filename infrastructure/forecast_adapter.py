"""Pure adapter boundary: caller fetches first, normalize once, then plan offline."""
from math import cos, isfinite, radians, sin
from typing import Mapping, Protocol

from prototype.forecast_data import ForecastDataset, GridProduct
from prototype.forecast_metadata import Coverage, ProductMetadata
from prototype.model import KNOT, velocity


class ForecastAdapter(Protocol):
    """Provider-independent contract; no transport, clocks or lazy callbacks.

    Return a fully materialized immutable normalized ForecastDataset or reject
    malformed/unsupported payloads with ValueError. Missing nodes use None and
    invalid cells remain explicit. Fetching is a separate caller responsibility.
    """
    def normalize(self, payload: Mapping[str, object]) -> ForecastDataset: ...


class SyntheticFixtureAdapter:
    """Estimated test data only. Input vectors are [speed, compass bearing].

    Wind bearing is FROM, current bearing is TO, true north clockwise;
    velocities relative to ground in kn or m/s. Waves: [Hs(m), Tm02(s), FROM(deg)].
    Coordinates: east/north metres anchored at explicit WGS84 origin.
    """
    def normalize(self, payload):
        try:
            products = tuple(self._product(raw) for raw in payload['products'])
            return ForecastDataset(payload['dataset_id'], payload['version'], products)
        except (KeyError, TypeError, IndexError) as error:
            raise ValueError('Ofullständig eller felaktig syntetisk prognosfixture') from error

    def _product(self, raw):
        name = raw['product']
        if raw.get('issued_at') is None:
            raise ValueError('Syntetiska regressionsdata kräver explicit utfärdandetid')
        if name not in ('wind', 'current', 'waves'):
            raise ValueError('Okänd produkt')
        expected_reference = 'ground-from-true-north-tm02' if name == 'waves' else (
            'ground-from-true-north' if name == 'wind' else 'ground-to-true-north')
        if raw['reference_frame'] != expected_reference:
            raise ValueError('Okänd eller ej stödd extern referensram')
        if name == 'waves':
            if tuple(raw['units']) != ('m', 's', 'deg'):
                raise ValueError('Fixturevågor kräver m, s och deg')
            units, frame = ('m', 's', '1', '1'), 'ground-from-true-east-north-tm02'
        else:
            if tuple(raw['units']) not in (('m/s', 'deg'), ('kn', 'deg')):
                raise ValueError('Fixturevektorer kräver m/s eller kn och deg')
            units, frame = ('m/s', 'm/s'), 'ground-to-true-east-north'
        coverage = Coverage(**raw['coverage'])
        metadata = ProductMetadata(name, raw['dataset_id'], raw['version'], raw['source'],
                                   raw['issued_at'], raw['valid_from'], raw['valid_until'],
                                   coverage, units, frame)
        values = tuple(tuple(tuple(self._node(name, raw['units'], node) for node in row)
                             for row in plane) for plane in raw['values'])
        return GridProduct(metadata, raw['east_m'], raw['north_m'], raw['times'], values,
                           raw.get('invalid_cells', ()))

    @staticmethod
    def _node(name, units, node):
        if node is None:
            return None
        count = 3 if name == 'waves' else 2
        if len(node) != count or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                   or not isfinite(v) for v in node):
            raise ValueError('Ogiltig fixturenod; dataluckor måste markeras med None')
        if name == 'waves':
            height, period, bearing = node
            return (height, period, sin(radians(bearing % 360)), cos(radians(bearing % 360)))
        speed, bearing = node
        if speed < 0:
            raise ValueError('Negativ fart i fixture')
        speed *= KNOT if units[0] == 'kn' else 1
        vector = velocity(-speed if name == 'wind' else speed, bearing % 360)
        return vector.east, vector.north
