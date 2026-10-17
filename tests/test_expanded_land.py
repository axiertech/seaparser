"""Closed source rings and explicit expanded review scope, never navigability."""
from pathlib import Path
import json
import unittest
from infrastructure.land import load_land,FORWARD
from prototype.polygon import inside,xy
from prototype.model import Vector
from scripts.import_vinga_land import assemble

ROOT=Path(__file__).resolve().parents[1]


class ExpandedLandTests(unittest.TestCase):
    def test_all_raw_ring_vertices_are_inside_conservative_hulls(self):
        path=ROOT/'fixtures/vinga-land-expanded-20261017.geojson'
        with self.assertRaises(ValueError):load_land(path)
        snapshot=load_land(path,review_bounds=(11.55,57.60,11.66,57.67))
        self.assertEqual(len(snapshot.obstacles),24)
        self.assertEqual(snapshot.completeness,'unknown');self.assertEqual(snapshot.depth_status,'unknown')
        for feature,polygon in zip(json.loads(snapshot.source_geojson)['features'],snapshot.obstacles):
            vertices=tuple(xy(v) for v in polygon.vertices)
            for lon,lat in feature['geometry']['coordinates'][0]:
                self.assertTrue(inside(xy(Vector(*FORWARD.transform(lon,lat))),vertices))
        self.assertTrue(any(p.intersects(Vector(300,-400),Vector(300,-400)) for p in snapshot.obstacles))
        self.assertFalse(any(p.intersects(Vector(500,0),Vector(500,350)) for p in snapshot.obstacles))

    def source(self,closed):
        last='1' if closed else '3'
        return ('<osm><node id="1" lon="11.604" lat="57.632"/><node id="2" lon="11.606" lat="57.632"/>'
                '<node id="3" lon="11.605" lat="57.634"/><way id="4" version="1" timestamp="2026-01-01T00:00:00Z">'
                '<nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="'+last+'"/><tag k="natural" v="coastline"/></way></osm>').encode()

    def test_relevant_open_coast_is_rejected_instead_of_silently_dropped(self):
        options=dict(retrieved_at='2026-10-17T12:00:00Z',source_url='https://api.openstreetmap.org/api/0.6/map',
                     coverage=(11.55,57.60,11.66,57.67),radius_m=1500)
        self.assertEqual(len(assemble(self.source(True),**options)['features']),1)
        with self.assertRaisesRegex(ValueError,'Open coastline'):assemble(self.source(False),**options)
        duplicate=self.source(True).replace(b'</osm>',b'<node id="1" lon="11.605" lat="57.633"/></osm>')
        with self.assertRaisesRegex(ValueError,'Duplicate'):assemble(duplicate,**options)
        with self.assertRaisesRegex(ValueError,'enclose'):assemble(self.source(True),**(options|{'coverage':(11.60,57.63,11.61,57.64)}))
