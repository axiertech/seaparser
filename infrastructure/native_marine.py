"""Frozen native geographic products emitted by CopernicusMarineAdapter.

No transport or normalization adapter. Point interpolation uses each product's
own geographic axes. Whole-segment support uses a conservative whole-disk box,
not sampled positions or a separable approximation of the projected grid.
"""
from dataclasses import dataclass,field
from datetime import datetime
from fractions import Fraction
from math import atan2,cos,degrees,hypot,isfinite,nextafter,radians

from infrastructure.land import INVERSE
from prototype.environment import Conditions,WaveData
from prototype.model import Vector
from prototype.forecast import utc_time
from prototype.forecast_data import DataUnavailable,axis_cell
from prototype.forecast_metadata import ProductMetadata
from prototype.segment_weather import CellWeatherBound,WeatherSegmentCheck,WeatherWitness,MAX_WEATHER_CELLS

ORIGIN=(57.633,11.605)
MIN_CURVATURE_RADIUS_M=6_300_000.0
GEOGRAPHIC_SUPPORT_GUARD_M=1.0


def disk_geographic_bounds(radius_m):
    """Enclose WGS84 geodesics of length <= r from the Vinga AEQD origin.

    WGS84 M>=a(1-e²)>6.3e6 and N>=a>6.3e6 everywhere. From the
    surface metric, |dphi|<=ds/M and |dlambda|<=ds/(N cos(phi)).
    First bound latitude, then longitude with the smallest cosine in that
    latitude range. This bounds entire geodesics, not just boundary samples.
    One metre is reserved for numerical mapping; angular bounds round outward.
    This is a geometric interpolation model, not source/datum qualification.
    """
    if type(radius_m) not in (float,int) or not isfinite(radius_m) or not 0<radius_m<=5000:
        raise ValueError('Bounded positive native-geometry radius <=5000 m required')
    distance=radius_m+GEOGRAPHIC_SUPPORT_GUARD_M
    angular=nextafter(distance/MIN_CURVATURE_RADIUS_M,float('inf'))
    latitude_delta=nextafter(degrees(angular),float('inf'))
    latitude_max=nextafter(radians(abs(ORIGIN[0])+latitude_delta),float('inf'))
    cosine=nextafter(cos(latitude_max),0)
    longitude_delta=nextafter(degrees(angular/cosine),float('inf'))
    return (nextafter(ORIGIN[1]-longitude_delta,-float('inf')),
            nextafter(ORIGIN[0]-latitude_delta,-float('inf')),
            nextafter(ORIGIN[1]+longitude_delta,float('inf')),
            nextafter(ORIGIN[0]+latitude_delta,float('inf')))


def lerp(a,b,f):
    if a==b or f==0:return a
    if f==1:return b
    return max(min(a,b),min(max(a,b),(1-f)*a+f*b))


