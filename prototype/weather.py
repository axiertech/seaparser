"""Hard sample-level weather limits and unvalidated synthetic wave exposure."""
from dataclasses import dataclass
from math import isfinite, radians, sin


COMFORT_MODEL = "synthetic-wave-exposure-v1; ej validerat för verkliga båtrörelser"


class WeatherLimitExceeded(ValueError):
    """Absolute limits cannot be traded for time or comfort."""


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{name} saknas eller är ogiltigt')
    return value


def known_interval(start, end, time, name):
    if start is None or end is None:
        raise ValueError(f'{name}: explicit giltighetsintervall krävs')
    if not start <= time < end:
        raise ValueError(f'{name}: data saknas vid uppslagets tid')


def wave_values(waves):
    if waves is None:
        raise ValueError('Vågdata saknas')
    height = number(waves.height_m, 'Signifikant våghöjd')
    period = number(waves.period_seconds, 'Vågperiod')
    direction = number(waves.from_degrees, 'Vågornas från-riktning')
    if height < 0 or period <= 0:
        raise ValueError('Våghöjd måste vara icke-negativ och period positiv')
    return height, period, direction


def synthetic_comfort_rate(waves, heading_degrees):
    """Dimensionless rate: (Hs/1m)^2*(5s/T)^2*(1+sin(relative)^2)."""
    height, period, direction = wave_values(waves)
    heading = number(heading_degrees, 'Riktning genom vatten för komfort')
    relative = radians((direction - heading + 180) % 360 - 180)
    try:
        rate = height**2 * (5 / period)**2 * (1 + sin(relative)**2)
    except OverflowError:
        raise ValueError('Syntetiskt komfortmått kan inte beräknas') from None
    if not isfinite(rate):
        raise ValueError('Syntetiskt komfortmått kan inte beräknas')
    return rate


@dataclass(frozen=True)
class WeatherPolicy:
    max_wind_m_s: float
    max_wave_height_m: float
    wind_reference: str = 'ground'

    def __post_init__(self):
        if (number(self.max_wind_m_s, 'Vindgräns') < 0
                or number(self.max_wave_height_m, 'Våggräns') < 0
                or self.wind_reference != 'ground'):
            raise ValueError('Hårda gränser kräver icke-negativa värden och markrelativ vind')

    def check(self, weather, time):
        known_interval(weather.valid_from, weather.valid_until, time, 'Vind/ström')
        current = weather.current
        if current is None or not all(isfinite(v) for v in (current.east, current.north)):
            raise ValueError('Strömdata krävs med aktiverad väderpolicy; ingen fallback')
        wind = weather.wind
        if wind is None or not all(isfinite(v) for v in (wind.east, wind.north)):
            raise ValueError('Vinddata krävs för den hårda markrelativa gränsen')
        if weather.wind_reference == 'water':
            wind = wind + current
        if not isfinite(wind.speed):
            raise ValueError('Markrelativ vindstyrka är ogiltig')
        if wind.speed > self.max_wind_m_s:
            raise WeatherLimitExceeded(f'Hård vindgräns överskriden: {wind.speed:g} > {self.max_wind_m_s:g} m/s (markrelativ vind)')
        waves = weather.waves
        if waves is None:
            raise ValueError('Vågdata saknas')
        known_interval(waves.valid_from, waves.valid_until, time, 'Vågor')
        height = number(waves.height_m, 'Signifikant våghöjd')
        if height < 0:
            raise ValueError('Signifikant våghöjd är negativ')
        if height > self.max_wave_height_m:
            raise WeatherLimitExceeded(f'Hård våghöjdsgräns överskriden: {height:g} > {self.max_wave_height_m:g} m')
        wave_values(waves)  # Period and direction are necessary for both selections.
