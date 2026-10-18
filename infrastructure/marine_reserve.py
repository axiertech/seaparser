"""Explicit nearest valid marine reserve, constrained to visible connected water.

Normalized node components come from the existing Copernicus field adapter.
No transport, file access, hidden zero values or weather-limit certification.
"""
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from math import atan2,degrees,isfinite,hypot
from types import MappingProxyType
import numpy as np

from infrastructure.land import FORWARD,INVERSE
from prototype.forecast_data import axis_cell,DataUnavailable
from prototype.model import Vector
from prototype.forecast import utc_time


@dataclass(frozen=True)
class ReservePolicy:
    method: str='nearest_valid_water'
    max_distance_m: float=20000
    max_time_offset_seconds: float=21600
    time_weight_m_per_second: float=1
    water_path_spacing_m: float=250
    water_path_max_cells: int=30000
    water_path_max_expansions: int=10000
    water_path_max_sources: int=16
    water_path_margin_m: float=0

    def __post_init__(self):
        if self.method not in ('none','nearest_valid_water','nearest_valid_water_path') or any(type(v) not in (int,float) or not isfinite(v) or v<0 for v in (self.max_distance_m,self.max_time_offset_seconds,self.time_weight_m_per_second,self.water_path_margin_m)):
            raise ValueError('Explicit finite reserve policy required')
        if (type(self.water_path_spacing_m) not in (int,float) or not isfinite(self.water_path_spacing_m) or self.water_path_spacing_m<=0
                or any(type(v) is not int or v<=0 for v in (self.water_path_max_cells,self.water_path_max_expansions,self.water_path_max_sources))):
            raise ValueError('Explicit positive water path search budgets required')


@dataclass(frozen=True)
class DataEstimate:
    variable: str
    method: str
    source_longitude: float
    source_latitude: float
    source_time: datetime
    distance_m: float
    time_offset_seconds: float
    source_value: float
    uncertainty: str='high'
    direct_distance_m: float | None=None
    connection_waypoints: tuple=()
    connection_expansions: int=0
    connection_spacing_m: float | None=None
    source_search_truncated: bool=False


def configured_reserve_policies(config):
    """Validate a detached versioned configuration; no file access in queries."""
    expected={'wind':{'wind_east_m_s','wind_north_m_s'},
        'current':{'current_east_m_s','current_north_m_s'},
        'waves':{'wave_height_m','wave_period_seconds','wave_direction_from_degrees'}}
    try:
        if type(config['schema']) is not int or config['schema']!=1 or set(config['products'])!=set(expected):raise ValueError('Known reserve configuration schema/products required')
        result={}
        for product,variables in expected.items():
            supplied=config['products'][product]
            if set(supplied)!=variables or any('method' not in v for v in supplied.values()):raise ValueError('Explicit method for every source variable required')
            result[product]=MappingProxyType({name:ReservePolicy(**value) for name,value in supplied.items()})
        return MappingProxyType(result)
    except (KeyError,TypeError) as error:
        raise ValueError('Incomplete or malformed reserve policy configuration') from error


