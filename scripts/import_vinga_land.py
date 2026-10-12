"""Offline, bounded Vinga review import. Incomplete coastlines remain unknown."""
import xml.etree.ElementTree as E
import json
import hashlib
from datetime import datetime
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Offline OSM coastline assembly; never fetches data')
parser.add_argument('source',type=Path); parser.add_argument('--retrieved-at',required=True)
args=parser.parse_args()
if datetime.fromisoformat(args.retrieved_at).tzinfo is None:
 parser.error('retrieved-at requires an explicit timezone')
p=args.source
if p.stat().st_size > 5_000_000:
 parser.error('bounded import permits at most 5 MB')
root=E.parse(p).getroot()
nodes={n.attrib['id']:[float(n.attrib['lon']),float(n.attrib['lat'])] for n in root.findall('node')}
ways={w.attrib['id']:w for w in root.findall('way') if any(t.attrib=={'k':'natural','v':'coastline'} for t in w.findall('tag'))}
refs={k:[n.attrib['ref'] for n in w.findall('nd')] for k,w in ways.items()}
remaining=set(refs); rings=[]
while remaining:
 k=min(remaining,key=int); remaining.remove(k); ids=[k]; chain=refs[k][:]
 while chain[-1]!=chain[0]:
  successors=[j for j in remaining if refs[j][0]==chain[-1]]
  if len(successors)!=1: break
  j=successors[0];remaining.remove(j);ids.append(j);chain.extend(refs[j][1:])
 if chain[-1]==chain[0]:
  coords=[nodes[n] for n in chain]
  if all(11.593<=x<=11.614 and 57.629<=y<=57.637 for x,y in coords):
   rings.append({'type':'Feature','geometry':{'type':'Polygon','coordinates':[coords]},'properties':{'id':'osm-'+ids[0],'ways':[{'id':j,'version':ways[j].attrib['version'],'timestamp':ways[j].attrib['timestamp']} for j in ids],'quality':'unknown','depth':'unknown'}})
print([(r['properties']['id'],len(r['geometry']['coordinates'][0])) for r in rings])
out={'type':'FeatureCollection','features':rings,'metadata':{'source':'OpenStreetMap contributors','license':'ODbL-1.0','attribution':'© OpenStreetMap contributors','license_url':'https://opendatacommons.org/licenses/odbl/1-0/','source_url':'https://api.openstreetmap.org/api/0.6/map?bbox=11.58,57.62,11.63,57.65','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'retrieved_at':args.retrieved_at,'version':'vinga-2026-10-12-v1','coverage':[11.593,57.629,11.614,57.637],'completeness':'unknown','depth':'unknown','coordinate_order':'longitude, latitude'}}
Path('fixtures').mkdir(exist_ok=True);Path('fixtures/vinga-land.geojson').write_text(json.dumps(out,separators=(',',':'))+'\n')
