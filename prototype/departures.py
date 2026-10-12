"""Bounded explicit departure comparison; no forecast fetching or automatic search."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from .forecast import Clock, FixedClock, utc_time
from .model import ConstantBoat
from .routes import RouteCandidate, RouteComparison, RouteResult, compare_routes


@dataclass(frozen=True)
class DepartureResult:
    departure_time: datetime
    routes: RouteComparison


@dataclass(frozen=True)
class DepartureComparison:
    status: str
    departures: tuple[DepartureResult, ...]
    planning_time: datetime
    shortest_travel: RouteResult | None
    earliest_arrival: RouteResult | None
    selection_criterion: str | None
    selected: RouteResult | None
    scope: str = "Endast angivna avgångstider och kompletta kandidatrutter; ingen global optimalitet."


def compare_departures(environment, departures, target, candidates, *, clock: Clock,
                       max_departures=24, max_candidates=100,
                       selection_criterion=None, **route_options):
    """Reuse identical inputs; ties follow supplied departure and route order.

    The environment and boat must remain unchanged throughout this synchronous
    call. The caller supplies a frozen forecast dataset, never a live fetcher.
    Selection is optional and explicitly either duration or arrival time.
    All route controls (including comfort allowance) apply equally per departure.
    """
    if selection_criterion not in (None, 'shortest_travel_time', 'earliest_arrival'):
        raise ValueError("Okänt urvalskriterium för avgång")
    for limit in (max_departures, max_candidates):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("Sökgränser måste vara positiva heltal")
    times = []
    for value in departures:
        if len(times) >= max_departures:
            raise ValueError("För många avgångstider")
        instant = utc_time(value, 'Avgångstid')
        if instant in times:
            raise ValueError("Avgångstider måste vara unika")
        times.append(instant)
    if not times:
        raise ValueError("Minst en explicit avgångstid krävs")
    routes = []
    for candidate in candidates:
        if len(routes) >= max_candidates:
            raise ValueError("För många kandidatrutter")
        if not isinstance(candidate, RouteCandidate):
            raise ValueError("Explicit kandidatrutt krävs")
        routes.append(candidate)
    if not routes:
        raise ValueError("Minst en explicit kandidatrutt krävs")
    # Materialize one-shot inputs once, before any simulation.
    options = dict(route_options)
    options['obstacles'] = tuple(options.get('obstacles', ()))
    if options.get('boat') is None:
        speed = options.get('speed_knots', 5)
        if not isfinite(speed) or speed <= 0:
            raise ValueError("Båtfarten måste vara finit och positiv")
        options['boat'] = ConstantBoat(speed)
    if clock is None:
        raise ValueError("Avgångsjämförelse kräver en explicit planeringsklocka")
    planning_time = utc_time(clock.now(), 'Planeringstid')
    frozen_clock = FixedClock(planning_time)
    results = tuple(DepartureResult(time, compare_routes(
        environment, time, target, tuple(routes), clock=frozen_clock,
        max_candidates=max_candidates, **options)) for time in times)
    feasible = [row.routes.fastest for row in results if row.routes.fastest is not None]
    shortest = min(feasible, key=lambda r: r.travel_seconds) if feasible else None
    earliest = min(feasible, key=lambda r: r.arrival_time) if feasible else None
    selected = {'shortest_travel_time': shortest, 'earliest_arrival': earliest}.get(selection_criterion)
    return DepartureComparison('compared' if feasible else 'no_feasible_departure',
                               results, planning_time, shortest, earliest,
                               selection_criterion, selected)
