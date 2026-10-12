"""Frozen normalized grid snapshot; deterministic interpolation, no I/O."""
from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, hypot, isfinite

from .environment import Conditions, WaveData
from .forecast import utc_time
from .forecast_metadata import ProductMetadata
from .model import Vector


class DataUnavailable(ValueError):
    """No extrapolation or interpolation through invalid support."""


def axis_cell(axis, value):
    if not axis[0] <= value <= axis[-1]:
        raise DataUnavailable('Utanför rutnätets täckning; extrapolation avvisad')
    for index in range(len(axis) - 1):
        if value < axis[index + 1] or index == len(axis) - 2:
            span = axis[index + 1] - axis[index]
            fraction = ((value - axis[index]).total_seconds() / span.total_seconds()
                        if isinstance(value, datetime) else (value - axis[index]) / span)
            if not isfinite(fraction):
                raise DataUnavailable('Ogiltigt interpolationsintervall')
            return index, fraction
    raise DataUnavailable('Okänd täckning')


@dataclass(frozen=True)
class GridProduct:
    metadata: ProductMetadata
    east_m: tuple[float, ...]
    north_m: tuple[float, ...]
    times: tuple[datetime, ...]
    values: tuple  # [time][north][east][component], or None for a missing node
    invalid_cells: tuple[tuple[int, int, int], ...] = ()  # time, north, east cell

    def __post_init__(self):
        if type(self.metadata) is not ProductMetadata:
            raise ValueError('Explicit produktmetadata krävs')
        for name in ('east_m', 'north_m'):
            axis = tuple(getattr(self, name))
            if (len(axis) < 2 or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                   or not isfinite(v) for v in axis)
                    or any(a >= b for a, b in zip(axis, axis[1:]))):
                raise ValueError('Minst två strikt stigande finita koordinater krävs')
            object.__setattr__(self, name, axis)
        times = tuple(utc_time(t, 'Rutnätstid') for t in self.times)
        if len(times) < 2 or any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError('Minst två strikt stigande UTC-tider krävs')
        object.__setattr__(self, 'times', times)
        m = self.metadata
        c = m.coverage
        if ((self.east_m[0], self.north_m[0], self.east_m[-1], self.north_m[-1])
                != (c.min_east_m, c.min_north_m, c.max_east_m, c.max_north_m)
                or m.valid_from < times[0] or m.valid_until > times[-1]):
            raise ValueError('Deklarerad täckning/giltighet måste täckas av rutnätet')
        count = len(m.units)
        values = []
        for plane in self.values:
            rows = []
            for row in plane:
                nodes = []
                for node in row:
                    if node is None:
                        nodes.append(None)
                        continue
                    node = tuple(node)
                    if (len(node) != count or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                                or not isfinite(v) for v in node)):
                        raise ValueError('Ogiltiga normaliserade komponenter; markera dataluckor med None')
                    if m.product == 'waves' and (node[0] < 0 or node[1] <= 0
                                                or abs(hypot(node[2], node[3]) - 1) > 1e-9):
                        raise ValueError('Vågor kräver Hs>=0, Tm02>0 och enhetsvektor för från-riktning')
                    nodes.append(node)
                if len(nodes) != len(self.east_m):
                    raise ValueError('Rutnätets östdimension stämmer inte')
                rows.append(tuple(nodes))
            if len(rows) != len(self.north_m):
                raise ValueError('Rutnätets norddimension stämmer inte')
            values.append(tuple(rows))
        if len(values) != len(times):
            raise ValueError('Rutnätets tidsdimension stämmer inte')
        object.__setattr__(self, 'values', tuple(values))
        cells = tuple(tuple(cell) for cell in self.invalid_cells)
        limits = (len(times) - 1, len(self.north_m) - 1, len(self.east_m) - 1)
        if any(len(cell) != 3 or any(not isinstance(v, int) or isinstance(v, bool)
                    or not 0 <= v < limit for v, limit in zip(cell, limits)) for cell in cells):
            raise ValueError('Ogiltig cellmask')
        object.__setattr__(self, 'invalid_cells', cells)

    def interpolate(self, position, time):
        time = utc_time(time, 'Uppslagstid')
        m = self.metadata
        if not m.valid_from <= time < m.valid_until:
            raise DataUnavailable('Utanför produktens giltighet [från,till); extrapolation avvisad')
        if not m.coverage.contains(position):
            raise DataUnavailable('Utanför geografisk täckning; extrapolation avvisad')
        k, ft = axis_cell(self.times, time)
        j, fn = axis_cell(self.north_m, position.north)
        i, fe = axis_cell(self.east_m, position.east)
        # Closed invalid cells conservatively reject their shared boundaries too.
        for tk, nj, ei in self.invalid_cells:
            if (self.times[tk] <= time <= self.times[tk + 1]
                    and self.north_m[nj] <= position.north <= self.north_m[nj + 1]
                    and self.east_m[ei] <= position.east <= self.east_m[ei + 1]):
                raise DataUnavailable('Markerad ogiltig cell; interpolation avvisad')
        nodes = [[[self.values[k+dt][j+dn][i+de] for de in (0, 1)]
                  for dn in (0, 1)] for dt in (0, 1)]
        if any(node is None for plane in nodes for row in plane for node in row):
            raise DataUnavailable('Datalucka i interpolationsstödet')

        def lerp(a, b, weight):
            # Exact constants stay constant: no rounding above a hard limit.
            if a == b or weight == 0:
                return a
            if weight == 1:
                return b
            value = (1-weight)*a + weight*b
            if not isfinite(value):
                raise DataUnavailable('Interpolation gav ogiltiga komponenter')
            return max(min(a, b), min(max(a, b), value))

        result = []
        for component in range(len(m.units)):
            spatial = []
            for plane in nodes:
                rows = [lerp(row[0][component], row[1][component], fe) for row in plane]
                spatial.append(lerp(rows[0], rows[1], fn))
            result.append(lerp(spatial[0], spatial[1], ft))
        if not all(isfinite(v) for v in result):
            raise DataUnavailable('Interpolation gav ogiltiga komponenter')
        return tuple(result)


