"""True WGS84 tangent velocities to fixed Vinga AEQD coordinate rates.

Pure point kinematics, no source qualification, forecast transport or regridding.
Weather/boat vectors remain physical true E/N; accepted integration segments
remain affine in the existing projected coordinate system.
"""
from dataclasses import dataclass
from math import cos,sin,radians,isfinite,sqrt
from pyproj import Proj
from infrastructure.land import FRAME,INVERSE
from prototype.model import Vector

PROJECTION=Proj(FRAME)
A=6378137.0
F=1/298.257223563
E2=F*(2-F)
METHOD='wgs84-aeqd-proj-differential-v1'


@dataclass(frozen=True)
class AeqdMotionFrame:
    radius_m: float=1500

    def __post_init__(self):
        if type(self.radius_m) not in (int,float) or not isfinite(self.radius_m) or not 0<self.radius_m<=1500:
            raise ValueError('Motion frame requires bounded radius <=1500 m')

    def matrix(self,position):
        if not all(isfinite(v) for v in (position.east,position.north)) or position.speed>self.radius_m:
            raise ValueError('Position outside reviewed motion frame')
        lon,lat=INVERSE.transform(position.east,position.north,errcheck=True)
        phi=radians(lat);d=1-E2*sin(phi)**2
        meridian=A*(1-E2)/d**1.5;prime=A/sqrt(d)
        factors=PROJECTION.get_factors(lon,lat,errcheck=True)
        # PROJ's raw derivatives use normalized coordinates x/a,y/a and radians.
        east=A/(prime*cos(phi));north=A/meridian
        a,b,c,d=factors.dx_dlam*east,factors.dx_dphi*north,factors.dy_dlam*east,factors.dy_dphi*north
        determinant=a*d-b*c
        if not all(isfinite(v) for v in (a,b,c,d,determinant)) or not .99<determinant<1.01:
            raise ValueError('Invalid or singular motion differential')
        return a,b,c,d

    def position_rate(self,position,physical_velocity):
        if not all(isfinite(v) for v in (physical_velocity.east,physical_velocity.north)):
            raise ValueError('Finite physical velocity required')
        a,b,c,d=self.matrix(position)
        result=Vector(a*physical_velocity.east+b*physical_velocity.north,
                      c*physical_velocity.east+d*physical_velocity.north)
        if not all(isfinite(v) for v in (result.east,result.north)):
            raise ValueError('Non-finite projected position rate')
        return result

    def physical_direction(self,position,local_direction):
        if not all(isfinite(v) for v in (local_direction.east,local_direction.north)) or local_direction.speed==0:
            raise ValueError('Finite nonzero local direction required')
        a,b,c,d=self.matrix(position);det=a*d-b*c
        physical=Vector((d*local_direction.east-b*local_direction.north)/det,
                        (-c*local_direction.east+a*local_direction.north)/det)
        return physical.scaled(1/physical.speed)


@dataclass(frozen=True)
class RegionalAeqdMotionFrame(AeqdMotionFrame):
    """Explicit coastal development frame; legacy 1500 m frame stays bounded."""
    radius_m: float=120000

    def __post_init__(self):
        if type(self.radius_m) not in (int,float) or not isfinite(self.radius_m) or not 0<self.radius_m<=120000:
            raise ValueError('Regional motion frame requires bounded radius <=120000 m')


@dataclass(frozen=True)
class SwedishCoastAeqdMotionFrame(AeqdMotionFrame):
    """Explicit Trelleborg–Strömstad frame; older profile bounds unchanged."""
    radius_m: float=350000

    def __post_init__(self):
        if type(self.radius_m) not in (int,float) or not isfinite(self.radius_m) or not 0<self.radius_m<=350000:
            raise ValueError('Swedish coast motion frame requires bounded radius <=350000 m')