class MarineReserve:
    def __init__(self,product,longitude,latitude,times,values,water,policies,*,metadata=None):
        self.metadata=metadata
        self.product=product;self.longitude=tuple(float(v) for v in longitude);self.latitude=tuple(float(v) for v in latitude);self.times=tuple(utc_time(t,'Marine time') for t in times)
        self.variables=('wave_height_m','wave_period_seconds','wave_direction_from_degrees') if product=='waves' else ('current_east_m_s','current_north_m_s')
        if product not in ('waves','current') or set(policies)!=set(self.variables) or any(type(p) is not ReservePolicy for p in policies.values()):raise ValueError('Known marine product and per-variable reserve policies required')
        self.policies=MappingProxyType(dict(policies));self.water=water;self.values=np.array(values,dtype='float64',copy=True);self.values.flags.writeable=False
        components=4 if product=='waves' else 2
        if self.values.shape!=(len(times),len(latitude),len(longitude),components):raise ValueError('Exact native marine shape required')
        if np.isinf(self.values).any():raise ValueError('Infinite source values are invalid, not missing data')
        for axis in (self.longitude,self.latitude,self.times):
            if len(axis)<2 or any(a>=b for a,b in zip(axis,axis[1:])):raise ValueError('Ordered native marine axes required')
        if any(not isfinite(v) for v in (*self.longitude,*self.latitude)):raise ValueError('Finite marine coordinate axes required')
        self.valid=np.isfinite(self.values).all(axis=-1);self.epochs=np.array([t.timestamp() for t in times])
        if product=='waves':
            direction_length=np.hypot(self.values[...,2],self.values[...,3])
            if (np.any(self.values[...,0]<0) or np.any(self.values[...,1]<=0)
                    or np.any(np.abs(direction_length[np.isfinite(direction_length)]-1)>1e-9)):
                raise ValueError('Invalid normalized wave node')
        self.grid_longitude,self.grid_latitude=np.meshgrid(self.longitude,self.latitude);self.x,self.y=FORWARD.transform(self.grid_longitude,self.grid_latitude)

    @lru_cache(maxsize=16384)
    def sample(self,position,when):
        when=utc_time(when,'Marine query time')
        lon,lat=INVERSE.transform(position.east,position.north,errcheck=True)
        try:
            i,fx=axis_cell(self.longitude,lon);j,fy=axis_cell(self.latitude,lat);k,ft=axis_cell(self.times,when)
            nodes=self.values[k:k+2,j:j+2,i:i+2]
            visible=all(self.water.clear(position,Vector(float(self.x[j+dy,i+dx]),float(self.y[j+dy,i+dx]))) for dy in (0,1) for dx in (0,1))
            if np.isfinite(nodes).all() and visible:
                result=np.zeros(self.values.shape[-1])
                for dt in (0,1):
                    for dy in (0,1):
                        for dx in (0,1):result+=nodes[dt,dy,dx]*(ft if dt else 1-ft)*(fy if dy else 1-fy)*(fx if dx else 1-fx)
                if self.product!='waves' or hypot(result[2],result[3])>1e-12:return tuple(float(v) for v in result),()
        except ValueError:
            pass
        return self.reserve(position,when)

    def reserve(self,position,when):
        # Keep vector components and wave attributes from ONE actual node/time.
        # A product therefore obeys the intersection of its variable policies;
        # mixing independently chosen directions/periods would invent a sea state.
        if any(policy.method=='none' for policy in self.policies.values()):raise DataUnavailable(f'{self.product}: source gap; configured reserve disabled')
        max_distance=min(p.max_distance_m for p in self.policies.values());max_time=min(p.max_time_offset_seconds for p in self.policies.values())
        weight=max(p.time_weight_m_per_second for p in self.policies.values())
        path_enabled=all(p.method=='nearest_valid_water_path' for p in self.policies.values())
        path_budget=dict(spacing_m=min(p.water_path_spacing_m for p in self.policies.values()),
            max_cells=min(p.water_path_max_cells for p in self.policies.values()),
            max_expansions=min(p.water_path_max_expansions for p in self.policies.values()),
            margin_m=max(p.water_path_margin_m for p in self.policies.values()))
        max_sources=min(p.water_path_max_sources for p in self.policies.values());attempts=0;truncated=False
        offsets=self.epochs-when.timestamp();eligible=np.flatnonzero(np.abs(offsets)<=max_time)
        if not len(eligible):raise DataUnavailable(f'{self.product}: no valid source time within configured reserve')
        order=eligible[np.argsort(np.abs(offsets[eligible]),kind='stable')]
        distance=np.hypot(self.x-position.east,self.y-position.north);possible=self.valid[eligible].any(axis=0)&(distance<=max_distance)
        indices=np.argsort(np.where(possible,distance,np.inf),axis=None,kind='stable');best=None;best_score=float('inf')
        for index in indices:
            j,i=np.unravel_index(index,distance.shape);d=float(distance[j,i])
            if not possible[j,i] or d>best_score:break
            k=next((int(k) for k in order if self.valid[k,j,i]),None)
            if k is None:continue
            source=Vector(float(self.x[j,i]),float(self.y[j,i]));connection=None;length=d
            if not self.water.clear(position,source,path_budget['margin_m'] if path_enabled else 0):
                if not path_enabled:continue
                if attempts>=max_sources:truncated=True;break
                attempts+=1
                connection=self.water.connection(position,source,max_distance_m=max_distance,**path_budget)
                if connection.status!='found':
                    if connection.status not in ('disconnected_water','endpoint_blocked'):truncated=True
                    continue
                length=connection.distance_m
            score=length+abs(float(offsets[k]))*weight
            if score<best_score:best_score=score;best=(k,j,i,length,d,connection)
        if best is None:raise DataUnavailable(f'{self.product}: no valid reserve source found over water within {max_distance:g} m / {max_time:g} s; path_sources={attempts}/{max_sources}')
        k,j,i,d,direct,connection=best;value=tuple(float(v) for v in self.values[k,j,i]);raw=(value[0],value[1],degrees(atan2(value[2],value[3]))%360) if self.product=='waves' else value
        path=tuple(tuple(float(v) for v in INVERSE.transform(p.east,p.north,errcheck=True)) for p in connection.points) if connection else ()
        method='nearest_valid_water_path' if connection else 'nearest_valid_visible_water'
        records=tuple(DataEstimate(variable,method,float(self.grid_longitude[j,i]),float(self.grid_latitude[j,i]),self.times[k],d,float(offsets[k]),raw[n],
            direct_distance_m=direct,connection_waypoints=path,connection_expansions=connection.expansions if connection else 0,
            connection_spacing_m=connection.spacing_m if connection else None,
            source_search_truncated=truncated) for n,variable in enumerate(self.variables))
        return value,records


