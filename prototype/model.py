"""Båtmodell och gemensamma storheter: meter, sekunder, öst/nord."""
from dataclasses import dataclass
from math import sin, cos, radians, hypot, atan2, degrees, isfinite, sqrt
from datetime import datetime
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import Conditions

KNOT = 1852 / 3600
CROSS_TRACK_TOLERANCE = 1e-9  # m/s; numerical compensation residual


class BoatModel(Protocol):
    def evaluate(self, position: "Vector", time: datetime,
                 weather: "Conditions") -> tuple["Vector", tuple[str, ...]]: ...


class CourseUnavailable(ValueError):
    """Ingen tillåten styrkurs med tillräcklig framdrift."""


class BoatPerformance(BoatModel, Protocol):
    @property
    def assumptions(self) -> tuple[str, ...]: ...

    def compensate(self, direction: "Vector", position: "Vector", time: datetime,
                   weather: "Conditions", min_progress_m_s: float
                   ) -> tuple["Vector", tuple[str, ...]]: ...


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
        if self.speed < 1e-12:
            return None
        bearing = degrees(atan2(self.east, self.north)) % 360
        return 0.0 if bearing == 360 else bearing


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

    @property
    def assumptions(self):
        return ("Syntetisk uppskattad konstantfartsmodell v1; ingen uppmätt båtprestanda.",)

    def compensate(self, direction, position, time, weather, min_progress_m_s):
        # Analytic formula is valid only for this heading-independent speed model.
        if self.leeway not in (None, 0):
            raise ValueError("Kompenserad konstantmodell stöder endast noll vindavdrift")
        lateral = Vector(-direction.north, direction.east)
        cross = weather.current.dot(lateral)
        speed = self.speed_knots * KNOT
        if abs(cross) > speed:
            raise CourseUnavailable("Sidoströmmen är för stark för önskad kurs över grund")
        along = sqrt(max(0, speed * speed - cross * cross))
        if along + weather.current.dot(direction) <= min_progress_m_s:
            raise CourseUnavailable("Framdriften mot målet är otillräcklig")
        return (direction.scaled(along) + lateral.scaled(-cross),
                self.assumptions + ("Kompenserad färd antar noll vindavdrift.",))
