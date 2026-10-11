"""Integration med explicit mittpunktsmetod; ingen databas eller I/O."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import isfinite, sqrt

from .model import BoatModel, ConstantBoat, KNOT, Vector
from .environment import Environment
from .obstacles import check_segment, ObstacleCollision


@dataclass(frozen=True)
class Evaluation:
    position: Vector
    time: datetime
    water: Vector
    current: Vector
    ground: Vector
    assumptions: tuple[str, ...]
    source: str
    version: str
    current_status: str
    valid_from: datetime | None
    valid_until: datetime | None


@dataclass(frozen=True)
class Step:
    start: Evaluation
    midpoint: Evaluation
    end_position: Vector
    end_time: datetime


def evaluate(boat: BoatModel, environment: Environment, position, time, allow_missing_current=False):
    weather = environment.evaluate(position, time)
    water, assumptions = boat.evaluate(position, time, weather)
    if not all(isfinite(v) for v in (water.east, water.north)):
        raise ValueError("Båtmodellen gav ogiltig hastighet")
    current = weather.current
    status = "valid"
    reason = weather.reason
    if weather.valid_from is not None and time < weather.valid_from:
        current, reason = None, "före prognosens giltighetstid"
    elif weather.valid_until is not None and time >= weather.valid_until:
        current, reason = None, "prognosens slut"
    if current is None or not all(isfinite(v) for v in (current.east, current.north)):
        reason = reason or ("saknade data" if current is None else "ogiltiga värden")
        if not allow_missing_current:
            raise ValueError(f"Strömdata saknas vid {time.isoformat()}, "
                             f"position ({position.east}, {position.north}) m: {reason}")
        status = "assumed_zero"
        assumptions += (f"Strömdata saknas ({reason}); strömmen antas vara 0 m/s.",)
        current = Vector(0, 0)
    return Evaluation(position, time, water, current, water + current,
                      assumptions, weather.source, weather.version, status,
                      weather.valid_from, weather.valid_until)


def simulate(boat: BoatModel, environment: Environment, start, duration, step_seconds=60, position=Vector(0, 0),
             *, allow_missing_current=False, obstacles=()):
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Starttid måste ha tidszon")
    if not isfinite(duration) or duration < 0 or not isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("Ogiltig varaktighet eller steglängd")
    if not all(isfinite(v) for v in (position.east, position.north)):
        raise ValueError("Ogiltig startposition")
    if duration > 0 and (timedelta(seconds=step_seconds).total_seconds() == 0 or
                         timedelta(seconds=duration).total_seconds() == 0):
        raise ValueError("Tidssteg och varaktighet måste vara minst en mikrosekund")
    time = start.astimezone(timezone.utc)
    obstacles = tuple(obstacles)
    check_segment(position, position, obstacles)
    remaining = duration
    steps = []
    while remaining > 0:
        dt = min(step_seconds, remaining)
        first = evaluate(boat, environment, position, time, allow_missing_current)
        middle = evaluate(boat, environment, position + first.ground.scaled(dt / 2),
                          time + timedelta(seconds=dt / 2), allow_missing_current)
        end = position + middle.ground.scaled(dt)
        check_segment(position, end, obstacles)
        position = end
        time += timedelta(seconds=dt)
        steps.append(Step(first, middle, position, time))
        remaining -= dt
    return steps


class CourseUnavailable(ValueError):
    """Kurs eller minsta framdrift kan inte upprätthållas vid ett uppslag."""


@dataclass(frozen=True)
class Voyage:
    status: str
    reason: str
    steps: tuple[Step, ...]
    end_position: Vector
    elapsed_seconds: float
    travel_seconds: float | None
    target: Vector
    tolerance_m: float
    assumptions: tuple[str, ...] = (
        "Syntetisk uppskattad båt: konstant fart genom vattnet, noll vindavdrift.",)


def compensated_evaluation(speed_knots, direction, environment, position, time,
                           min_progress_m_s):
    # Återanvänd strikt datavalidering; ingen fallback i målfärden.
    sample = evaluate(ConstantBoat(speed_knots=0, leeway=0), environment, position, time)
    lateral = Vector(-direction.north, direction.east)
    cross = sample.current.dot(lateral)
    speed = speed_knots * KNOT
    if abs(cross) > speed:
        raise CourseUnavailable("Sidoströmmen är för stark för önskad kurs över grund")
    along = sqrt(max(0, speed * speed - cross * cross))
    progress = along + sample.current.dot(direction)
    if progress <= min_progress_m_s:
        raise CourseUnavailable("Framdriften mot målet är otillräcklig")
    water = direction.scaled(along) + lateral.scaled(-cross)
    return replace(sample, water=water, ground=water + sample.current)


def sail_to_target(environment: Environment, start, target: Vector, *, speed_knots=5,
                   position=Vector(0, 0), step_seconds=60, max_seconds=86400,
                   tolerance_m=0.01, min_progress_m_s=0.01, max_steps=100000,
                   obstacles=()):
    """Rak kompenserad målfärd; restid ges enbart vid uppnått mål."""
    values = (speed_knots, step_seconds, max_seconds, tolerance_m, min_progress_m_s,
              position.east, position.north, target.east, target.north)
    if not all(isfinite(v) for v in values):
        raise ValueError("Indata måste vara finita")
    if (speed_knots <= 0 or step_seconds < 1e-6 or max_seconds <= 0
            or tolerance_m <= 0 or min_progress_m_s < 0
            or not isinstance(max_steps, int) or max_steps <= 0):
        raise ValueError("Ogiltiga gränser för målfärd")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Starttid måste ha tidszon")
    start = start.astimezone(timezone.utc)
    time, elapsed, steps = start, 0.0, []
    offset = target - position
    distance = offset.speed
    direction = offset.scaled(1 / distance) if distance else Vector(0, 0)

    def result(status, reason=""):
        return Voyage(status, reason, tuple(steps), position, elapsed,
                      elapsed if status == "arrived" else None, target, tolerance_m)

    obstacles = tuple(obstacles)
    try:
        check_segment(position, position, obstacles)
        check_segment(target, target, obstacles)
    except ObstacleCollision as exc:
        return result("blocked", str(exc))

    while (target - position).speed > tolerance_m:
        if elapsed >= max_seconds or len(steps) >= max_steps:
            return result("limit_reached", "Simuleringens tids- eller steggräns nådd")
        try:
            first = compensated_evaluation(speed_knots, direction, environment,
                                           position, time, min_progress_m_s)
            remaining = (target - position).dot(direction)
            # Startfarten begränsar predikterad mittpunkt till före målet.
            dt = min(step_seconds, max_seconds - elapsed,
                     remaining / first.ground.dot(direction))

            def trial(seconds):
                middle = compensated_evaluation(
                    speed_knots, direction, environment,
                    position + first.ground.scaled(seconds / 2),
                    time + timedelta(seconds=seconds / 2), min_progress_m_s)
                return middle, position + middle.ground.scaled(seconds)

            middle, end = trial(dt)
            if (end - target).dot(direction) > 0:
                # Lokalisera målpassagen genom omräknade mittpunktssteg.
                low, high = 0.0, dt
                for _ in range(60):
                    dt = (low + high) / 2
                    middle, end = trial(dt)
                    error = (end - target).dot(direction)
                    if abs(error) <= tolerance_m / 10:
                        break
                    if error > 0:
                        high = dt
                    else:
                        low = dt
            if dt < 1e-6:
                return result("limit_reached", "Tidsupplösningen räcker inte för målpassagen")
            check_segment(position, end, obstacles)
        except ObstacleCollision as exc:
            return result("blocked", str(exc))
        except CourseUnavailable as exc:
            return result("infeasible", str(exc))
        except ValueError as exc:
            return result("data_unavailable", str(exc))
        elapsed += dt
        time = start + timedelta(seconds=elapsed)
        steps.append(Step(first, middle, end, time))
        position = end
    return result("arrived")
