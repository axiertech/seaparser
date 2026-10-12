"""Compare complete, predefined waypoint routes; no graph pruning or I/O."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

from .calculation import Voyage, sail_to_target
from .environment import Environment
from .model import Vector


@dataclass(frozen=True)
class RouteCandidate:
    name: str
    waypoints: tuple[Vector, ...] = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Kandidaten måste ha ett namn")
        points = tuple(self.waypoints)
        if any(not isinstance(p, Vector) or not all(isfinite(v) for v in (p.east, p.north))
               for p in points):
            raise ValueError("Vägpunkter måste vara finita positioner")
        object.__setattr__(self, 'waypoints', points)


@dataclass(frozen=True)
class RouteResult:
    candidate: RouteCandidate
    status: str
    reason: str
    legs: tuple[Voyage, ...]
    departure_time: datetime
    arrival_time: datetime | None
    end_position: Vector
    elapsed_seconds: float
    travel_seconds: float | None
    target: Vector
    tolerance_m: float


@dataclass(frozen=True)
class RouteComparison:
    status: str
    candidates: tuple[RouteResult, ...]
    fastest: RouteResult | None
    scope: str = "Endast de angivna kompletta kandidatrutterna; ingen global optimalitet."


def compare_routes(environment: Environment, start: datetime, target: Vector,
                   candidates, *, position=Vector(0, 0), obstacles=(), speed_knots=5,
                   step_seconds=60, max_seconds=86400, tolerance_m=0.01,
                   min_progress_m_s=0.01, max_steps=100000,
                   max_candidates=100, max_waypoints=32):
    """Independent full simulations with equal limits; first candidate wins exact ties."""
    values = (speed_knots, step_seconds, max_seconds, tolerance_m, min_progress_m_s,
              position.east, position.north, target.east, target.north)
    if (not all(isfinite(v) for v in values) or speed_knots <= 0 or step_seconds < 1e-6
            or max_seconds <= 0 or tolerance_m <= 0 or min_progress_m_s < 0):
        raise ValueError("Ogiltiga färdgränser eller positioner")
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0
           for v in (max_steps, max_candidates, max_waypoints)):
        raise ValueError("Sök- och steggränser måste vara positiva heltal")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Starttid måste ha tidszon")
    # Bound consumption even for a generator; no implicit candidate generation.
    routes = []
    names = set()
    for candidate in candidates:
        if len(routes) >= max_candidates:
            raise ValueError("För många kandidatrutter")
        if not isinstance(candidate, RouteCandidate) or candidate.name in names:
            raise ValueError("Kandidatrutter måste ha unika namn")
        if len(candidate.waypoints) > max_waypoints:
            raise ValueError("För många fördefinierade vägpunkter")
        names.add(candidate.name)
        routes.append(candidate)
    if not routes:
        raise ValueError("Minst en explicit kandidatrutt krävs")
    start = start.astimezone(timezone.utc)
    obstacles = tuple(obstacles)
    results = []
    for candidate in routes:
        current_position, current_time = position, start
        legs, step_count = [], 0
        status, reason = 'arrived', ''
        for destination in (*candidate.waypoints, target):
            elapsed = (current_time - start).total_seconds()
            remaining_seconds = max_seconds - elapsed
            remaining_steps = max_steps - step_count
            if ((destination - current_position).speed > tolerance_m
                    and (remaining_seconds <= 0 or remaining_steps <= 0)):
                status, reason = 'limit_reached', 'Hela kandidatruttens tids- eller steggräns nådd'
                break
            # Zero-distance legs still check obstacle contact; never snap to a waypoint.
            leg = sail_to_target(
                environment, current_time, destination, position=current_position,
                obstacles=obstacles, speed_knots=speed_knots, step_seconds=step_seconds,
                max_seconds=max(remaining_seconds, 1e-6), tolerance_m=tolerance_m,
                min_progress_m_s=min_progress_m_s, max_steps=max(remaining_steps, 1))
            legs.append(leg)
            step_count += len(leg.steps)
            current_position = leg.end_position
            if leg.steps:
                current_time = leg.steps[-1].end_time
            if leg.status != 'arrived':
                status, reason = leg.status, leg.reason
                break
        elapsed = (current_time - start).total_seconds()
        results.append(RouteResult(
            candidate, status, reason, tuple(legs), start,
            current_time if status == 'arrived' else None, current_position,
            elapsed, elapsed if status == 'arrived' else None, target, tolerance_m))
    feasible = [result for result in results if result.status == 'arrived']
    fastest = min(feasible, key=lambda result: result.travel_seconds) if feasible else None
    return RouteComparison('selected' if fastest is not None else 'no_feasible_route',
                           tuple(results), fastest)