@dataclass(frozen=True)
class NativeMarineProduct:
    metadata: ProductMetadata
    longitude: tuple[float,...]
    latitude: tuple[float,...]
    times: tuple[datetime,...]
    values: tuple
    support_radius_m: float
    geographic_bounds: tuple=field(init=False)
    support_nodes: tuple=field(init=False)

    def __post_init__(self):
        bounds=disk_geographic_bounds(self.support_radius_m)
        object.__setattr__(self,'geographic_bounds',bounds)
        if self.metadata.product not in ('waves','current') or (self.metadata.coverage.origin_latitude,self.metadata.coverage.origin_longitude)!=ORIGIN:
            raise ValueError('Known Vinga marine product required')
        c=self.metadata.coverage;r=self.support_radius_m
        if (c.min_east_m,c.min_north_m,c.max_east_m,c.max_north_m)!=(-r,-r,r,r):
            raise ValueError('Native metadata must explicitly enclose its configured disk')
        for name,lower,upper in (('longitude',-180,180),('latitude',-90,90)):
            axis=tuple(getattr(self,name))
            if (not 2<=len(axis)<=64 or any(type(v) not in (float,int) or not isfinite(v) or not lower<=v<=upper for v in axis)
                    or any(a>=b for a,b in zip(axis,axis[1:]))):
                raise ValueError('Finite ordered bounded native geographic axes required')
            object.__setattr__(self,name,axis)
        if not (self.longitude[0]<=bounds[0]<bounds[2]<=self.longitude[-1]
                and self.latitude[0]<=bounds[1]<bounds[3]<=self.latitude[-1]):
            raise DataUnavailable('Own native grid does not enclose the entire guarded disk')
        times=tuple(utc_time(t,'Native time') for t in self.times)
        if (not 2<=len(times)<=25 or any((b-a).total_seconds()!=3600 for a,b in zip(times,times[1:]))
                or self.metadata.valid_from!=times[0] or self.metadata.valid_until!=times[-1]):
            raise ValueError('Exact bounded hourly native time support required')
        object.__setattr__(self,'times',times)
        if not isinstance(self.values,(tuple,list)) or len(self.values)!=len(times):raise ValueError('Bounded native planes required')
        planes=[]
        for plane in self.values:
            if not isinstance(plane,(tuple,list)) or len(plane)!=len(self.latitude):raise ValueError('Bounded native rows required')
            rows=[]
            for row in plane:
                if not isinstance(row,(tuple,list)) or len(row)!=len(self.longitude):raise ValueError('Bounded native columns required')
                nodes=[]
                for node in row:
                    if node is not None:
                        node=tuple(node)
                        if len(node)!=len(self.metadata.units) or any(type(v) not in (int,float) or not isfinite(v) for v in node):
                            raise ValueError('Finite normalized native components required')
                        if self.metadata.product=='waves' and (node[0]<0 or node[1]<=0 or abs(hypot(node[2],node[3])-1)>1e-12):
                            raise ValueError('Physical wave components required')
                    nodes.append(node)
                if len(nodes)!=len(self.longitude):raise ValueError('Native longitude shape mismatch')
                rows.append(tuple(nodes))
            if len(rows)!=len(self.latitude):raise ValueError('Native latitude shape mismatch')
            planes.append(tuple(rows))
        if len(planes)!=len(times):raise ValueError('Native time shape mismatch')
        object.__setattr__(self,'values',tuple(planes))
        xs=[i for i in range(len(self.longitude)-1) if self.longitude[i]<=bounds[2] and self.longitude[i+1]>=bounds[0]]
        ys=[j for j in range(len(self.latitude)-1) if self.latitude[j]<=bounds[3] and self.latitude[j+1]>=bounds[1]]
        nodes=tuple(sorted({(j+dy,i+dx) for j in ys for i in xs for dy in (0,1) for dx in (0,1)}))
        object.__setattr__(self,'support_nodes',nodes)

    def _position(self,position):
        if not all(isfinite(v) for v in (position.east,position.north)) or position.speed>self.support_radius_m:
            raise DataUnavailable('Position outside native product disk')

    def _times(self,start,end):
        start,end=utc_time(start,'Segment start'),utc_time(end,'Segment end')
        if not self.times[0]<=start<self.times[-1] or not start<=end<=self.times[-1]:
            raise DataUnavailable('Segment outside native time support')
        return tuple(k for k in range(len(self.times)-1) if self.times[k]<=end and self.times[k+1]>=start)

    def segment_nodes(self,start,start_time,end,end_time):
        self._position(start);self._position(end)
        # A disk is convex: the whole affine local segment remains in it.
        intervals=self._times(start_time,end_time)
        if len(intervals)*len(self.support_nodes)>MAX_WEATHER_CELLS:raise DataUnavailable('Native support work budget exceeded')
        nodes=tuple(self.values[k+dt][j][i] for k in intervals for dt in (0,1) for j,i in self.support_nodes)
        if any(n is None for n in nodes):raise DataUnavailable('Missing own native support node in whole-disk/time envelope')
        return nodes

    def validate_segment(self,start,start_time,end,end_time):
        self.segment_nodes(start,start_time,end,end_time)

    def interpolate(self,position,time):
        self._position(position);time=utc_time(time,'Native lookup')
        if not self.times[0]<=time<self.times[-1]:raise DataUnavailable('Native validity end is exclusive')
        lon,lat=INVERSE.transform(position.east,position.north,errcheck=True)
        if not self.geographic_bounds[0]<=lon<=self.geographic_bounds[2] or not self.geographic_bounds[1]<=lat<=self.geographic_bounds[3]:
            raise DataUnavailable('Geographic transform left proven support envelope')
        i,fx=axis_cell(self.longitude,lon);j,fy=axis_cell(self.latitude,lat);k,ft=axis_cell(self.times,time)
        nodes=[[[self.values[k+dt][j+dy][i+dx] for dx in (0,1)] for dy in (0,1)] for dt in (0,1)]
        if any(n is None for plane in nodes for row in plane for n in row):raise DataUnavailable('Missing native interpolation corner')
        result=[]
        for component in range(len(self.metadata.units)):
            planes=[]
            for plane in nodes:
                rows=[lerp(row[0][component],row[1][component],fx) for row in plane]
                planes.append(lerp(rows[0],rows[1],fy))
            result.append(lerp(planes[0],planes[1],ft))
        return tuple(result)


