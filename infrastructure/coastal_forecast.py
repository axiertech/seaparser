"""Materialized coastal development estimates; no transport during simulation.

Whole land segments remain hard constraints. Source envelopes bound selected
weather values, while explicit support witnesses and a configured regional
coordinate enclosure retain uncertainty. This class NEVER certifies weather.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import atan2,degrees
from functools import lru_cache
import numpy as np

from infrastructure.land import INVERSE
from infrastructure.motion_frame import RegionalAeqdMotionFrame,SwedishCoastAeqdMotionFrame
from prototype.environment import Conditions,WaveData
from prototype.forecast_data import DataUnavailable
from prototype.obstacles import ObstacleCollision


@dataclass(frozen=True)
class CoastalObstacle:
    water: object
    margin_m: float
    name: str='OSM coastal land / acquisition boundary; depth unknown'

    def intersects(self,start,end):return not self.water.clear(start,end,self.margin_m)


class CoastalForecast:
    def __init__(self,wind,current,waves,metadata,water,policy,*,margin_m=10,radius_m=120000,profile="vinga-uddevalla"):
        self.wind=wind;self.current=current;self.waves=waves;self.water=water;self.policy=policy
        self.product_metadata=tuple(metadata);self.margin_m=margin_m;self.frame=(SwedishCoastAeqdMotionFrame if profile=="trelleborg-stromstad" else RegionalAeqdMotionFrame)(radius_m)
        self.dataset_id=profile+'-real-coastal-estimates';self.version='20261018-water-path-v1'
        self.start=max(m.valid_from for m in metadata);self.end=min(m.valid_until for m in metadata)
        self.issued=min(m.issued_at for m in metadata)
        self.wind_components=tuple(float(np.nanmax(np.abs(wind.values[...,i]))) for i in (0,1))
        self.wind_squared_bound=sum((Fraction(v)**2 for v in self.wind_components),Fraction())
        self.wave_height_bound=float(np.nanmax(waves.values[...,0]))

    def position_rate(self,position,velocity):return self.frame.position_rate(position,velocity)
    def physical_direction(self,position,direction):return self.frame.physical_direction(position,direction)

    @lru_cache(maxsize=32768)
    def samples(self,position,when):
        if not self.start<=when<self.end:raise DataUnavailable('Outside frozen common coastal validity')
        self.frame.matrix(position)
        if not self.water.clear(position,position,self.margin_m):raise ObstacleCollision('Point touches coastal land/margin or acquisition boundary')
        w,wr=self.wind.sample(position,when);c,cr=self.current.sample(position,when);h,hr=self.waves.sample(position,when)
        return w,c,h,(*wr,*cr,*hr)

    @lru_cache(maxsize=32768)
    def evaluate(self,position,when):
        from prototype.model import Vector
        w,c,h,records=self.samples(position,when);wm,cm,hm=self.product_metadata
        waves=WaveData(h[0],h[1],degrees(atan2(h[2],h[3]))%360,self.start,self.end,
            source=hm.source,version=hm.version,issued_at=hm.issued_at,metadata=hm)
        return Conditions(Vector(*c),'High uncertainty: explicit coastal estimates' if records else 'Development source assumptions',
            self.dataset_id,self.version,Vector(*w),self.start,self.end,waves=waves,issued_at=self.issued,
            wind_metadata=wm,current_metadata=cm,waves_metadata=hm,dataset_id=self.dataset_id,dataset_version=self.version)

    def validate_segment(self,start,start_time,end,end_time,*,required_products=('current','wind','waves')):
        if not self.start<=start_time<=end_time<self.end:raise DataUnavailable('Segment leaves common coastal validity')
        if not self.water.clear(start,end,self.margin_m):raise DataUnavailable('Whole coastal segment crosses land/margin')
        length=(end-start).speed
        if length>1000:raise DataUnavailable('Coastal support model requires integrated segments <=1000 m')
        middle=(start+end).scaled(.5);when=start_time+(end_time-start_time)*.5
        # This explicit development assumption encloses the native coordinate
        # image by 2*half-length +2 m. It is separately reported, not certified.
        lon,lat=INVERSE.transform(middle.east,middle.north,errcheck=True)
        x,y=self.wind.native._xy(lon,lat);guard=length+2
        sample=self.wind.native.sample
        if not (float(sample.x_m[0])<=x-guard<=x+guard<=float(sample.x_m[-1])
                and float(sample.y_m[0])<=y-guard<=y+guard<=float(sample.y_m[-1])):
            raise DataUnavailable('Whole regional wind enclosure leaves native source grid')
        i0=max(0,int(np.searchsorted(np.array(sample.x_m,dtype=float),x-guard))-1)
        i1=min(len(sample.x_m),int(np.searchsorted(np.array(sample.x_m,dtype=float),x+guard))+1)
        j0=max(0,int(np.searchsorted(np.array(sample.y_m,dtype=float),y-guard))-1)
        j1=min(len(sample.y_m),int(np.searchsorted(np.array(sample.y_m,dtype=float),y+guard))+1)
        k0=max(0,int(np.searchsorted(self.wind.epochs,start_time.timestamp(),side='right'))-1)
        k1=min(len(sample.times),int(np.searchsorted(self.wind.epochs,end_time.timestamp()))+1)
        if not self.wind.valid[k0:k1,j0:j1,i0:i1].all():raise DataUnavailable('Wind enclosure touches missing native source values')
        if self.wind_squared_bound>Fraction(self.policy.max_wind_m_s)**2:
            raise DataUnavailable('Conservative source wind envelope cannot establish selected model limit; estimate not verified')
        if self.wave_height_bound>self.policy.max_wave_height_m:
            raise DataUnavailable('Conservative source wave envelope cannot establish selected model limit; estimate not verified')
        # A source reachable from the midpoint stays reachable from every point
        # of this closed land-free segment via that midpoint. The length/time
        # slack below proves existence of a permitted marine support witness.
        for field in (self.current,self.waves):
            _,records=field.sample(middle,when)
            if not records:_,records=field.reserve(middle,when)
            for r in records:
                p=field.policies[r.variable]
                if (r.distance_m+length/2>p.max_distance_m or
                        max(abs((r.source_time-t).total_seconds()) for t in (start_time,end_time))>p.max_time_offset_seconds):
                    raise DataUnavailable('Whole segment lacks configured marine distance/time reserve slack')
        for p,t in ((start,start_time),(middle,when),(end,end_time)):
            self.policy.check(self.evaluate(p,t),t)
