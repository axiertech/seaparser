"""Frozen OSM land adapter: display rings and conservative routing hulls differ."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from pyproj import CRS, Transformer
from prototype.model import Vector
from prototype.polygon import Polygon, xy, cross, inside

FRAME='+proj=aeqd +lat_0=57.633 +lon_0=11.605 +ellps=WGS84 +units=m +no_defs'
FORWARD=Transformer.from_crs('EPSG:4326',CRS.from_proj4(FRAME),always_xy=True)
INVERSE=Transformer.from_crs(CRS.from_proj4(FRAME),'EPSG:4326',always_xy=True)


def hull(points):
    """Exact monotone-chain predicates on projected stored numbers; no inward simplification."""
    points=sorted(set(xy(p) for p in points))
    def chain(items):
        result=[]
        for p in items:
            while len(result)>1 and cross(result[-2],result[-1],p)<=0:
                result.pop()
            result.append(p)
        return result
    result=chain(points)[:-1]+chain(reversed(points))[:-1]
    if len(result)<3 or not all(inside(p,result) for p in points):
        raise ValueError('Degenererat eller otillräckligt landhölje')
    return tuple(Vector(float(x),float(y)) for x,y in result)


@dataclass(frozen=True)
class LandSnapshot:
    version: str
    sha256: str
    source_geojson: str
    obstacles: tuple[Polygon,...]
    depth_status: str='unknown'
    completeness: str='unknown'


def load_land(path=None,margin_m=10,*,review_bounds=None):
    bounds=(11.593,57.629,11.614,57.637) if review_bounds is None else tuple(review_bounds)
    if len(bounds)!=4 or not (11.55<=bounds[0]<bounds[2]<=11.66 and 57.60<=bounds[1]<bounds[3]<=57.67):
        raise ValueError('Utanför granskat Vinga-landområde')
    payload=(path or Path(__file__).resolve().parents[1]/'fixtures/vinga-land.geojson').read_bytes()
    data=json.loads(payload); meta=data['metadata']
    if meta.get('license')!='ODbL-1.0' or meta.get('completeness')!='unknown' or meta.get('depth')!='unknown':
        raise ValueError('Landkälla kräver licens och uttrycklig okänd kvalitet/djup')
    polygons=[]
    for feature in data['features']:
        geometry=feature['geometry']; rings=geometry['coordinates']
        if geometry['type']!='Polygon' or len(rings)!=1 or len(rings[0])<4 or rings[0][0]!=rings[0][-1]:
            raise ValueError('Endast fullständiga slutna landringar utan hål stöds')
        points=[]
        for lon,lat in rings[0][:-1]:
            if not (bounds[0]<=lon<=bounds[2] and bounds[1]<=lat<=bounds[3]):
                raise ValueError('Land utanför fryst testtäckning')
            x,y=FORWARD.transform(lon,lat,errcheck=True); points.append(Vector(x,y))
        polygons.append(Polygon(feature['properties']['id'],hull(points),margin_m,
                                source='OpenStreetMap contributors / ODbL-1.0',version=meta['version'],quality='unknown'))
    if not polygons:
        raise ValueError('Saknat landunderlag')
    return LandSnapshot(meta['version'],hashlib.sha256(payload).hexdigest(),payload.decode(),tuple(polygons))


def to_local(latitude,longitude):
    from .geography import finite
    if not (finite(latitude) and finite(longitude) and 57.629<=latitude<=57.637 and 11.593<=longitude<=11.614):
        raise ValueError('Position utanför Vingas begränsade landunderlag')
    return Vector(*FORWARD.transform(longitude,latitude,errcheck=True))


def to_geo(position):
    from .geography import finite
    if not all(finite(v) for v in (position.east,position.north)) or position.speed>1500:
        raise ValueError('Position utanför Vingas lokala projektion')
    return list(INVERSE.transform(position.east,position.north,errcheck=True))


def metadata():
    from .geography import metadata as base_metadata
    return base_metadata() | {'definition':FRAME,'origin':[11.605,57.633],'max_radius_m':1500,
                              'limitations':'Endast Vinga-testområdet. Okänt djup och okänd landfullständighet.'}


def review_to_geo(position):
    """Project stored larger land-hull vertices for review only, never route input.

    Route coordinates retain to_local/to_geo limits. This explicit path is
    bounded to the separately acquired source bbox and carries no navigation claim.
    """
    lon,lat=INVERSE.transform(position.east,position.north,errcheck=True)
    if not (11.55<=lon<=11.66 and 57.60<=lat<=57.67):
        raise ValueError('Landgranskningspunkt utanför hämtat källområde')
    return [lon,lat]