class NativeWindWithReserve(MarineReserve):
    """Keep NativeMetWind's native LCC interpolation; share only reserve policy."""
    def __init__(self,sample,water,policies):
        from infrastructure.met_wind_segments import NativeMetWind,MET_FORWARD
        self.native=NativeMetWind(sample);self.product='wind';self.variables=('wind_east_m_s','wind_north_m_s')
        if set(policies)!=set(self.variables) or any(type(p) is not ReservePolicy for p in policies.values()):raise ValueError('Per-component wind reserve policies required')
        self.policies=MappingProxyType(dict(policies));self.water=water;self.times=tuple(utc_time(t,'Wind source time') for t in sample.times);self.epochs=np.array([t.timestamp() for t in self.times])
        for axis in (sample.x_m,sample.y_m,self.times):
            if len(axis)<2 or any(a>=b for a,b in zip(axis,axis[1:])):raise ValueError('Ordered native wind axes required')
        if any(not isfinite(float(v)) for v in (*sample.x_m,*sample.y_m)):raise ValueError('Finite native wind axes required')
        # Source positions must derive from the SAME native axes as the values;
        # accepting a second detached coordinate matrix could misattribute them.
        native_x,native_y=np.meshgrid(np.array(sample.x_m,dtype=float),np.array(sample.y_m,dtype=float))
        self.grid_longitude,self.grid_latitude=MET_FORWARD.transform(native_x,native_y,direction='INVERSE',errcheck=True)
        speed=np.array(sample.speed_m_s,dtype=float);direction=np.array(sample.direction_from_degrees,dtype=float)
        expected=(len(self.times),len(sample.y_m),len(sample.x_m))
        if speed.shape!=expected or direction.shape!=expected:raise ValueError('Exact native wind source shape required')
        if np.isinf(speed).any() or np.isinf(direction).any() or np.any(speed[np.isfinite(speed)]<0) or np.any((direction[np.isfinite(direction)]<0)|(direction[np.isfinite(direction)]>360)):raise ValueError('Invalid source wind')
        self.values=np.stack((-speed*np.sin(np.deg2rad(direction)),-speed*np.cos(np.deg2rad(direction))),axis=-1);self.values.flags.writeable=False
        self.valid=np.isfinite(self.values).all(axis=-1);self.x,self.y=FORWARD.transform(self.grid_longitude,self.grid_latitude)
        if (self.grid_longitude.shape!=self.valid.shape[1:] or self.grid_latitude.shape!=self.valid.shape[1:]
                or not np.isfinite(self.grid_longitude).all() or not np.isfinite(self.grid_latitude).all()):raise ValueError('Exact finite native wind coordinates required')

    @lru_cache(maxsize=16384)
    def sample(self,position,when):
        when=utc_time(when,'Wind query time');lon,lat=INVERSE.transform(position.east,position.north,errcheck=True)
        try:
            value=self.native.at(lon,lat,when);return (value.east,value.north),()
        except ValueError:return self.reserve(position,when)
