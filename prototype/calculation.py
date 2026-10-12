"""Integration med explicit mittpunktsmetod; ingen databas eller I/O."""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import isfinite

from .model import BoatModel, BoatPerformance, ConstantBoat, Vector, CourseUnavailable, CROSS_TRACK_TOLERANCE
from .environment import Environment, WaveData, Conditions
from .forecast import ForecastPolicy, Clock, capture_planning_time
from .forecast_metadata import ProductMetadata
from .segment_weather import WeatherSegmentCheck, SegmentWeatherExceeded, SegmentWeatherUnverified, SCOPE as SEGMENT_WEATHER_SCOPE
from .weather import WeatherPolicy, WeatherLimitExceeded, synthetic_comfort_rate, COMFORT_MODEL, WEATHER_VERIFICATION_SCOPE
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
    waves: WaveData | None = None
    weather_checked: bool = False
    comfort_rate_synthetic: float | None = None
    issued_at: datetime | None = None
    forecast_checked: bool = False
    planning_time: datetime | None = None
    wind_metadata: ProductMetadata | None = None
    current_metadata: ProductMetadata | None = None
    waves_metadata: ProductMetadata | None = None
    dataset_id: str | None = None
    dataset_version: str | None = None


@dataclass(frozen=True)
class Step:
    start: Evaluation
    midpoint: Evaluation
    end_position: Vector
    end_time: datetime
    weather_segment_check: WeatherSegmentCheck | None = None


def evaluate(boat: BoatModel, environment: Environment, position, time, allow_missing_current=False, weather_policy=None, forecast_policy=None, planning_time=None):
    weather = environment.evaluate(position, time)
    return evaluate_conditions(boat, weather, position, time, allow_missing_current, weather_policy, forecast_policy, planning_time)


def evaluate_conditions(boat, weather, position, time, allow_missing_current=False, weather_policy=None, forecast_policy=None, planning_time=None):
    if forecast_policy is not None:
        forecast_policy.check(weather, planning_time)
    if weather_policy is not None:
        weather_policy.check(weather, time)
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
                      getattr(boat, "assumptions", ()), weather.wind, weather.wind_reference,
                      weather.waves, weather_policy is not None,
                      synthetic_comfort_rate(weather.waves, water.course) if weather_policy is not None else None,
                      weather.issued_at, forecast_policy is not None, planning_time,
                      weather.wind_metadata, weather.current_metadata, weather.waves_metadata,
                      weather.dataset_id, weather.dataset_version)


def forecast_step_seconds(sample, start, seconds):
    """Täck hela [start, slut); slut vid valid_until tillåts utan extrapolering."""
    if sample.current_status == "valid" and sample.valid_from is not None and sample.valid_from > start:
        raise ValueError("Strömdata saknas för hela tidssteget: före prognosens giltighetstid")
    boundaries = [sample.valid_from, sample.valid_until]
    if sample.wind_metadata is not None:
        boundaries += [sample.wind_metadata.valid_from, sample.wind_metadata.valid_until]
    if sample.weather_checked:
        if sample.waves.valid_from > start:
            raise ValueError("Vågdata täcker inte hela tidssteget")
        boundaries += [sample.waves.valid_from, sample.waves.valid_until]
    for boundary in boundaries:
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


def check_forecast_segment(environment, start, start_time, end, end_time, weather_policy):
    certifier = getattr(environment, 'certify_weather_segment', None)
    if weather_policy is not None and certifier is not None:
        check = certifier(start, start_time, end, end_time, weather_policy)
        if check.status == 'exceeded':
            raise SegmentWeatherExceeded(check)
        if check.status != 'verified':
            raise SegmentWeatherUnverified(check)
        return check
    checker = getattr(environment, 'validate_segment', None)
    if checker is not None:
        checker(start, start_time, end, end_time,
                required_products=('current', 'wind', 'waves') if weather_policy is not None else ('current',))


