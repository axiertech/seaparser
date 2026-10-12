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


def load_land(path=None,margin_m=10):
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
            if not (11.593<=lon<=11.614 and 57.629<=lat<=57.637):
                raise ValueError('Land utanför fryst testtäckning')
            x,y=FORWARD.transform(lon,lat,errcheck=True); points.append(Vector(x,y))
        polygons.append(Polygon(feature['properties']['id'],hull(points),margin_m,
                                source='OpenStreetMap contributors / ODbL-1.0',version=meta['version'],quality='unknown'))
    if not polygons:
        raise ValueError('Saknat landunderlag')
    return LandSnapshot(meta['version'],hashlib.sha256(payload).hexdigest(),payload.decode(),tuple(polygons))
