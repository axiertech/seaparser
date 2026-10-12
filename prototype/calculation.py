"""Integration med explicit mittpunktsmetod; ingen databas eller I/O."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import isfinite

from .model import BoatModel, BoatPerformance, ConstantBoat, Vector, CourseUnavailable, CROSS_TRACK_TOLERANCE
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
    boat_assumptions: tuple[str, ...] = ()
    wind: Vector | None = None
    wind_reference: str = "ground"


@dataclass(frozen=True)
class Step:
    start: Evaluation
    midpoint: Evaluation
    end_position: Vector
    end_time: datetime


def evaluate(boat: BoatModel, environment: Environment, position, time, allow_missing_current=False):
    weather = environment.evaluate(position, time)
    return evaluate_conditions(boat, weather, position, time, allow_missing_current)


def evaluate_conditions(boat, weather, position, time, allow_missing_current=False):
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
                      weather.valid_from, weather.valid_until,
                      getattr(boat, "assumptions", ()), weather.wind, weather.wind_reference)


def forecast_step_seconds(sample, start, seconds):
    """Täck hela [start, slut); slut vid valid_until tillåts utan extrapolering."""
    if sample.current_status == "valid" and sample.valid_from is not None and sample.valid_from > start:
        raise ValueError("Strömdata saknas för hela tidssteget: före prognosens giltighetstid")
    for boundary in (sample.valid_from, sample.valid_until):
        if boundary is not None and boundary > start:
            seconds = min(seconds, (boundary - start).total_seconds())
    return seconds


def forecast_step(first, position, time, seconds, midpoint):
    seconds = forecast_step_seconds(first, time, seconds)
    # Nya gränser vid mittpunkten kräver omräkning av både tid och position.
    for _ in range(100):
        if seconds < 1e-6:
            raise ValueError("Strömdata saknas: prognosgränsen är närmare än tidsupplösningen")
        middle = midpoint(position + first.ground.scaled(seconds / 2),
                          time + timedelta(seconds=seconds / 2))
        bounded = forecast_step_seconds(middle, time, seconds)
        if bounded == seconds:
            return seconds, middle, position + middle.ground.scaled(seconds)
        seconds = bounded
    raise ValueError("Strömdata saknas: prognosgränserna kunde inte lösas för tidssteget")


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
        dt, middle, end = forecast_step(
            first, position, time, dt,
            lambda p, t: evaluate(boat, environment, p, t, allow_missing_current))
        check_segment(position, end, obstacles)
        position = end
        time += timedelta(seconds=dt)
        steps.append(Step(first, middle, position, time))
        remaining -= dt
    return steps


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
    assumptions: tuple[str, ...] = ()


def compensated_evaluation(boat: BoatPerformance, direction, environment, position, time,
                           min_progress_m_s):
    weather = environment.evaluate(position, time)
    # Validate coverage/current without calling a polar at an arbitrary fixed heading.
    sample = evaluate_conditions(ConstantBoat(speed_knots=0, leeway=0), weather, position, time)
    water, assumptions = boat.compensate(direction, position, time, weather, min_progress_m_s)
    if not all(isfinite(v) for v in (water.east, water.north)):
        raise ValueError("Båtprestandan gav ogiltig vattenhastighet")
    ground = water + sample.current
    lateral = Vector(-direction.north, direction.east)
    if abs(ground.dot(lateral)) > CROSS_TRACK_TOLERANCE or ground.dot(direction) <= min_progress_m_s:
        raise CourseUnavailable("Båtprestandan gav ingen giltig kompenserad kurs")
    return replace(sample, water=water, ground=ground, assumptions=assumptions,
                   boat_assumptions=boat.assumptions)


def sail_to_target(environment: Environment, start, target: Vector, *, speed_knots=5,
                   position=Vector(0, 0), step_seconds=60, max_seconds=86400,
                   tolerance_m=0.01, min_progress_m_s=0.01, max_steps=100000,
                   obstacles=(), boat: BoatPerformance | None = None):
    """Rak kompenserad målfärd; restid ges enbart vid uppnått mål."""
    values = (step_seconds, max_seconds, tolerance_m, min_progress_m_s,
              position.east, position.north, target.east, target.north)
    if boat is None:
        values += (speed_knots,)
    if not all(isfinite(v) for v in values):
        raise ValueError("Indata måste vara finita")
    if ((boat is None and speed_knots <= 0) or step_seconds < 1e-6 or max_seconds <= 0
            or tolerance_m <= 0 or min_progress_m_s < 0
            or not isinstance(max_steps, int) or max_steps <= 0):
        raise ValueError("Ogiltiga gränser för målfärd")
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Starttid måste ha tidszon")
    boat = boat if boat is not None else ConstantBoat(speed_knots=speed_knots, leeway=0)
    start = start.astimezone(timezone.utc)
    time, elapsed, steps = start, 0.0, []
    offset = target - position
    distance = offset.speed
    direction = offset.scaled(1 / distance) if distance else Vector(0, 0)

    def result(status, reason=""):
        return Voyage(status, reason, tuple(steps), position, elapsed,
                      elapsed if status == "arrived" else None, target, tolerance_m, boat.assumptions)

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
            first = compensated_evaluation(boat, direction, environment,
                                           position, time, min_progress_m_s)
            remaining = (target - position).dot(direction)
            # Startfarten begränsar predikterad mittpunkt till före målet.
            dt = min(step_seconds, max_seconds - elapsed,
                     remaining / first.ground.dot(direction))

            def trial(seconds):
                return forecast_step(
                    first, position, time, seconds,
                    lambda p, t: compensated_evaluation(
                        boat, direction, environment, p, t, min_progress_m_s))

            dt, middle, end = trial(dt)
            if (end - target).dot(direction) > 0:
                # Lokalisera målpassagen genom omräknade mittpunktssteg.
                low, high = 0.0, dt
                for _ in range(60):
                    dt = (low + high) / 2
                    dt, middle, end = trial(dt)
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