def simulate(boat: BoatModel, environment: Environment, start, duration, step_seconds=60, position=Vector(0, 0),
             *, allow_missing_current=False, obstacles=(), weather_policy: WeatherPolicy | None = None,
             forecast_policy: ForecastPolicy | None = None, clock: Clock | None = None):
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Starttid måste ha tidszon")
    if not isfinite(duration) or duration < 0 or not isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("Ogiltig varaktighet eller steglängd")
    if not all(isfinite(v) for v in (position.east, position.north)):
        raise ValueError("Ogiltig startposition")
    if duration > 0 and (timedelta(seconds=step_seconds).total_seconds() == 0 or
                         timedelta(seconds=duration).total_seconds() == 0):
        raise ValueError("Tidssteg och varaktighet måste vara minst en mikrosekund")
    planning_time = capture_planning_time(clock, forecast_policy)
    time = start.astimezone(timezone.utc)
    obstacles = tuple(obstacles)
    check_segment(position, position, obstacles)
    remaining = duration
    steps = []
    while remaining > 0:
        dt = min(step_seconds, remaining)
        first = evaluate(boat, environment, position, time, allow_missing_current, weather_policy, forecast_policy, planning_time)
        dt, middle, end = forecast_step(
            first, position, time, dt,
            lambda p, t: evaluate(boat, environment, p, t, allow_missing_current, weather_policy, forecast_policy, planning_time))
        check_segment(position, end, obstacles)
        segment_check = check_forecast_segment(environment, position, time, end, time+timedelta(seconds=dt), weather_policy)
        position = end
        time += timedelta(seconds=dt)
        steps.append(Step(first, middle, position, time, segment_check))
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
    comfort_exposure: float | None = None
    weather_status: str = "not_requested"
    comfort_model: str | None = None
    weather_policy: WeatherPolicy | None = None
    forecast_policy: ForecastPolicy | None = None
    planning_time: datetime | None = None
    forecast_status: str = "not_requested"
    destination_reached: bool = False
    arrival_checked_time: datetime | None = None
    arrival_weather_status: str = "not_requested"
    arrival_observation: Conditions | None = None
    weather_verification_scope: str = WEATHER_VERIFICATION_SCOPE
    forecast_support_scope: str = "Kontrollerat vid uppslag; inget kontinuerligt datastöd verifierat."
    weather_segment_status: str = "not_requested"
    weather_segment_failure: WeatherSegmentCheck | None = None


def compensated_evaluation(boat: BoatPerformance, direction, environment, position, time,
                           min_progress_m_s, weather_policy=None, forecast_policy=None, planning_time=None):
    weather = environment.evaluate(position, time)
    if forecast_policy is not None:
        forecast_policy.check(weather, planning_time)
    if weather_policy is not None:
        weather_policy.check(weather, time)
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
                   boat_assumptions=boat.assumptions, weather_checked=weather_policy is not None,
                   comfort_rate_synthetic=(synthetic_comfort_rate(weather.waves, water.course)
                                           if weather_policy is not None else None),
                   issued_at=weather.issued_at, forecast_checked=forecast_policy is not None, planning_time=planning_time)


