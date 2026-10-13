"""Immutable normalized product identity and explicit local geographic coverage."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from .forecast import utc_time


@dataclass(frozen=True)
class Coverage:
    min_east_m: float
    min_north_m: float
    max_east_m: float
    max_north_m: float
    origin_latitude: float
    origin_longitude: float
    coordinate_reference: str = 'local-east-north-metres-at-wgs84-origin'

    def __post_init__(self):
        values = (self.min_east_m, self.min_north_m, self.max_east_m,
                  self.max_north_m, self.origin_latitude, self.origin_longitude)
        if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in values)
                or self.min_east_m >= self.max_east_m or self.min_north_m >= self.max_north_m
                or not -90 <= self.origin_latitude <= 90 or not -180 <= self.origin_longitude <= 180
                or self.coordinate_reference != 'local-east-north-metres-at-wgs84-origin'):
            raise ValueError('Explicit känd geografisk täckning och referensram krävs')

    def contains(self, position):
        return (self.min_east_m <= position.east <= self.max_east_m
                and self.min_north_m <= position.north <= self.max_north_m)


@dataclass(frozen=True)
class ProductMetadata:
    product: str
    dataset_id: str
    version: str
    source: str
    issued_at: datetime | None
    valid_from: datetime
    valid_until: datetime
    coverage: Coverage
    units: tuple[str, ...]
    reference_frame: str
    retrieved_at: datetime | None = None
    source_url: str | None = None
    license_url: str | None = None
    source_sha256: str | None = None
    planning_blockers: tuple[str, ...] = ()

    def __post_init__(self):
        specs = {'wind': (('m/s', 'm/s'), 'ground-to-true-east-north'),
                 'current': (('m/s', 'm/s'), 'ground-to-true-east-north'),
                 'waves': (('m', 's', '1', '1'), 'ground-from-true-east-north-tm02')}
        if (self.product not in specs or not all(isinstance(v, str) and v.strip()
                for v in (self.dataset_id, self.version, self.source))
                or type(self.coverage) is not Coverage):
            raise ValueError('Känd produkt, identitet, källa och täckning krävs')
        object.__setattr__(self, 'units', tuple(self.units))
        if (self.units, self.reference_frame) != specs[self.product]:
            raise ValueError('Produkten måste vara normaliserad till kända enheter och referensramar')
        for name in ('valid_from', 'valid_until'):
            object.__setattr__(self, name, utc_time(getattr(self, name), name))
        for name in ('issued_at', 'retrieved_at'):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, utc_time(value, name))
        if not isinstance(self.planning_blockers, (tuple, list)):
            raise ValueError('Planeringsblockerare kräver en lista av explicita orsaker')
        blockers = tuple(self.planning_blockers)
        if any(not isinstance(value, str) or not value.strip() for value in blockers):
            raise ValueError('Planeringsblockerare kräver explicita orsaker')
        object.__setattr__(self, 'planning_blockers', blockers)
        for name in ('source_url', 'license_url', 'source_sha256'):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f'{name} måste vara en icke-tom text när den anges')
        if self.source_sha256 is not None and (len(self.source_sha256) != 64 or
                any(char not in '0123456789abcdef' for char in self.source_sha256)):
            raise ValueError('Källans SHA-256 måste vara 64 hexadecimala tecken')
        if self.valid_from >= self.valid_until:
            raise ValueError('Positivt giltighetsintervall krävs')
