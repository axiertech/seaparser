"""Syntetiska väder-/strömdata utvärderade vid given position och UTC-tid."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Callable, Protocol

from .model import Vector, velocity
from .forecast_metadata import ProductMetadata


@dataclass(frozen=True)
class WaveData:
    """Synthetic Hm0 metres, Tm02 seconds, mean FROM bearing in true ground axes."""
    height_m: float | None
    period_seconds: float | None
    from_degrees: float | None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    source: str = "synthetic-waves"
    version: str = "1"
    period_kind: str = "tm02"
    direction_reference: str = "ground-from-true-north"
    issued_at: datetime | None = None
    metadata: ProductMetadata | None = None

    def __post_init__(self):
        if self.period_kind != "tm02" or self.direction_reference != "ground-from-true-north":
            raise ValueError("Vågdata kräver Tm02 och markrelativ från-riktning")
        for boundary in (self.valid_from, self.valid_until, self.issued_at):
            if boundary is not None and (not isinstance(boundary, datetime) or boundary.tzinfo is None or boundary.utcoffset() is None):
                raise ValueError("Vågornas giltighetstid måste ha tidszon")
        if self.valid_from is not None and self.valid_until is not None and self.valid_from >= self.valid_until:
            raise ValueError("Vågornas giltighetsintervall måste vara positivt")


@dataclass(frozen=True)
class Conditions:
    current: Vector | None
    reason: str = ""
    source: str = "synthetic"
    version: str = "1"
    wind: Vector | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    wind_reference: str = "ground"
    waves: WaveData | None = None
    issued_at: datetime | None = None
    wind_metadata: ProductMetadata | None = None
    current_metadata: ProductMetadata | None = None
    waves_metadata: ProductMetadata | None = None
    dataset_id: str | None = None
    dataset_version: str | None = None

    def __post_init__(self):
        if self.wind_reference not in ("ground", "water"):
            raise ValueError("Vindens referensram måste vara ground eller water")
        for boundary in (self.valid_from, self.valid_until, self.issued_at):
            if boundary is not None and (not isinstance(boundary, datetime) or boundary.tzinfo is None or boundary.utcoffset() is None):
                raise ValueError("Prognosens giltighetstid måste ha tidszon")
        if (self.valid_from is not None and self.valid_until is not None
                and self.valid_from >= self.valid_until):
            raise ValueError("Prognosens giltighetsintervall måste vara positivt")


class Environment(Protocol):
    def evaluate(self, position: Vector, time: datetime) -> Conditions: ...


class SegmentEnvironment(Environment, Protocol):
    def validate_segment(self, start: Vector, start_time: datetime, end: Vector,
                         end_time: datetime, *, required_products: tuple[str, ...]) -> None: ...


class MotionEnvironment(Environment, Protocol):
    """Optional pure kinematic mapping; weather and boat vectors stay physical."""
    def position_rate(self, position: Vector, physical_velocity: Vector) -> Vector: ...
    def physical_direction(self, position: Vector, local_direction: Vector) -> Vector: ...


@dataclass(frozen=True)
class SyntheticEnvironment:
    field: Callable[[Vector, datetime], Conditions]

    def evaluate(self, position, time):
        return self.field(position, time)


def wind_from(speed_m_s, from_degrees):
    """Air TO vector from meteorological FROM bearing, clockwise from true north."""
    if not isfinite(speed_m_s) or speed_m_s < 0 or not isfinite(from_degrees):
        raise ValueError("Vindstyrka och från-riktning måste vara finita")
    return velocity(-speed_m_s, from_degrees)


def water_relative_wind(weather):
    """W_water = W_ground - C_ground; all vectors are velocities TOWARDS motion."""
    if weather.wind is None or not all(isfinite(v) for v in (weather.wind.east, weather.wind.north)):
        raise ValueError("Vinddata saknas eller är ogiltiga")
    if weather.wind_reference == 'water':
        return weather.wind
    if weather.current is None or not all(isfinite(v) for v in (weather.current.east, weather.current.north)):
        raise ValueError("Strömdata krävs för vindens omräkning från mark till vatten")
    return weather.wind - weather.current
