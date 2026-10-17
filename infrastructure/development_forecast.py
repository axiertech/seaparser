"""Frozen real-source development composition; assumptions never certify sources.

No file, HTTP or SQL access. Native wind is sampled on its source grid; marine
support/masks are checked on each own grid. Only configured metadata gaps may
be conditionally accepted by the application composition root.
"""
from dataclasses import dataclass, field, replace
from fractions import Fraction
from math import isfinite

from infrastructure.met_wind_segments import NativeMetWind, VingaRouteSegment, direction_from_to_components
from infrastructure.native_wind import NativeWindSample
from infrastructure.native_marine import NativeMarineDataset
from infrastructure.land import to_geo
from prototype.forecast_data import ForecastDataset, DataUnavailable
from prototype.forecast_metadata import ProductMetadata
from prototype.model import Vector
from prototype.segment_weather import (WeatherSegmentCheck, CellWeatherBound, WeatherWitness,
                                       certify_weather_segment)


@dataclass(frozen=True)
class DevelopmentForecast:
    dataset_id: str
    version: str
    wind: NativeWindSample
    marine: ForecastDataset | NativeMarineDataset
    wind_metadata: ProductMetadata
    assumptions: tuple[tuple[str,str], ...]
    support_radius_m: float
    component_bounds: tuple = field(init=False)

    def __post_init__(self):
        if not isfinite(self.support_radius_m) or not 0 < self.support_radius_m <= 900:
            raise ValueError('Utvecklingsområdet måste ligga inom 900 m')
        native=NativeMetWind(self.wind)
        support=native.bound_segment(VingaRouteSegment(Vector(-self.support_radius_m,0),
                    Vector(self.support_radius_m,0),self.wind.times[0],self.wind.times[-1]),
                    max_wind_m_s=100000)
        if support['status'] != 'within_interpolation_model':
            raise DataUnavailable('Native vindgrid täcker inte hela utvecklingsområdet')
        vectors=[direction_from_to_components(float(speed),float(direction))
                 for speeds,directions in zip(self.wind.speed_m_s,self.wind.direction_from_degrees,strict=True)
                 for row,drow in zip(speeds,directions,strict=True)
                 for speed,direction in zip(row,drow,strict=True)]
        object.__setattr__(self,'component_bounds',tuple((min(getattr(v,c) for v in vectors),
                         max(getattr(v,c) for v in vectors)) for c in ('east','north')))

    @property
    def product_metadata(self):
        return (self.wind_metadata,*self.marine.product_metadata)

    def evaluate(self,position,time):
        data=self.marine.evaluate(position,time)
        try:
            if position.speed > self.support_radius_m or not self.wind.times[0] <= time < self.wind.times[-1]:
                raise DataUnavailable('Utanför verkligt gemensamt vindstöd')
            value=NativeMetWind(self.wind).at(*to_geo(position),time)
            # Clamp roundoff to the real source component envelope used below.
            vector=Vector(*(max(low,min(high,v)) for v,(low,high) in
                            zip((value.east,value.north),self.component_bounds,strict=True)))
            return replace(data,wind=vector,wind_metadata=self.wind_metadata,
                           reason=data.reason.replace('wind: produkt saknas i underlaget','').strip('; '),
                           dataset_id=self.dataset_id,dataset_version=self.version)
        except ValueError as error:
            return replace(data,wind=None,wind_metadata=self.wind_metadata,reason=str(error))

    def validate_segment(self,start,start_time,end,end_time,*,required_products=('current','wind','waves')):
        self.marine.validate_segment(start,start_time,end,end_time,
                     required_products=tuple(n for n in required_products if n != 'wind'))
        if 'wind' in required_products and (max(start.speed,end.speed)>self.support_radius_m
                or not self.wind.times[0] <= start_time <= end_time <= self.wind.times[-1]):
            raise DataUnavailable('Segmentet lämnar verkligt native vindstöd')

    def certify_weather_segment(self,start,start_time,end,end_time,policy):
        try:
            self.validate_segment(start,start_time,end,end_time)
            waves=(self.marine.certify_waves_segment(start,start_time,end,end_time,policy)
                   if isinstance(self.marine,NativeMarineDataset) else
                   certify_weather_segment(self.marine,start,start_time,end,end_time,policy,weather_products=('waves',)))
            if waves.status != 'verified':
                return waves
            upper=sum((Fraction(max(abs(low),abs(high)))**2 for low,high in self.component_bounds),Fraction(0))
            bound=CellWeatherBound('wind',(-1,-1,-1),policy.max_wind_m_s,
                    'verified' if upper <= Fraction(policy.max_wind_m_s)**2 else 'unverified',
                    wind_abs_components_m_s=tuple(max(abs(a),abs(b)) for a,b in self.component_bounds),
                    wind_squared_upper=str(upper),reason='Native källnoders konservativa komponenthölje; villkorat av antaganden')
            if bound.status != 'verified':
                for f in (0,.5,1):
                    point=start+(end-start).scaled(f); when=start_time+(end_time-start_time)*f
                    if when >= self.wind.times[-1]:
                        continue
                    wind=self.evaluate(point,when).wind
                    if wind is not None and Fraction(wind.east)**2+Fraction(wind.north)**2 > Fraction(policy.max_wind_m_s)**2:
                        return WeatherSegmentCheck('exceeded','Vindgräns överskriden',bounds=(*waves.bounds,bound),
                            witness=WeatherWitness('wind',point,when,policy.max_wind_m_s,(wind.east,wind.north)))
                return WeatherSegmentCheck('unverified','Native vindhölje kan inte godkänna vald gräns',
                             bounds=(*waves.bounds,bound),failure_kind='bounds_inconclusive')
            return WeatherSegmentCheck('verified',method='native-wind-envelope-and-marine-grid-v1',bounds=(*waves.bounds,bound))
        except ValueError as error:
            return WeatherSegmentCheck('unverified',str(error),failure_kind='data_unavailable')