def sail_to_target(environment: Environment, start, target: Vector, *, speed_knots=5,
                   position=Vector(0, 0), step_seconds=60, max_seconds=86400,
                   tolerance_m=0.01, min_progress_m_s=0.01, max_steps=100000,
                   obstacles=(), boat: BoatPerformance | None = None,
                   weather_policy: WeatherPolicy | None = None,
                   forecast_policy: ForecastPolicy | None = None, clock: Clock | None = None):
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
    planning_time = capture_planning_time(clock, forecast_policy)
    boat = boat if boat is not None else ConstantBoat(speed_knots=speed_knots, leeway=0)
    start = start.astimezone(timezone.utc)
    time, elapsed, steps = start, 0.0, []
    exposure = 0.0 if weather_policy is not None else None
    offset = target - position
    distance = offset.speed
    direction = offset.scaled(1 / distance) if distance else Vector(0, 0)

    arrival_checked_time, arrival_weather_status, arrival_observation = None, "not_requested", None
    segment_failure = None
    segment_capable = weather_policy is not None and getattr(environment, 'certify_weather_segment', None) is not None

    def result(status, reason=""):
        return Voyage(status, reason, tuple(steps), position, elapsed,
                      elapsed if status == "arrived" else None, target, tolerance_m, boat.assumptions, exposure,
                      (("passed_segments_and_arrival" if segment_capable else "passed_at_samples") if status == "arrived" else "incomplete")
                      if weather_policy is not None else "not_requested",
                      comfort_model=COMFORT_MODEL if weather_policy is not None else None,
                      weather_policy=weather_policy, forecast_policy=forecast_policy, planning_time=planning_time,
                      forecast_status=("passed_at_samples_and_arrival" if status == "arrived" else "incomplete")
                      if forecast_policy is not None else "not_requested",
                      destination_reached=(target - position).speed <= tolerance_m,
                      arrival_checked_time=arrival_checked_time, arrival_weather_status=arrival_weather_status,
                      arrival_observation=arrival_observation,
                      weather_verification_scope=SEGMENT_WEATHER_SCOPE if segment_capable else WEATHER_VERIFICATION_SCOPE,
                      weather_segment_status=(segment_failure.status if segment_failure else
                                              ('verified' if steps else 'not_applicable') if status == 'arrived' else 'incomplete')
                      if segment_capable else ('not_available' if weather_policy is not None else 'not_requested'),
                      weather_segment_failure=segment_failure,
                      forecast_support_scope=(
                          "Hela accepterade integrerade segment: datastöd för vind/ström/vågor; hårda vädergränser certifieras separat."
                          if weather_policy is not None else
                          "Hela accepterade integrerade segment: strömmens datastöd; övriga produkter endast vid uppslag.")
                      if getattr(environment, 'validate_segment', None) is not None else
                      "Kontrollerat vid uppslag; inget kontinuerligt datastöd verifierat.")

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
                                           position, time, min_progress_m_s, weather_policy, forecast_policy, planning_time)
            remaining = (target - position).dot(direction)
            # Startfarten begränsar predikterad mittpunkt till före målet.
            dt = min(step_seconds, max_seconds - elapsed,
                     remaining / first.ground.dot(direction))

            def trial(seconds):
                return forecast_step(
                    first, position, time, seconds,
                    lambda p, t: compensated_evaluation(
                        boat, direction, environment, p, t, min_progress_m_s, weather_policy, forecast_policy, planning_time))

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
            segment_check = check_forecast_segment(environment, position, time, end,
                                   start+timedelta(seconds=elapsed+dt), weather_policy)
        except ObstacleCollision as exc:
            return result("blocked", str(exc))
        except SegmentWeatherExceeded as exc:
            segment_failure = exc.check
            return result("weather_limit", str(exc))
        except SegmentWeatherUnverified as exc:
            segment_failure = exc.check
            return result('data_unavailable' if exc.check.failure_kind == 'data_unavailable' else 'weather_unverified', str(exc))
        except WeatherLimitExceeded as exc:
            return result("weather_limit", str(exc))
        except CourseUnavailable as exc:
            return result("infeasible", str(exc))
        except ValueError as exc:
            return result("data_unavailable", str(exc))
        if exposure is not None:
            increment = dt * middle.comfort_rate_synthetic
            if not isfinite(exposure + increment):
                return result("data_unavailable", "Syntetisk komfortexponering är ogiltig")
            exposure += increment
        elapsed += dt
        time = start + timedelta(seconds=elapsed)
        steps.append(Step(first, middle, end, time, segment_check))
        position = end
    # Completing movement does not verify destination weather. Query ACTUAL
    # end position/time, including zero-distance legs and exact validity boundaries.
    if weather_policy is not None or forecast_policy is not None:
        arrival_checked_time = time
        try:
            observation = environment.evaluate(position, time)
            if forecast_policy is not None:
                forecast_policy.check(observation, planning_time)
            if weather_policy is not None:
                weather_policy.check(observation, time)
                arrival_observation = observation
                arrival_weather_status = "passed_at_arrival"
        except WeatherLimitExceeded as exc:
            arrival_weather_status = "weather_limit"
            return result("weather_limit", "Ankomstkontroll: " + str(exc))
        except ValueError as exc:
            arrival_weather_status = "data_unavailable"
            return result("data_unavailable", "Ankomstkontroll: " + str(exc))
    return result("arrived")
