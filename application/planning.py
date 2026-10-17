"""Reproducible offline planning with explicit immutable inputs and provenance."""
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from infrastructure.development_forecast import DevelopmentForecast
from hashlib import sha256
import json

from prototype.departures import compare_departures
from prototype.forecast import FixedClock, ForecastPolicy, utc_time
from prototype.forecast_data import ForecastDataset, MAX_SEGMENT_INTERVALS
from prototype.model import ConstantBoat, Vector
from prototype.obstacles import Rectangle
from prototype.polygon import Polygon
from prototype.presentation import export_departure_comparison
from prototype.routes import RouteCandidate
from prototype.sailing import PolarBoat
from prototype.weather import WeatherPolicy
from prototype.segment_weather import METHOD as WEATHER_SEGMENT_METHOD, MAX_WEATHER_CELLS

ALGORITHM_VERSION = 'explicit-candidates-midpoint-grid-weather-v3'
REPORT_SCHEMA_VERSION = 1


def canonical(data):
    """Stable UTF-8 representation; no NaN, secrets, transport or wall-clock reads."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=lambda value: str(value) if isinstance(value, Decimal) else value.isoformat())


def digest(data):
    return sha256(canonical(data).encode('utf-8')).hexdigest()


def bounded_tuple(values, limit, name):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError(f'{name}: positiv heltalsgräns krävs')
    result = []
    for value in values:
        if len(result) >= limit:
            raise ValueError(f'{name}: för många alternativ')
        result.append(value)
    return tuple(result)


@dataclass(frozen=True)
class PlanRequest:
    dataset: ForecastDataset | DevelopmentForecast
    planning_time: datetime
    departures: tuple[datetime, ...]
    target: Vector
    candidates: tuple[RouteCandidate, ...]
    weather_policy: WeatherPolicy
    forecast_policy: ForecastPolicy
    boat: ConstantBoat | PolarBoat = PolarBoat()
    position: Vector = Vector(0, 0)
    obstacles: tuple[Rectangle | Polygon, ...] = ()
    step_seconds: float = 10
    max_seconds: float = 86400
    max_steps: int = 100000
    tolerance_m: float = .01
    min_progress_m_s: float = .01
    max_comfort_extra_seconds: float = 40
    max_departures: int = 24
    max_candidates: int = 100
    max_waypoints: int = 32
    max_obstacles: int = 100
    selection_criterion: str | None = None

    def __post_init__(self):
        if (type(self.dataset) not in (ForecastDataset, DevelopmentForecast) or type(self.boat) not in (ConstantBoat, PolarBoat)
                or type(self.weather_policy) is not WeatherPolicy or type(self.forecast_policy) is not ForecastPolicy
                or type(self.target) is not Vector or type(self.position) is not Vector):
            raise ValueError('Planeringen kräver fryst dataset, känd fryst båtmodell, positioner och båda policyerna')
        object.__setattr__(self, 'planning_time', utc_time(self.planning_time, 'Planeringstid'))
        departures = bounded_tuple(self.departures, self.max_departures, 'Avgångar')
        object.__setattr__(self, 'departures', tuple(utc_time(t, 'Avgångstid') for t in departures))
        candidates = bounded_tuple(self.candidates, self.max_candidates, 'Rutter')
        obstacles = bounded_tuple(self.obstacles, self.max_obstacles, 'Hinder')
        if any(type(c) is not RouteCandidate for c in candidates) or any(type(o) not in (Rectangle, Polygon) for o in obstacles):
            raise ValueError('Endast frysta kandidatrutter och syntetiska rektangel-/polygonhinder stöds')
        object.__setattr__(self, 'candidates', candidates)
        object.__setattr__(self, 'obstacles', obstacles)


def run_plan(request: PlanRequest) -> str:
    """JSON report; input identity includes the entire dataset, not just its label.

    Only built-in immutable boat configurations currently have a provenance
    serializer; routing itself still accepts other BoatPerformance implementations.
    """
    comparison = compare_departures(
        request.dataset, request.departures, request.target, request.candidates,
        clock=FixedClock(request.planning_time), boat=request.boat, position=request.position,
        obstacles=request.obstacles, weather_policy=request.weather_policy,
        forecast_policy=request.forecast_policy, step_seconds=request.step_seconds,
        max_seconds=request.max_seconds, max_steps=request.max_steps,
        tolerance_m=request.tolerance_m, min_progress_m_s=request.min_progress_m_s,
        max_comfort_extra_seconds=request.max_comfort_extra_seconds,
        max_departures=request.max_departures, max_candidates=request.max_candidates,
        max_waypoints=request.max_waypoints, selection_criterion=request.selection_criterion)
    inputs = asdict(request)
    boat = {'model': type(request.boat).__name__, 'configuration': inputs['boat'],
            'assumptions': request.boat.assumptions}
    dataset = inputs['dataset']
    real=isinstance(request.dataset,DevelopmentForecast)
    algorithm_version='real-native-wind-marine-conditional-v1' if real else ALGORITHM_VERSION
    algorithm_settings = {'forecast_segment_interval_limit': MAX_SEGMENT_INTERVALS,
                          'weather_segment_method': 'native-wind-envelope-and-marine-grid-v1' if real else WEATHER_SEGMENT_METHOD,
                          'weather_certificate_cell_limit': MAX_WEATHER_CELLS}
    identity = {'algorithm_settings': algorithm_settings, 'schema_version': REPORT_SCHEMA_VERSION, 'algorithm_version': algorithm_version,
                'request': inputs, 'boat_model': boat['model']}
    parameters = {key: value for key, value in inputs.items() if key not in ('dataset', 'boat')}
    return canonical({
        'manifest': {'schema_version': REPORT_SCHEMA_VERSION, 'algorithm_version': algorithm_version,
                     'algorithm_settings': algorithm_settings,
                     'input_sha256': digest(identity), 'dataset_sha256': digest(dataset),
                     'boat_sha256': digest(boat), 'boat': boat, 'parameters': parameters,
                     'dataset_id': request.dataset.dataset_id, 'dataset_version': request.dataset.version,
                     'forecast_products': [asdict(m) | ({'issued_at_status':'assumed', 'metadata_status':'development_assumptions'}
                         if isinstance(request.dataset,DevelopmentForecast) else {}) for m in request.dataset.product_metadata],
                     **({'source_assumptions':dict(request.dataset.assumptions),
                         'source_qualification':'unverified','result_qualification':'conditional_on_assumptions'}
                         if isinstance(request.dataset,DevelopmentForecast) else {}),
                     'boat_data_estimated': True,
                     'limitations': 'Uppskattad båtmodell och lokalt plan; datastöd över integrerade segment, konservativ certifiering av hårda vind-/våggränser och separat ankomstkontroll; ingen navigationsprodukt.'},
        'comparison': json.loads(export_departure_comparison(comparison))})
