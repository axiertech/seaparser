"""Offline provider adapters for frozen POINT references, never regional extrapolation."""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite,sin,cos,radians
from typing import Protocol,Mapping
from prototype.forecast import utc_time,ForecastPolicy
from prototype.forecast_data import DataUnavailable


def timestamp(value):
    if not isinstance(value,str):
        raise ValueError('Explicit tidsmetadata krävs')
    return utc_time(datetime.fromisoformat(value),'Prognostid')


def vector(speed,bearing,*,from_direction=False):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in (speed,bearing)) or speed<0:
        raise ValueError('Ogiltiga fart-/riktningsdata')
    sign=-1 if from_direction else 1
    return (sign*speed*sin(radians(bearing)),sign*speed*cos(radians(bearing)))


@dataclass(frozen=True)
class PointForecast:
    provider: str
    product: str
    version: str
    retrieved_at: datetime
    issued_at: datetime | None
    issuance_basis: str
    updated_at: datetime | None
    position: tuple[float,float]
    times: tuple[datetime,...]
    values: tuple[tuple[float | None,...] | None,...]
    units: tuple[str,...]
    reference_frame: str
    source_sha256: str
    source_url: str
    license_url: str
    coverage_status: str='point-only; regional coverage unknown'

    def check_age(self,planning_time,max_age_seconds):
        planning_time=utc_time(planning_time,'Planeringstid')
        policy=ForecastPolicy(max_age_seconds)
        if self.issued_at is None:
            raise DataUnavailable('Utfärdandetid saknas; updated_at är inte modellens utfärdandetid')
        age=(planning_time-self.issued_at).total_seconds()
        if not 0<=age<=policy.max_age_seconds:
            raise DataUnavailable('Prognosen är gammal eller utfärdad efter planeringstidpunkten')

    def interpolate(self,position,time):
        if tuple(position)!=self.position:
            raise DataUnavailable('Punktdata får inte extrapoleras till Vinga-området')
        time=utc_time(time,'Uppslagstid')
        if not self.times[0]<=time<self.times[-1]:
            raise DataUnavailable('Utanför giltighet [från,till); ingen extrapolation')
        i=next(i for i in range(len(self.times)-1) if self.times[i]<=time<self.times[i+1])
        a,b=self.values[i:i+2]
        if a is None or b is None or any(v is None for v in (*a,*b)):
            raise DataUnavailable('Datalucka i tidsinterpolationsstödet')
        weight=(time-self.times[i]).total_seconds()/(self.times[i+1]-self.times[i]).total_seconds()
        return tuple(x+weight*(y-x) for x,y in zip(a,b))


class PointForecastAdapter(Protocol):
    def normalize(self,payload:Mapping[str,object],*,retrieved_at:datetime,source_url:str)->tuple[PointForecast,...]: ...


def record(payload,provider,product,retrieved_at,source_url,issued_at,basis,updated_at,times,values,units,frame):
    import json
    coordinates=payload['geometry']['coordinates'][:2]
    if (payload['geometry']['type']!='Point' or len(coordinates)!=2
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in coordinates)
            or not (-180<=coordinates[0]<=180 and -90<=coordinates[1]<=90)):
        raise ValueError('WGS84 punktgeometri krävs')
    if len(times)<2 or any(a>=b for a,b in zip(times,times[1:])):
        raise ValueError('Minst två strikt stigande giltighetstider krävs')
    retrieved_at=utc_time(retrieved_at,'Hämtningstid')
    identity=sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return PointForecast(provider,product,identity,
                         retrieved_at,issued_at,basis,updated_at,tuple(coordinates),tuple(times),tuple(values),tuple(units),frame,
                         identity,source_url,
                         'https://creativecommons.org/licenses/by/4.0/')


class SnowPointAdapter:
    """SMHI SNOW1gv1: createdTime=forecast creation, referenceTime=forecast start."""
    def normalize(self,payload,*,retrieved_at,source_url):
        issued=timestamp(payload.get('createdTime')); series=payload['timeSeries']
        times=[timestamp(s['time']) for s in series]
        values=[]
        for s in series:
            d=s['data']; speed=d.get('wind_speed'); bearing=d.get('wind_from_direction')
            values.append(None if speed is None or bearing is None else vector(speed,bearing,from_direction=True))
        return (record(payload,'SMHI SNOW1gv1','wind',retrieved_at,source_url,issued,'createdTime: forecast creation',None,times,values,
                       ('m/s','m/s'),'ground-to-true-east-north'),)


class MetOceanPointAdapter:
    """MET Oceanforecast 2.0: preserve unknown issuance and absent Tm02."""
    def normalize(self,payload,*,retrieved_at,source_url):
        properties=payload['properties'];meta=properties['meta'];series=properties['timeseries']
        times=[timestamp(s['time']) for s in series];current=[];waves=[]
        units=meta['units']
        expected={'sea_water_speed':'m/s','sea_water_to_direction':'degrees','sea_surface_wave_height':'m','sea_surface_wave_from_direction':'degrees'}
        if any(units.get(k)!=v for k,v in expected.items()):
            raise ValueError('Okända marina enheter')
        for s in series:
            d=s['data']['instant']['details'];speed=d.get('sea_water_speed'); bearing=d.get('sea_water_to_direction')
            current.append(None if speed is None or bearing is None else vector(speed,bearing))
            # Provider does not supply Tm02. Never invent a period or use zero.
            height=d.get('sea_surface_wave_height'); direction=d.get('sea_surface_wave_from_direction')
            if height is None or direction is None:
                waves.append(None)
            else:
                if not isinstance(height,(int,float)) or isinstance(height,bool) or not isfinite(height) or height<0:
                    raise ValueError('Ogiltig signifikant våghöjd')
                unit=vector(1,direction)
                waves.append((height,None,*unit))
        updated=timestamp(meta.get('updated_at'))
        return tuple(record(payload,'MET Norway Oceanforecast 2.0',kind,retrieved_at,source_url,None,'unknown; updated_at is latest data update',updated,
                            times,values,u,f) for kind,values,u,f in (
            ('current',current,('m/s','m/s'),'ground-to-true-east-north; depth unspecified by point API'),
            ('waves',waves,('m','s','1','1'),'ground-from-true-east-north-tm02; period missing')))
