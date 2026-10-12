"""Forecast freshness at one explicit planning-clock snapshot, not simulated ETA."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Protocol


def utc_time(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f'{name} måste vara en explicit tidszonsmedveten tid')
    return value.astimezone(timezone.utc)


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def __post_init__(self):
        object.__setattr__(self, 'instant', utc_time(self.instant, 'Klocktid'))

    def now(self):
        return self.instant


def capture_planning_time(clock, policy):
    if clock is None:
        if policy is not None:
            raise ValueError('Prognosålderskontroll kräver en explicit klocka')
        return None
    return utc_time(clock.now(), 'Planeringstid')


@dataclass(frozen=True)
class ForecastPolicy:
    max_age_seconds: float

    def __post_init__(self):
        if (isinstance(self.max_age_seconds, bool) or not isinstance(self.max_age_seconds, (int, float))
                or not isfinite(self.max_age_seconds) or self.max_age_seconds < 0):
            raise ValueError('Maximal prognosålder måste vara finit och icke-negativ')

    def check(self, weather, planning_time):
        planning_time = utc_time(planning_time, 'Planeringstid')
        records = [('Vind/ström', weather.issued_at)]
        if weather.waves is not None:
            records.append(('Vågor', weather.waves.issued_at))
        for name, issued_at in records:
            issued_at = utc_time(issued_at, f'{name}: utfärdandetid')
            age = (planning_time - issued_at).total_seconds()
            if age < 0:
                raise ValueError(f'{name}: prognosen är utfärdad efter planeringstidpunkten')
            if age > self.max_age_seconds:
                raise ValueError(f'{name}: prognosen är för gammal vid planeringen')