@dataclass(frozen=True)
class ForecastDataset:
    dataset_id: str
    version: str
    products: tuple[GridProduct, ...]

    def __post_init__(self):
        if not all(isinstance(v, str) and v.strip() for v in (self.dataset_id, self.version)):
            raise ValueError('Prognosunderlaget kräver identitet och version')
        products = tuple(self.products)
        if not products or any(type(p) is not GridProduct for p in products):
            raise ValueError('Minst en normaliserad produkt krävs')
        if len({p.metadata.product for p in products}) != len(products):
            raise ValueError('Högst en fryst produkt per slag; inget automatiskt prognosbyte')
        origins = {(p.metadata.coverage.origin_latitude, p.metadata.coverage.origin_longitude)
                   for p in products}
        if len(origins) != 1:
            raise ValueError('Alla produkter måste använda samma geografiska origo')
        object.__setattr__(self, 'products', products)

    @property
    def product_metadata(self):
        return tuple(p.metadata for p in self.products)

    def evaluate(self, position: Vector, time: datetime) -> Conditions:
        time = utc_time(time, 'Uppslagstid')
        data, metadata, reasons = {}, {}, []
        for product in self.products:
            name = product.metadata.product
            metadata[name] = product.metadata
            try:
                data[name] = product.interpolate(position, time)
            except DataUnavailable as error:
                reasons.append(f'{name}: {error}')
        for name in ('wind', 'current', 'waves'):
            if name not in metadata:
                reasons.append(f'{name}: produkt saknas i underlaget')
        wind, current, waves = data.get('wind'), data.get('current'), data.get('waves')
        wm = metadata.get('waves')
        wave_data = None
        if waves is not None:
            if hypot(waves[2], waves[3]) < 1e-12:
                reasons.append('waves: interpolerad från-riktning är odefinierad')
            else:
                wave_data = WaveData(waves[0], waves[1], degrees(atan2(waves[2], waves[3])) % 360,
                                     wm.valid_from, wm.valid_until, wm.source, wm.version,
                                     issued_at=wm.issued_at, metadata=wm)
        cm = metadata.get('current')
        return Conditions(Vector(*current) if current is not None else None,
                          reason='; '.join(reasons), source=cm.source if cm else 'missing-current',
                          version=cm.version if cm else self.version,
                          wind=Vector(*wind) if wind is not None else None,
                          valid_from=cm.valid_from if cm else None,
                          valid_until=cm.valid_until if cm else None,
                          issued_at=cm.issued_at if cm else None, waves=wave_data,
                          wind_metadata=metadata.get('wind'), current_metadata=cm,
                          waves_metadata=wm, dataset_id=self.dataset_id, dataset_version=self.version)
