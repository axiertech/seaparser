"""Båtmodell och gemensamma storheter: meter, sekunder, öst/nord."""
from dataclasses import dataclass
from math import sin, cos, radians, hypot, atan2, degrees, isfinite
from datetime import datetime
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import Conditions

KNOT = 1852 / 3600


class BoatModel(Protocol):
    def evaluate(self, position: "Vector", time: datetime,
                 weather: "Conditions") -> tuple["Vector", tuple[str, ...]]: ...


@dataclass(frozen=True)
class Vector:
    east: float
    north: float

    def __add__(self, other):
        return Vector(self.east + other.east, self.north + other.north)

    def __sub__(self, other):
        return Vector(self.east - other.east, self.north - other.north)

    def dot(self, other):
        return self.east * other.east + self.north * other.north

    def scaled(self, seconds):
        return Vector(self.east * seconds, self.north * seconds)

    @property
    def speed(self):
        return hypot(self.east, self.north)

    @property
    def course(self):
        return None if self.speed < 1e-12 else degrees(atan2(self.east, self.north)) % 360


def velocity(speed, direction):
    """Riktning mot rörelsen, medurs från nord; fart i m/s."""
    angle = radians(direction)
    return Vector(speed * sin(angle), speed * cos(angle))


@dataclass(frozen=True)
class ConstantBoat:
    speed_knots: float = 5
    heading: float = 90
    leeway: float | None = None

    def __post_init__(self):
        if not isfinite(self.speed_knots) or self.speed_knots < 0:
            raise ValueError("Båtfarten måste vara finit och icke-negativ")
        if not isfinite(self.heading) or (self.leeway is not None and not isfinite(self.leeway)):
            raise ValueError("Stävriktning och avdriftsvinkel måste vara finita")

    def evaluate(self, position, time, weather):
        # position, tid och väder ingår i gränssnittet för framtida modeller.
        assumption = "Vindavdriftsmodell saknas; vindavdrift antas vara 0°."
        return (velocity(self.speed_knots * KNOT, self.heading + (self.leeway or 0)),
                (assumption,) if self.leeway is None else ())
