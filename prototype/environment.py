"""Syntetiska väder-/strömdata utvärderade vid given position och UTC-tid."""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from .model import Vector


@dataclass(frozen=True)
class Conditions:
    current: Vector | None
    reason: str = ""
    source: str = "synthetic"
    version: str = "1"
    wind: Vector | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    def __post_init__(self):
        for boundary in (self.valid_from, self.valid_until):
            if boundary is not None and (boundary.tzinfo is None or boundary.utcoffset() is None):
                raise ValueError("Prognosens giltighetstid måste ha tidszon")
        if (self.valid_from is not None and self.valid_until is not None
                and self.valid_from >= self.valid_until):
            raise ValueError("Prognosens giltighetsintervall måste vara positivt")


class Environment(Protocol):
    def evaluate(self, position: Vector, time: datetime) -> Conditions: ...


@dataclass(frozen=True)
class SyntheticEnvironment:
    field: Callable[[Vector, datetime], Conditions]

    def evaluate(self, position, time):
        return self.field(position, time)
