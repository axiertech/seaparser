"""Heading-dependent polar compensation; complete roots on linear polar pieces."""
from dataclasses import dataclass
from math import atan2, ceil, cos, degrees, floor, isfinite, pi, radians, sin

from .environment import water_relative_wind
from .model import CourseUnavailable, KNOT, Vector, velocity, CROSS_TRACK_TOLERANCE
from .polar import SailPolar, SYNTHETIC_POLAR

@dataclass(frozen=True)
class PolarBoat:
    polar: SailPolar = SYNTHETIC_POLAR
    heading: float = 90

    def __post_init__(self):
        if not isfinite(self.heading):
            raise ValueError('Styrkursen måste vara finit')

    @property
    def assumptions(self):
        return self.polar.assumptions

    def wind(self, weather):
        wind = water_relative_wind(weather)
        if wind.speed < 1e-12:
            raise CourseUnavailable('Ingen tillåten segellösning: vind relativt vatten är noll')
        speed_knots = wind.speed / KNOT
        for boundary in self.polar.wind_knots:
            if abs(speed_knots - boundary) <= 1e-10:
                speed_knots = boundary
                break
        # Validate strength before searching or evaluating forbidden headings.
        self.polar.speed_m_s(speed_knots, 180)
        return speed_knots, (wind.course + 180) % 360

    def evaluate(self, position, time, weather):
        strength, from_direction = self.wind(weather)
        angle = abs((self.heading - from_direction + 180) % 360 - 180)
        # Only roundoff at exact boundaries is tolerated, never a meaningful no-go angle.
        if angle < self.polar.angles_degrees[0] - 1e-10:
            raise CourseUnavailable('Förbjuden vindvinkel; automatisk kryssplanering saknas')
        angle = max(angle, self.polar.angles_degrees[0])
        return velocity(self.polar.speed_m_s(strength, angle), self.heading), self.assumptions

    def compensate(self, direction, position, time, weather, min_progress_m_s):
        strength, from_direction = self.wind(weather)
        wind_heading = radians(from_direction)
        target_heading = radians(direction.course)
        lateral = Vector(-direction.north, direction.east)
        cross = weather.current.dot(lateral)
        solutions = []

        def bisect(function, low, high):
            left = function(low)
            for _ in range(60):
                middle = (low + high) / 2
                value = function(middle)
                if left * value <= 0:
                    high = middle
                else:
                    low, left = middle, value
            return (low + high) / 2

        # Each allowed signed TWA segment has s(theta)=s0+k*(theta-lo).
        for side in (-1, 1):
            for a, b in zip(self.polar.angles_degrees, self.polar.angles_degrees[1:]):
                low, high = sorted((wind_heading + side * radians(a),
                                    wind_heading + side * radians(b)))
                low_speed = self.polar.speed_m_s(strength, b if side < 0 else a)
                high_speed = self.polar.speed_m_s(strength, a if side < 0 else b)
                slope = (high_speed - low_speed) / (high - low)

                def speed(theta):
                    return max(0, low_speed + slope * (theta - low))

                def residual(theta):
                    return -speed(theta) * sin(theta - target_heading) + cross

                # F' = -(k*sin(delta)+s*cos(delta)). Its zeros obey
                # g=delta-atan2(k,s)=pi/2+n*pi; g'=1+k²/(s²+k²)>0.
                # Split at ALL stationary points, including tangential roots.
                def phase(theta):
                    return theta - target_heading - atan2(slope, speed(theta))

                cuts = [low, high]
                lower, upper = phase(low), phase(high)
                for n in range(ceil((lower - pi / 2) / pi), floor((upper - pi / 2) / pi) + 1):
                    level = pi / 2 + n * pi
                    cuts.append(bisect(lambda theta: phase(theta) - level, low, high))
                cuts.sort()
                roots = [theta for theta in cuts if abs(residual(theta)) <= CROSS_TRACK_TOLERANCE]
                for left, right in zip(cuts, cuts[1:]):
                    if residual(left) * residual(right) < 0:
                        roots.append(bisect(residual, left, right))
                for theta in roots:
                    water = velocity(speed(theta), degrees(theta))
                    ground = water + weather.current
                    if (abs(ground.dot(lateral)) <= CROSS_TRACK_TOLERANCE
                            and ground.dot(direction) > min_progress_m_s):
                        solutions.append((ground.dot(direction), theta, water))
        if not solutions:
            raise CourseUnavailable('Ingen tillåten polarlösning för kurs/ström; automatisk kryssplanering saknas')
        # Highest positive progress; deterministic heading tie-break within this model.
        _, _, water = max(solutions, key=lambda item: (item[0], -item[1]))
        return water, self.assumptions
