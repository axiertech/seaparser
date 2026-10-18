"""Assemble existing directed OSM coastlines into reusable water polygons.

Coastline direction defines land on the left. Open source chains are noded
against the acquisition boundary, never closed by a guessed inland chord.
Dangling interior coastlines reject materialization rather than being dropped.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from shapely import LineString,Polygon,Point,STRtree,unary_union,intersection,polygonize_full,to_wkb,set_precision
from infrastructure.land import FORWARD,FRAME
from scripts.copernicus_budget import digest

VERSION='osm-directed-coastline-water-v1'
TOPOLOGY_PRECISION_M=.0001
COAST_GUARD_M=.001


def water_faces(lines,domain):
    """Pure topology function also exercised with known synthetic shorelines."""
    # Snap-round only the topology operations. Original directed lines classify
    # the faces, and a larger water erosion preserves a conservative land guard.
    domain=set_precision(domain,TOPOLOGY_PRECISION_M)
    clipped=[intersection(set_precision(line,TOPOLOGY_PRECISION_M),domain,grid_size=TOPOLOGY_PRECISION_M) for line in lines if line.intersects(domain)]
    network=unary_union([*clipped,domain.boundary],grid_size=TOPOLOGY_PRECISION_M)
    polygons,cuts,dangles,invalid=polygonize_full(list(network.geoms) if hasattr(network,'geoms') else [network])
    if not cuts.is_empty or not dangles.is_empty or not invalid.is_empty:
        boundary_distances=[domain.boundary.distance(Point(p)) for line in dangles.geoms for p in (line.coords[0],line.coords[-1])]
        short=sum(line.length<1e-6 for line in dangles.geoms)
        raise ValueError(f'Incomplete coastline topology: cuts={len(cuts.geoms)}, dangles={len(dangles.geoms)}, invalid={len(invalid.geoms)}, submicrometre={short}, boundary_endpoints={sum(v<1e-6 for v in boundary_distances)}/{len(boundary_distances)}, max_boundary_distance={max(boundary_distances,default=0)}')
    tree=STRtree(lines);water=[];land=[]
    for face in polygons.geoms:
        p=face.representative_point()
        if not domain.covers(p):continue
        coast=lines[int(tree.nearest(p))];distance=coast.project(p)
        # Keep the ORIGINAL source direction, independent of GEOS noding order.
        epsilon=min(.01,coast.length/1000)
        a=coast.interpolate(max(0,distance-epsilon));b=coast.interpolate(min(coast.length,distance+epsilon))
        side=(b.x-a.x)*(p.y-a.y)-(b.y-a.y)*(p.x-a.x)
        if side==0:raise ValueError('Unclassifiable coastline side')
        (land if side>0 else water).append(face)
    if not water:raise ValueError('No source-supported water face')
    if abs(sum(face.area for face in (*water,*land))-domain.area)>domain.area*1e-8:
        raise ValueError('Coastline faces do not partition the acquisition domain')
    result=unary_union(water).buffer(-COAST_GUARD_M,join_style='mitre')
    if not result.is_valid:raise ValueError('Invalid assembled water geometry')
    return result,{'water_faces':len(water),'land_faces':len(land),'topology_cuts':0,'topology_dangles':0,
        'topology_precision_m':TOPOLOGY_PRECISION_M,'additional_land_guard_m':COAST_GUARD_M}


def build(directory):
    directory=Path(directory);source=directory/'land/coastline.osm';source_hash=digest(source)
    entry=json.loads((directory/'land/sources.json').read_text())['coastline.osm']
    if source_hash!=entry['sha256'] or source.stat().st_size!=entry['bytes']:raise ValueError('Coastline source hash/size changed')
    output=directory/'land/water.wkb';manifest=directory/'land/water.json'
    if output.exists() or manifest.exists():
        saved=json.loads(manifest.read_text())
        if saved['version']!=VERSION or saved['source_sha256']!=source_hash or saved['water_sha256']!=digest(output):raise ValueError('Existing materialized land differs; preserve it')
        print('WATER_CACHE_HIT',saved['water_sha256'],flush=True);return saved
    bbox=json.loads((directory/'request.json').read_text())['bbox'];w,s,e,n=bbox
    border=[(w+(e-w)*i/64,s) for i in range(64)]+[(e,s+(n-s)*i/64) for i in range(64)]+[(e-(e-w)*i/64,n) for i in range(64)]+[(w,n-(n-s)*i/64) for i in range(64)]
    domain=Polygon([FORWARD.transform(x,y,errcheck=True) for x,y in border])
    nodes={};ways=[]
    for _,element in ET.iterparse(source,events=('end',)):
        if element.tag=='node':nodes[element.attrib['id']]=(float(element.attrib['lon']),float(element.attrib['lat']));element.clear()
        elif element.tag=='way':
            refs=[node.attrib['ref'] for node in element.findall('nd')]
            if len(refs)<2 or any(node not in nodes for node in refs):raise ValueError('Missing coastline nodes')
            ways.append(refs);element.clear()
    print('COASTLINE_NODES',len(nodes),'WAYS',len(ways),flush=True)
    lines=[]
    for refs in ways:
        points=[nodes[node] for node in refs];xs,ys=FORWARD.transform([p[0] for p in points],[p[1] for p in points],errcheck=True)
        line=LineString(zip(xs,ys))
        if not line.is_simple:raise ValueError('Self-intersecting source coastline')
        lines.append(line)
    water,stats=water_faces(lines,domain);data=to_wkb(water)
    output.write_bytes(data)
    result={'version':VERSION,'projection':FRAME,'bbox':bbox,'source_sha256':source_hash,'water_sha256':sha256(data).hexdigest(),
        'bytes':len(data),'source_nodes':len(nodes),'source_ways':len(ways),'license':'ODbL-1.0','completeness':'unknown','depth':'unknown',**stats}
    manifest.write_text(json.dumps(result,indent=2)+'\n');print('WATER_MATERIALIZED',json.dumps(result),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args();build(a.directory)
