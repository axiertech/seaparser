"""Assemble existing directed OSM coastlines into reusable water polygons.

Coastline direction defines land on the left. Open source chains are noded
against the acquisition boundary, never closed by a guessed inland chord.
Dangling interior coastlines reject materialization rather than being dropped.
"""
import argparse
from array import array
from hashlib import sha256
import json
from math import ceil,floor,isfinite
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from shapely import LineString,Polygon,Point,STRtree,unary_union,coverage_union_all,intersection,polygonize_full,to_wkb,from_wkb,set_precision,box,get_num_coordinates
from shapely.prepared import prep
from infrastructure.land import FORWARD,FRAME
from scripts.copernicus_budget import digest

VERSION='osm-directed-coastline-water-v2'
TOPOLOGY_PRECISION_M=.0001
COAST_GUARD_M=.001
TILED_GUARD_M=.006
MIN_TILED_CLEARANCE_M=.005


def read_coastlines(source):
    """Retain OSM IDs/coordinates in compact arrays, not a million objects."""
    ids=array('q');longitudes=array('d');latitudes=array('d');ways=[]
    parser=ET.iterparse(source,events=('start','end'));_,root=next(parser)
    if root.tag!='osm':raise ValueError('Unexpected coastline XML root')
    for event,element in parser:
        if event!='end':continue
        if element.tag=='remark':raise ValueError('Incomplete coastline source')
        if element.tag=='node':
            identifier=int(element.attrib['id'])
            if identifier<=0:raise ValueError('Positive OSM node ID required')
            ids.append(identifier);longitudes.append(float(element.attrib['lon']));latitudes.append(float(element.attrib['lat']))
            root.clear()
        elif element.tag=='way':
            refs=array('q',(int(node.attrib['ref']) for node in element.findall('nd')))
            if len(refs)<2:raise ValueError('Missing coastline nodes')
            ways.append(refs);root.clear()
    node_count,way_count=len(ids),len(ways)
    if not node_count or not way_count:raise ValueError('Complete coastline nodes/ways required')
    ids=np.frombuffer(ids,dtype=np.int64);lons=np.frombuffer(longitudes,dtype=np.float64);lats=np.frombuffer(latitudes,dtype=np.float64)
    if not np.isfinite(lons).all() or not np.isfinite(lats).all():raise ValueError('Finite source coastline coordinates required')
    if not (np.diff(ids)>0).all():
        order=np.argsort(ids,kind='stable');ids,lons,lats=ids[order],lons[order],lats[order]
        if not (np.diff(ids)>0).all():raise ValueError('Duplicate coastline node IDs')
    lines=[]
    for refs in ways:
        refs=np.frombuffer(refs,dtype=np.int64);indices=np.searchsorted(ids,refs)
        if (indices>=len(ids)).any() or not (ids[indices]==refs).all():raise ValueError('Missing coastline nodes')
        xs,ys=FORWARD.transform(lons[indices],lats[indices],errcheck=True)
        line=LineString(np.column_stack((xs,ys)))
        if not line.is_simple:raise ValueError('Self-intersecting source coastline')
        lines.append(line)
    return lines,node_count,way_count


def _edges(geometry):
    boundary=geometry.boundary;parts=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
    edges=[]
    for part in parts:
        coordinates=np.asarray(part.coords)
        edges.extend(LineString(coordinates[i:i+65]) for i in range(0,len(coordinates)-1,64))
    return edges


def validate_erosion(water,result):
    """Prove subset/clearance without overlaying two million-vertex polygons.

    Closed boundaries cannot cross (the complete edge-distance check below).
    A wet interior witness per result polygon excludes outside components;
    one excluded witness per connected source ring excludes filled land holes.
    Together these are a whole-set topology proof, not sampled route support.
    """
    if result.is_empty or result.geom_type not in ('Polygon','MultiPolygon') or not result.is_valid:
        raise ValueError('Invalid eroded water geometry')
    source=prep(water);target=prep(result)
    components=list(result.geoms) if result.geom_type=='MultiPolygon' else [result]
    if any(not source.contains(p.representative_point()) for p in components):
        raise ValueError('Erosion includes an outside source component')
    boundary=water.boundary;rings=list(boundary.geoms) if hasattr(boundary,'geoms') else [boundary]
    if any(target.covers(Point(ring.coords[0])) for ring in rings):
        raise ValueError('Erosion fills source land or acquisition boundary')
    source_edges=STRtree(_edges(water));result_edges=_edges(result)
    for start in range(0,len(result_edges),2048):
        hits=source_edges.query(np.array(result_edges[start:start+2048],dtype=object),
                                predicate='dwithin',distance=MIN_TILED_CLEARANCE_M)
        if hits.size:raise ValueError('Tiled erosion violates conservative closed source guard')


