"""Reproducible offline planning with explicit immutable inputs and provenance."""
from dataclasses import asdict, dataclass
from datetime import datetime
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

ALGORITHM_VERSION = 'explicit-candidates-midpoint-grid-weather-v4'
# v4: the hashed identity no longer carries a duplicated top-level 'boat_model'
# key; the resolved name lives only in identity['request']['boat_model'].
REPORT_SCHEMA_VERSION = 2

BOAT_MODELS = ('sailboat', 'motorboat')

# Estimated motorboat cruise speed and leeway. These are documented assumptions,
# not measured data; the manifest marks them as estimated.
MOTORBOAT_CRUISE_KNOTS = 12
MOTORBOAT_LEEWAY = 0

# Boat class expected for each named model; used to reject contradictory requests.
BOAT_MODEL_TYPES = {'sailboat': PolarBoat, 'motorboat': ConstantBoat}


def boat_for_model(boat_model: str) -> ConstantBoat | PolarBoat:
    """Return the built-in boat profile for a named model.

    Args:
        boat_model: One of BOAT_MODELS, e.g. 'sailboat' or 'motorboat'.

    Returns:
        A frozen built-in boat configuration. The motorboat profile is an
        estimated constant-speed model, not measured data.

    Raises:
        ValueError: If the model name is unknown.
    """
    if boat_model == 'sailboat':
        return PolarBoat()
    if boat_model == 'motorboat':
        return ConstantBoat(speed_knots=MOTORBOAT_CRUISE_KNOTS, leeway=MOTORBOAT_LEEWAY)
    raise ValueError(f'Okänd båtmodell: {boat_model!r}; tillåtna: {", ".join(BOAT_MODELS)}')


def boat_model_for(boat: ConstantBoat | PolarBoat) -> str:
    """Return the model name matching a built-in boat configuration.

    Args:
        boat: A built-in boat configuration.

    Returns:
        The matching name from BOAT_MODELS.

    Raises:
        ValueError: If the boat type has no named model.
    """
    for name, boat_type in BOAT_MODEL_TYPES.items():
        if type(boat) is boat_type:
            return name
    raise ValueError(f'Okänd båttyp: {type(boat).__name__}')


def resolve_boat_model(boat_model: str | None, boat: ConstantBoat | PolarBoat) -> str:
    """Return a model name from BOAT_MODELS consistent with the boat profile.

    Args:
        boat_model: An explicit model name, or None to derive it from the profile.
        boat: A built-in boat configuration.

    Returns:
        The model name matching the profile. When boat_model is None the name is
        derived via boat_model_for(boat).

    Raises:
        ValueError: If boat_model names a model whose expected boat type does not
            match the supplied profile.
    """
    if boat_model is None:
        return boat_model_for(boat)
    if boat_model not in BOAT_MODELS:
        raise ValueError(f'Okänd båtmodell: {boat_model!r}; tillåtna: {", ".join(BOAT_MODELS)}')
    if type(boat) is not BOAT_MODEL_TYPES[boat_model]:
        raise ValueError(f'Båtmodellen {boat_model!r} kräver en '
                         f'{BOAT_MODEL_TYPES[boat_model].__name__}-profil, '
                         f'inte {type(boat).__name__}')
    return boat_model


def canonical(data):
    """Stable UTF-8 representation; no NaN, secrets, transport or wall-clock reads."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=lambda value: value.isoformat())


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
    dataset: ForecastDataset
    planning_time: datetime
    departures: tuple[datetime, ...]
    target: Vector
    candidates: tuple[RouteCandidate, ...]
    weather_policy: WeatherPolicy
    forecast_policy: ForecastPolicy
    boat: ConstantBoat | PolarBoat = PolarBoat()
    boat_model: str = 'sailboat'
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
        if (type(self.dataset) is not ForecastDataset or type(self.boat) not in (ConstantBoat, PolarBoat)
                or type(self.weather_policy) is not WeatherPolicy or type(self.forecast_policy) is not ForecastPolicy
                or type(self.target) is not Vector or type(self.position) is not Vector):
            raise ValueError('Planeringen kräver fryst dataset, känd fryst båtmodell, positioner och båda policyerna')
        if self.boat_model not in BOAT_MODELS:
            raise ValueError(f'Okänd båtmodell: {self.boat_model!r}; tillåtna: {", ".join(BOAT_MODELS)}')
        # A caller that only supplied a boat profile keeps the default
        # 'sailboat' label; derive the label from the profile instead of
        # silently mislabelling the manifest. Explicit contradictions fail.
        if self.boat_model == 'sailboat' and type(self.boat) is not PolarBoat:
            object.__setattr__(self, 'boat_model', boat_model_for(self.boat))
        else:
            object.__setattr__(self, 'boat_model', resolve_boat_model(self.boat_model, self.boat))
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
            'assumptions': request.boat.assumptions, 'boat_model': request.boat_model,
            'estimated': True,
            'estimation_note': 'Uppskattad båtmodell; inte uppmätta prestandadata.'}
    dataset = inputs['dataset']
    algorithm_settings = {'forecast_segment_interval_limit': MAX_SEGMENT_INTERVALS,
                          'weather_segment_method': WEATHER_SEGMENT_METHOD,
                          'weather_certificate_cell_limit': MAX_WEATHER_CELLS}
    identity = {'algorithm_settings': algorithm_settings, 'schema_version': REPORT_SCHEMA_VERSION, 'algorithm_version': ALGORITHM_VERSION,
                'request': inputs}
    parameters = {key: value for key, value in inputs.items() if key not in ('dataset', 'boat')}
    return canonical({
        'manifest': {'schema_version': REPORT_SCHEMA_VERSION, 'algorithm_version': ALGORITHM_VERSION,
                     'algorithm_settings': algorithm_settings,
                     'input_sha256': digest(identity), 'dataset_sha256': digest(dataset),
                     'boat_sha256': digest(boat), 'boat': boat, 'parameters': parameters,
                     'dataset_id': request.dataset.dataset_id, 'dataset_version': request.dataset.version,
                     'forecast_products': [asdict(m) for m in request.dataset.product_metadata],
                     'boat_data_estimated': True,
                     'limitations': 'Uppskattad båtmodell och lokalt plan; datastöd över integrerade segment, konservativ certifiering av hårda vind-/våggränser och separat ankomstkontroll; ingen navigationsprodukt.'},
        'comparison': json.loads(export_departure_comparison(comparison))})
