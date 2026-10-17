"""Whole-cell component envelopes; approval uses exact inequalities, not samples."""
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction

from .model import Vector
from .weather import WeatherLimitExceeded

METHOD = 'segment-aabb-component-box-exact-squared-v1'
MAX_WEATHER_CELLS = 4096
SCOPE = ('Konservativa cellgränser för markrelativ vindstyrka och Hs över hela accepterade '
         'integrerade segment; faktisk ankomst kontrolleras separat. Komfort/övriga vädervärden endast vid uppslag.')


@dataclass(frozen=True)
class CellWeatherBound:
    product: str
    cell: tuple[int, int, int]
    limit: float
    status: str
    wind_abs_components_m_s: tuple[float, float] | None = None
    wind_squared_upper: str | None = None
    wave_height_upper_m: float | None = None
    reason: str = ''


@dataclass(frozen=True)
class WeatherWitness:
    product: str
    position: Vector
    time: datetime
    limit: float
    wind_components_m_s: tuple[float, float] | None = None
    wave_height_m: float | None = None


@dataclass(frozen=True)
class WeatherSegmentCheck:
    status: str  # verified, exceeded, unverified
    reason: str = ''
    method: str = METHOD
    bounds: tuple[CellWeatherBound, ...] = ()
    witness: WeatherWitness | None = None
    failure_kind: str | None = None


class SegmentWeatherExceeded(WeatherLimitExceeded):
    def __init__(self, check):
        self.check = check
        super().__init__(check.reason)


class SegmentWeatherUnverified(ValueError):
    def __init__(self, check):
        self.check = check
        super().__init__(check.reason)


def squared_norm(components):
    return sum((Fraction(v)**2 for v in components), Fraction(0))


def certify_weather_segment(dataset, start, start_time, end, end_time, policy, *, weather_products=('wind', 'waves')):
    """Box proof: clamped component lerps stay in the corner component ranges.

    |W|² <= max|u_corner|²+max|v_corner|²; Hs <= max Hs_corner.
    Fraction compares the exact stored binary numbers, with no rounding epsilon.
    Failed bounds are NOT observations. Points may prove exceedance, never safety.
    """
    try:
        dataset.validate_segment(start, start_time, end, end_time, required_products=('current', *weather_products))
        products = {p.metadata.product: p for p in dataset.products}
        bounds, witness = [], None
        for name in weather_products:
            product = products[name]
            limit = policy.max_wind_m_s if name == 'wind' else policy.max_wave_height_m
            # Entire axis-aligned space/time box encloses the affine segment.
            # Cell selection uses only ordered comparisons, never sampled fractions.
            ranges = []
            for axis, low, high in ((product.east_m, min(start.east, end.east), max(start.east, end.east)),
                                   (product.north_m, min(start.north, end.north), max(start.north, end.north)),
                                   (product.times, min(start_time, end_time), max(start_time, end_time))):
                ranges.append(tuple(i for i in range(len(axis)-1) if axis[i] <= high and axis[i+1] >= low))
            east, north, times = ranges
            if len(east)*len(north)*len(times) > MAX_WEATHER_CELLS:
                return WeatherSegmentCheck('unverified', 'Certifieringsboxens cellgräns nådd',
                                           failure_kind='bounds_inconclusive')
            for k in times:
                for j in north:
                    for i in east:
                        cell = (k, j, i)
                        nodes = tuple(product.values[k+dt][j+dn][i+de]
                                      for dt in (0, 1) for dn in (0, 1) for de in (0, 1))
                        if cell in product.invalid_cells or any(node is None for node in nodes):
                            bounds.append(CellWeatherBound(name, cell, limit, 'unverified',
                                                           reason='Okänt/maskerat stöd i konservativ certifieringsbox'))
                        elif name == 'wind':
                            components = tuple(max(abs(node[c]) for node in nodes) for c in (0, 1))
                            upper = squared_norm(components)
                            passed = upper <= Fraction(limit)**2
                            bounds.append(CellWeatherBound(name, cell, limit, 'verified' if passed else 'unverified',
                                                           components, str(upper)))
                        else:
                            upper = max(node[0] for node in nodes)
                            bounds.append(CellWeatherBound(name, cell, limit, 'verified' if upper <= limit else 'unverified',
                                                           wave_height_upper_m=upper))
            for position, time in product.segment_points(start, start_time, end, end_time):
                # Expired endpoints can bound movement, but are not valid observations.
                if time >= product.metadata.valid_until:
                    continue
                value = product.interpolate(position, time)
                exceeded = squared_norm(value) > Fraction(limit)**2 if name == 'wind' else value[0] > limit
                if exceeded and witness is None:
                    witness = WeatherWitness(name, position, time, limit,
                                             tuple(value) if name == 'wind' else None,
                                             value[0] if name == 'waves' else None)
        if witness is not None:
            return WeatherSegmentCheck('exceeded', f'{witness.product}: hård vädergräns konstaterat överskriden längs segmentet',
                                       bounds=tuple(bounds), witness=witness)
        if any(bound.status != 'verified' for bound in bounds):
            return WeatherSegmentCheck('unverified', 'Konservativ cellgräns kan inte verifiera segmentets hårda vädergränser; ingen konstaterad överträdelse',
                                       bounds=tuple(bounds), failure_kind='bounds_inconclusive')
        return WeatherSegmentCheck('verified', bounds=tuple(bounds))
    except ValueError as error:
        return WeatherSegmentCheck('unverified', str(error), failure_kind='data_unavailable')
