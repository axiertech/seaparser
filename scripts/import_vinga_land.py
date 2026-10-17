"""Offline bounded OSM coastline assembly; incomplete sources remain unknown."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import xml.etree.ElementTree as E

from infrastructure.land import FORWARD
from infrastructure.native_marine import disk_geographic_bounds

LEGACY_BOUNDS=(11.593,57.629,11.614,57.637)


def assemble(data, *, retrieved_at, source_url, coverage=LEGACY_BOUNDS, radius_m=None):
    if len(data)>5_000_000:raise ValueError('Bounded import permits at most 5 MB')
    if datetime.fromisoformat(retrieved_at).tzinfo is None:raise ValueError('Explicit timezone-aware retrieval time required')
    west,south,east,north=coverage
    if not (11.55<=west<east<=11.66 and 57.60<=south<north<=57.67):raise ValueError('Bounded reviewed Vinga source extent required')
    if radius_m is not None:
        bounds=disk_geographic_bounds(radius_m+10)
        if not (west<=bounds[0] and south<=bounds[1] and east>=bounds[2] and north>=bounds[3]):
            raise ValueError('Source bbox does not enclose guarded land-review disk')
    root=E.fromstring(data)
    nodes={n.attrib['id']:[float(n.attrib['lon']),float(n.attrib['lat'])] for n in root.findall('node')}
    if any(not all(isfinite(v) for v in p) or not -180<=p[0]<=180 or not -90<=p[1]<=90 for p in nodes.values()):
        raise ValueError('Finite geographic source nodes required')
    if len(nodes)!=len(root.findall('node')) or len({w.attrib['id'] for w in root.findall('way')})!=len(root.findall('way')):
        raise ValueError('Duplicate source node/way identities are ambiguous')
    ways={w.attrib['id']:w for w in root.findall('way') if any(t.attrib=={'k':'natural','v':'coastline'} for t in w.findall('tag'))}
    refs={k:[n.attrib['ref'] for n in w.findall('nd')] for k,w in ways.items()}
    if any(len(v)<2 or any(n not in nodes for n in v) for v in refs.values()):raise ValueError('Complete source coastline nodes required')
    remaining=set(refs);rings=[];open_count=0;excluded=0
    while remaining:
        key=min(remaining,key=int);remaining.remove(key);ids=[key];chain=refs[key][:]
        while chain[-1]!=chain[0]:
            successors=[j for j in remaining if refs[j][0]==chain[-1]]
            if len(successors)!=1:break
            j=successors[0];remaining.remove(j);ids.append(j);chain.extend(refs[j][1:])
        coords=[nodes[n] for n in chain]
        relevant=True
        if radius_m is not None:
            local=[FORWARD.transform(*p,errcheck=True) for p in coords];padding=radius_m+10
            relevant=(min(p[0] for p in local)<=padding and max(p[0] for p in local)>=-padding
                      and min(p[1] for p in local)<=padding and max(p[1] for p in local)>=-padding)
        if chain[-1]!=chain[0]:
            open_count+=1
            if radius_m is not None and relevant:raise ValueError('Open coastline chain may intersect review disk; no silent omission')
            continue
        inside=all(west<=x<=east and south<=y<=north for x,y in coords)
        if relevant and not inside and radius_m is not None:raise ValueError('Relevant whole land ring extends outside reviewed source bounds')
        if not relevant or not inside:excluded+=1;continue
        rings.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[coords]},'properties':{
            'id':'osm-'+ids[0],'ways':[{'id':j,'version':ways[j].attrib['version'],'timestamp':ways[j].attrib['timestamp']} for j in ids],
            'quality':'unknown','depth':'unknown'}})
    if not rings:raise ValueError('No complete land rings in reviewed extent')
    metadata=dict(source='OpenStreetMap contributors',license='ODbL-1.0',attribution='© OpenStreetMap contributors',
        license_url='https://opendatacommons.org/licenses/odbl/1-0/',source_url=source_url,source_sha256=sha256(data).hexdigest(),
        retrieved_at=retrieved_at,version='vinga-2026-10-12-v1' if radius_m is None else 'vinga-2026-10-17-radius-'+str(radius_m),
        coverage=list(coverage),completeness='unknown',depth='unknown',coordinate_order='longitude, latitude')
    if radius_m is not None:
        metadata.update(review_disk_radius_m=radius_m,selection_square_padding_m=10,
            selection_scope='All assembled coast rings whose projected bounding box intersects the padded review square; completeness remains unknown',
            source_coastline_way_count=len(ways),excluded_closed_rings=excluded,open_chains_outside_review=open_count)
    return {'type':'FeatureCollection','features':rings,'metadata':metadata}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--retrieved-at',required=True)
    p.add_argument('--output',type=Path,default=Path('fixtures/vinga-land.geojson'))
    p.add_argument('--coverage',type=float,nargs=4,default=LEGACY_BOUNDS);p.add_argument('--radius-m',type=float)
    p.add_argument('--source-url',default='https://api.openstreetmap.org/api/0.6/map?bbox=11.58,57.62,11.63,57.65')
    a=p.parse_args()
    with a.source.open('rb') as stream:data=stream.read(5_000_001)
    result=assemble(data,retrieved_at=a.retrieved_at,source_url=a.source_url,coverage=a.coverage,radius_m=a.radius_m)
    if a.output.exists():raise ValueError('Existing frozen land snapshot must be preserved')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('LAND_IMPORTED',len(result['features']),'closed rings; completeness/depth unknown')
