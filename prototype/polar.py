"""Estimated, immutable synthetic sail polar; no measured boat data."""
from dataclasses import dataclass
from math import isfinite

from .model import KNOT


@dataclass(frozen=True)
class SailPolar:
    identifier: str
    version: str
    source: str
    wind_knots: tuple[float, ...]
    angles_degrees: tuple[float, ...]
    boat_knots: tuple[tuple[float, ...], ...]
    estimated: bool = True

    def __post_init__(self):
        if not self.identifier or not self.version or not self.source or not self.estimated:
            raise ValueError('Denna polar kräver spårbar uppskattad testdata')
        if not isinstance(self.wind_knots, tuple) or not isinstance(self.angles_degrees, tuple):
            raise ValueError('Polarens axlar måste vara oföränderliga tuples')
        for axis in (self.wind_knots, self.angles_degrees):
            if len(axis) < 2 or any(not isfinite(x) for x in axis) or any(a >= b for a, b in zip(axis, axis[1:])):
                raise ValueError('Polaraxlar måste vara finita och strikt växande')
        if self.wind_knots[0] < 0 or self.angles_degrees[0] <= 0 or self.angles_degrees[-1] != 180:
            raise ValueError('Ogiltig vind- eller vinkelaxel')
        if (not isinstance(self.boat_knots, tuple) or len(self.boat_knots) != len(self.wind_knots)
                or any(not isinstance(row, tuple) or len(row) != len(self.angles_degrees)
                       or any(not isfinite(x) or x < 0 for x in row) for row in self.boat_knots)):
            raise ValueError('Ogiltiga polarfarter')

    @property
    def assumptions(self):
        return (f'Uppskattad syntetisk testpolar {self.identifier} version {self.version}; '
                f'källa: {self.source}. Ingen uppmätt båtprestanda; noll vindavdrift.',)

    def speed_m_s(self, wind_knots, angle_degrees):
        if not isfinite(wind_knots) or not isfinite(angle_degrees):
            raise ValueError('Polarindata måste vara finita')
        if not self.wind_knots[0] <= wind_knots <= self.wind_knots[-1]:
            raise ValueError('Vindstyrkan ligger utanför testpolarens giltiga intervall')
        if not self.angles_degrees[0] <= angle_degrees <= 180:
            raise ValueError('Vindvinkeln ligger utanför tillåtet polarintervall')
        def bracket(axis, x):
            for index in range(len(axis) - 1):
                if x <= axis[index + 1]:
                    return index, (x - axis[index]) / (axis[index + 1] - axis[index])
            raise ValueError('Indata utanför polar')
        i, wind_weight = bracket(self.wind_knots, wind_knots)
        j, angle_weight = bracket(self.angles_degrees, angle_degrees)
        low = self.boat_knots[i][j] * (1 - angle_weight) + self.boat_knots[i][j + 1] * angle_weight
        high = self.boat_knots[i + 1][j] * (1 - angle_weight) + self.boat_knots[i + 1][j + 1] * angle_weight
        return (low * (1 - wind_weight) + high * wind_weight) * KNOT


SYNTHETIC_POLAR = SailPolar(
    'seaparser-synthetic-sail', '1', 'Handvalda referensvärden 2026-10-12, uppskattad testdata',
    (0, 10, 20), (45, 60, 90, 120, 150, 180),
    ((0, 0, 0, 0, 0, 0), (3, 4, 5, 4.5, 3.5, 3), (4.5, 6, 7, 6.5, 5, 4.5)))