def erode_tiled(water,*,spacing_m=20000,max_tiles=512,progress=None,validate=True):
    """Conservative local erosion, then exact closed-source clearance checks.

    A 6 mm round guard exceeds the old 1 mm mitre guard's 5x limit,
    including arc approximation and 0.1 mm snap rounding. One metre of
    overlap keeps artificial tile boundaries outside the buffer influence.
    Final subset and 5 mm closed-boundary checks reject any clipping/seam
    defect; no unchecked water geometry can be admitted.
    """
    if (type(spacing_m) not in (int,float) or not isfinite(spacing_m) or spacing_m<1
            or type(max_tiles) is not int or max_tiles<=0):raise ValueError('Positive bounded water tile budget required')
    w,s,e,n=water.bounds
    imin,jmin,imax,jmax=floor(w/spacing_m),floor(s/spacing_m),ceil(e/spacing_m),ceil(n/spacing_m)
    count=(imax-imin)*(jmax-jmin)
    if count>max_tiles:raise ValueError('Water erosion tile budget exceeded')
    pieces=[]
    floating_water=set_precision(water,0)
    for j in range(jmin,jmax):
        for i in range(imin,imax):
            x,y=i*spacing_m,j*spacing_m
            local=intersection(floating_water,box(x-1,y-1,x+spacing_m+1,y+spacing_m+1),grid_size=0)
            if local.is_empty:continue
            eroded=local.buffer(-TILED_GUARD_M,quad_segs=8,join_style='round')
            piece=intersection(eroded,box(x,y,x+spacing_m,y+spacing_m),grid_size=TOPOLOGY_PRECISION_M)
            if not piece.is_empty:pieces.append(piece)
    # Core boxes have disjoint interiors; their shared edges already use the
    # same precision grid. General overlay would needlessly renode every coast.
    del floating_water,local,eroded,piece
    if progress:progress({'phase':'tile_union','pieces':len(pieces),'coordinates':sum(int(get_num_coordinates(p)) for p in pieces)})
    result=coverage_union_all(pieces)
    del pieces
    if validate:validate_erosion(water,result)
    return result,{'erosion_method':'overlapping-tiled-round-closed-clearance-v1',
        'erosion_tile_spacing_m':spacing_m,'erosion_tiles':count,
        'additional_land_guard_m':TILED_GUARD_M,'checked_closed_source_clearance_m':MIN_TILED_CLEARANCE_M}


def water_faces(lines,domain,*,consume_lines=False,progress=None,topology_only=False):
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
    # polygonize_full gives non-overlapping faces on one noded precision grid.
    # Avoid a second general overlay of this already established coverage.
    merged=coverage_union_all(water)
    if not merged.is_valid or abs(merged.area-sum(face.area for face in water))>domain.area*1e-8:
        raise ValueError('Invalid assembled water face coverage')
    counts={'water_faces':len(water),'land_faces':len(land)}
    # Topology construction and classification are complete. Keeping their
    # full graphs alive during erosion/union needlessly multiplies peak memory.
    del clipped,network,polygons,tree,water,land,face,p,coast,a,b
    if consume_lines:lines.clear()
    if progress:progress({'phase':'erosion','coordinates':int(get_num_coordinates(merged)),**counts})
    if topology_only:return merged,{**counts,'topology_cuts':0,'topology_dangles':0,'topology_precision_m':TOPOLOGY_PRECISION_M}
    if get_num_coordinates(merged)>100000:
        result,erosion=erode_tiled(merged,progress=progress)
    else:
        result=merged.buffer(-COAST_GUARD_M,join_style='mitre')
        erosion={'erosion_method':'whole-mitre-v1','additional_land_guard_m':COAST_GUARD_M}
        if not result.is_valid:raise ValueError('Invalid assembled water geometry')
    return result,{**counts,'topology_cuts':0,'topology_dangles':0,
        'topology_precision_m':TOPOLOGY_PRECISION_M,**erosion}


