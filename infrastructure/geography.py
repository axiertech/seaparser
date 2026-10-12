"""Fixed local WGS84 azimuthal-equidistant frame; no network/grid downloads."""
from math import isfinite
from pyproj import CRS, Transformer, network, __version__, proj_version_str
from prototype.model import Vector

network.set_network_enabled(False)
ORIGIN_LATITUDE, ORIGIN_LONGITUDE = 58.0, 11.0
MAX_RADIUS_M = 1000
DEFINITION = '+proj=aeqd +lat_0=58 +lon_0=11 +ellps=WGS84 +units=m +no_defs'
FORWARD = Transformer.from_crs('EPSG:4326',CRS.from_proj4(DEFINITION),always_xy=True)
INVERSE = Transformer.from_crs(CRS.from_proj4(DEFINITION),'EPSG:4326',always_xy=True)


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(value)


def to_local(latitude,longitude):
    if not (finite(latitude) and finite(longitude) and 57.98 <= latitude <= 58.02
            and 10.96 <= longitude <= 11.04):
        raise ValueError('Position utanför demonstratorns geografiska område')
    east,north = FORWARD.transform(longitude,latitude,errcheck=True)
    result=Vector(east,north)
    if result.speed > MAX_RADIUS_M:
        raise ValueError('Position utanför demonstratorns radie 1000 m')
    return result


def to_geo(position):
    if not all(finite(v) for v in (position.east,position.north)) or position.speed > MAX_RADIUS_M:
        raise ValueError('Lokala koordinater utanför demonstratorns radie 1000 m')
    longitude,latitude = INVERSE.transform(position.east,position.north,errcheck=True)
    return [longitude,latitude]


def metadata():
    return {'pyproj_version':__version__,'proj_version':proj_version_str,'crs':'WGS84 / local azimuthal equidistant','definition':DEFINITION,
            'origin':[ORIGIN_LONGITUDE,ORIGIN_LATITUDE],'max_radius_m':MAX_RADIUS_M,
            'coordinate_order':'longitude, latitude','reference_tolerance_m':0.01,
            'limitations':'Lokala raka segment; ingen global routing. Prognosområdet är mindre än projektionens område.'}
