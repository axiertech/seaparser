"""Provider-agnostic weather adapter with data classes and a stub provider.

This module defines only data classes and a stub provider that returns
estimated data. It must not import HTTP clients, SQL or UI code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class WeatherSnapshot:
    """A point-in-time weather observation or forecast.

    All numeric fields may be None when the corresponding value is unknown.
    ``estimated`` marks data that is not a verified observation.
    """
    wind_speed_ms: float | None = None
    wave_height_m: float | None = None
    current_speed_ms: float | None = None
    as_of: datetime | None = None
    estimated: bool = True


def is_usable(snapshot: WeatherSnapshot, now: datetime,
              max_age_s: float = 6 * 3600) -> bool:
    """Return True only for fresh, non-estimated data.

    Rejects a missing snapshot, estimated data, a missing, naive or
    unparseable ``as_of``, data older than ``max_age_s``, or ``as_of`` in
    the future. ``as_of`` must be timezone-aware (UTC).
    """
    if snapshot is None:
        return False
    if snapshot.estimated:
        return False
    if snapshot.as_of is None:
        return False
    try:
        as_of = snapshot.as_of
        if as_of.tzinfo is None:
            return False
        now_utc = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    except (AttributeError, ValueError, TypeError):
        return False
    age = (now_utc - as_of).total_seconds()
    if age < 0:
        return False
    return age <= max_age_s


class StubProvider:
    """A stub provider that returns estimated data with the current UTC time."""

    def fetch(self, lat: float, lon: float) -> WeatherSnapshot:
        """Return an estimated WeatherSnapshot stamped with the current UTC time."""
        return WeatherSnapshot(
            wind_speed_ms=None,
            wave_height_m=None,
            current_speed_ms=None,
            as_of=datetime.now(timezone.utc),
            estimated=True,
        )
