"""Build an isolated land/basemap review page; no network and no publication."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from infrastructure.land import load_land, INVERSE


def build(output):
    snapshot=load_land()
    source=json.loads(snapshot.source_geojson)
    routing={'type':'FeatureCollection','metadata':source['metadata'] | {'method':'conservative convex hull','routing_margin_m':10,'source_snapshot_sha256':snapshot.sha256},'features':[
        {'type':'Feature','properties':{'name':p.name},'geometry':{'type':'Polygon','coordinates':[
            [list(INVERSE.transform(v.east,v.north)) for v in (*p.vertices,p.vertices[0])]]}}
        for p in snapshot.obstacles]}
    output.mkdir(parents=True,exist_ok=True)
    regional_html=(Path(__file__).resolve().parents[1]/'frontend/map/index.html').read_text()
    regional_html=regional_html.replace('<html lang="sv">','<html lang="sv" data-profile="vinga">')
    regional_html=regional_html.replace("img-src 'self' data:;","img-src 'self' data: https://tile.openstreetmap.org;")
    regional_html=regional_html.replace('<title>', '<meta name="referrer" content="strict-origin-when-cross-origin"><title>')
    regional_html=regional_html.replace('Bakgrund: fryst OSM-land och lokalt översiktslager, inga officiella sjökort.', '<button id="background" type="button">Aktivera separat OSM-bakgrund</button> Bakgrunden är valfri, ingen tile-prefetch. <a href="land.geojson">Fryst landunderlag, ODbL-attribution och version</a>.')
    (output/'vinga.html').write_text(regional_html)
    (output/'land.geojson').write_text(snapshot.source_geojson)
    (output/'routing.geojson').write_text(json.dumps(routing))
    (output/'land-review.html').write_text('''<!doctype html><html lang="sv"><meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; style-src 'self' 'unsafe-inline'; script-src 'self'">
<title>Vinga – landgranskning</title><link rel="stylesheet" href="vendor/leaflet.css">
<h1>Vinga: verklig kartbakgrund och fryst landdata</h1>
<p>Granskningsverktyg, inte navigationsunderlag. Djup och landkällans fullständighet: okända.
Orange: OSM-landringar. Rött: konservativa konvexa routinghöljen med 10 m marginal i motorn.
Höljen kan stänga vikar och passager. Kartbilder används aldrig av ruttmotorn.</p>
<p>Denna sida granskar bara landgeometri. Länken till regional planering använder verkliga väderdata och redovisade utvecklingsantaganden.</p>
<button id="background">Aktivera OSM-bakgrund för manuell granskning</button>
<p><a href="land.geojson">Fryst ODbL-landunderlag och källmetadata</a> · <a href="routing.geojson">Routinghöljen</a> · <a href="index.html">Utvecklingsplanering</a> · <a href="vinga.html">Regional planering med verkliga väderdata</a></p>
<div id="map" style="height:65vh"></div><script src="vendor/leaflet.js"></script><script type="module" src="land-review.mjs"></script></html>''')
    (output/'land-review.mjs').write_text((Path(__file__).resolve().parents[1]/'frontend/map/land-review.mjs').read_text())


PUBLIC_ASSETS=('index.html','map.css','main.mjs','map-component.mjs','controller.mjs','client.mjs',
               'vendor/leaflet.js','vendor/leaflet.css','vendor/leaflet-LICENSE.txt',
               'vendor/images/marker-shadow.png','vendor/images/marker-icon.png','vendor/images/marker-icon-2x.png',
               'vendor/images/layers.png','vendor/images/layers-2x.png')


def build_bundle(output):
    """Explicit allowlist; no copying repository, config or unknown generated files."""
    build(output)
    source=Path(__file__).resolve().parents[1]/'frontend/dist'
    for name in PUBLIC_ASSETS:
        target=output/name; target.parent.mkdir(parents=True,exist_ok=True)
        copyfile(source/name,target)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=Path('frontend/land-dist'))
    parser.add_argument('--bundle',action='store_true')
    args=parser.parse_args()
    (build_bundle if args.bundle else build)(args.output)