def build(directory,stage=None):
    directory=Path(directory);source=directory/'land/coastline.osm';source_hash=digest(source)
    entry=json.loads((directory/'land/sources.json').read_text())['coastline.osm']
    if source_hash!=entry['sha256'] or source.stat().st_size!=entry['bytes']:raise ValueError('Coastline source hash/size changed')
    output=directory/'land/water.wkb';manifest=directory/'land/water.json'
    if output.exists() or manifest.exists():
        saved=json.loads(manifest.read_text())
        if saved['version'] not in (VERSION,'osm-directed-coastline-water-v1') or saved['source_sha256']!=source_hash or saved['water_sha256']!=digest(output):raise ValueError('Existing materialized land differs; preserve it')
        print('WATER_CACHE_HIT',saved['water_sha256'],flush=True);return saved
    bbox=json.loads((directory/'request.json').read_text())['bbox'];w,s,e,n=bbox
    identity={'version':VERSION,'source_sha256':source_hash,'bbox':bbox,
              'builder_sha256':digest(Path(__file__)),'projection':FRAME}
    stages=directory/'land/build-stages';stages.mkdir(exist_ok=True)
    def save_stage(name,geometry,stats):
        payload=to_wkb(geometry);path=stages/(name+'.wkb');receipt=stages/(name+'.json')
        if path.exists() or receipt.exists():raise ValueError('Preserve existing stage; verify before reuse')
        path.write_bytes(payload)
        receipt.write_text(json.dumps({**identity,'sha256':sha256(payload).hexdigest(),'bytes':len(payload),'stats':stats},indent=2)+'\n')
    def load_stage(name):
        path=stages/(name+'.wkb');saved=json.loads((stages/(name+'.json')).read_text())
        if any(saved.get(k)!=v for k,v in identity.items()) or saved['sha256']!=digest(path) or saved['bytes']!=path.stat().st_size:
            raise ValueError('Stage identity/integrity mismatch')
        return from_wkb(path.read_bytes()),saved['stats']
    progress=lambda info:print('WATER_STAGE',json.dumps(info),flush=True)
    if stage=='erode':
        merged,stats=load_stage('topology')
        water,erosion=erode_tiled(merged,progress=progress,validate=False)
        save_stage('eroded',water,{**stats,**erosion});print('STAGE_READY eroded',flush=True);return
    if stage=='validate':
        merged,_=load_stage('topology');water,stats=load_stage('eroded')
        validate_erosion(merged,water);del merged
        node_count,way_count=stats.pop('source_nodes'),stats.pop('source_ways')
    else:
        border=[(w+(e-w)*i/64,s) for i in range(64)]+[(e,s+(n-s)*i/64) for i in range(64)]+[(e-(e-w)*i/64,n) for i in range(64)]+[(w,n-(n-s)*i/64) for i in range(64)]
        domain=Polygon([FORWARD.transform(x,y,errcheck=True) for x,y in border])
        lines,node_count,way_count=read_coastlines(source)
        print('COASTLINE_NODES',node_count,'WAYS',way_count,flush=True)
        water,stats=water_faces(lines,domain,consume_lines=True,progress=progress,topology_only=stage=='topology')
        if stage=='topology':
            save_stage('topology',water,{**stats,'source_nodes':node_count,'source_ways':way_count})
            print('STAGE_READY topology',flush=True);return
    data=to_wkb(water)
    output.write_bytes(data)
    result={'version':VERSION,'projection':FRAME,'bbox':bbox,'source_sha256':source_hash,'water_sha256':sha256(data).hexdigest(),
        'bytes':len(data),'source_nodes':node_count,'source_ways':way_count,'license':'ODbL-1.0','completeness':'unknown','depth':'unknown',**stats}
    manifest.write_text(json.dumps(result,indent=2)+'\n');print('WATER_MATERIALIZED',json.dumps(result),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--stage',choices=('topology','erode','validate'));a=p.parse_args();build(a.directory,a.stage)