@dataclass(frozen=True)
class NativeMarineDataset:
    dataset_id: str
    version: str
    products: tuple[NativeMarineProduct,...]

    def __post_init__(self):
        products=tuple(self.products)
        if (not all(isinstance(v,str) and v.strip() for v in (self.dataset_id,self.version)) or len(products)!=2 or any(type(p) is not NativeMarineProduct for p in products)
                or {p.metadata.product for p in products}!={'current','waves'} or products[0].times!=products[1].times
                or products[0].support_radius_m!=products[1].support_radius_m):
            raise ValueError('One frozen current/wave pair with common explicit support required')
        object.__setattr__(self,'products',products)

    @property
    def product_metadata(self):return tuple(p.metadata for p in self.products)

    def validate_segment(self,start,start_time,end,end_time,*,required_products=('current','waves')):
        by_name={p.metadata.product:p for p in self.products}
        for name in required_products:
            if name not in by_name:raise DataUnavailable('Native product missing: '+name)
            by_name[name].validate_segment(start,start_time,end,end_time)

    def evaluate(self,position,time):
        data={};meta={p.metadata.product:p.metadata for p in self.products};reasons=['wind: produkt saknas i underlaget']
        for p in self.products:
            try:data[p.metadata.product]=p.interpolate(position,time)
            except ValueError as e:reasons.append(p.metadata.product+': '+str(e))
        cm,wm=meta['current'],meta['waves'];wave=data.get('waves');waves=None
        if wave is not None:
            if hypot(wave[2],wave[3])<1e-12:reasons.append('Undefined interpolated wave bearing')
            else:waves=WaveData(wave[0],wave[1],degrees(atan2(wave[2],wave[3]))%360,wm.valid_from,wm.valid_until,
                                wm.source,wm.version,issued_at=wm.issued_at,metadata=wm)
        return Conditions(Vector(*data['current']) if 'current' in data else None,reason='; '.join(reasons),source=cm.source,
            version=cm.version,valid_from=cm.valid_from,valid_until=cm.valid_until,issued_at=cm.issued_at,waves=waves,
            current_metadata=cm,waves_metadata=wm,dataset_id=self.dataset_id,dataset_version=self.version)

    def certify_waves_segment(self,start,start_time,end,end_time,policy):
        try:
            self.validate_segment(start,start_time,end,end_time)
            waves=next(p for p in self.products if p.metadata.product=='waves')
            maximum=max(n[0] for n in waves.segment_nodes(start,start_time,end,end_time))
            passed=Fraction(maximum)<=Fraction(policy.max_wave_height_m)
            bound=CellWeatherBound('waves',(-1,-1,-1),policy.max_wave_height_m,'verified' if passed else 'unverified',
                wave_height_upper_m=maximum,reason='Whole guarded disk and all touched native time cells')
            if passed:return WeatherSegmentCheck('verified',method='native-geographic-disk-envelope-v1',bounds=(bound,))
            for f in (0,.5,1):
                when=start_time+(end_time-start_time)*f
                if when>=waves.times[-1]:continue
                point=start+(end-start).scaled(f);value=waves.interpolate(point,when)[0]
                if Fraction(value)>Fraction(policy.max_wave_height_m):
                    return WeatherSegmentCheck('exceeded','Native wave limit exceeded',bounds=(bound,),
                        witness=WeatherWitness('waves',point,when,policy.max_wave_height_m,wave_height_m=value))
            return WeatherSegmentCheck('unverified','Conservative native Hs envelope cannot prove limit',bounds=(bound,),failure_kind='bounds_inconclusive')
        except ValueError as e:return WeatherSegmentCheck('unverified',str(e),failure_kind='data_unavailable')
