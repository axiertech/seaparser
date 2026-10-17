"""Native profile exercises unchanged bounded HTTP jobs and real 24-hull model."""
import asyncio
import json
from pathlib import Path
import unittest
import httpx
from pydantic import ValidationError
from api.main import create_app
from api.models import PlanInput
from application.geographic_plan import scene,calculate_geographic
from infrastructure.land import load_land,to_local
from infrastructure.planning_jobs import JobStore
from prototype.auto_routing import generate_routes,SearchPolicy
from prototype.model import Vector
from scripts.audit_native_candidates import payload

ROOT=Path(__file__).resolve().parents[1]


class SupportedGraphTests(unittest.TestCase):
    def test_supported_graph_has_same_examined_paths_with_existing_node_limit(self):
        land=load_land(ROOT/'fixtures/vinga-land-expanded-20261017.geojson',margin_m=10,review_bounds=(11.55,57.60,11.66,57.67))
        request=payload();a=to_local(**request['start']);b=to_local(**request['target'])
        result=generate_routes(a,b,land.obstacles,
            SearchPolicy(clearance_m=5,max_nodes=26,max_candidates=8,max_expansions=1000),node_radius_m=900)
        previous=json.loads((ROOT/'artifacts/native-candidate-budget/result.json').read_text())
        self.assertEqual(result.node_count,21);self.assertEqual(len(land.obstacles),24)
        old=previous['geometry_search']
        self.assertEqual(list(result.lengths_m),old['lengths_m'])
        from dataclasses import asdict
        self.assertEqual(json.loads(json.dumps([asdict(c) for c in result.candidates])),old['candidates'])
        for route in result.candidates:
            points=(Vector(500,0),*route.waypoints,Vector(500,350))
            for a,b in zip(points,points[1:]):
                self.assertTrue(a.speed<=900 and b.speed<=900)
                self.assertFalse(any(o.intersects(a,b) for o in land.obstacles))

    def test_native_profile_rejects_synthetic_scenarios_and_internal_controls(self):
        request=payload() | {'profile':'vinga-native'}
        self.assertEqual(PlanInput(**request).profile,'vinga-native')
        for changes in ({'scenario':'weather-limit'},{'node_radius_m':1500},{'audit_node_limit':66},
                        {'weather_config':'arbitrary.json'}, {'candidate_limit':8}):
            with self.assertRaises(ValidationError):PlanInput(**(request | changes))
        old=scene();a,b=old['start'],old['target']
        blocked=calculate_geographic(request | dict(start=dict(longitude=a[0],latitude=a[1]),
            target=dict(longitude=b[0],latitude=b[1])))
        self.assertEqual(blocked['geometry_search']['status'],'endpoint_blocked')
        self.assertIsNone(blocked['planning']);self.assertEqual(blocked['alternatives'],[])
        self.assertIn('2026-10-13',old['departure'])


class NativeProfileHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_scene_standard_worker_full_routes_and_hard_hs(self):
        store=JobStore()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(store)),base_url='http://test') as client:
            try:
                s=(await client.get('/api/scene?profile=vinga-native')).json()
                self.assertIn('2026-10-17',s['departure']);self.assertEqual(len(s['obstacles']['features']),24)
                self.assertEqual(store.timeout,20);self.assertEqual(store.max_active,2)
                request=payload() | {'profile':'vinga-native','candidate_limit':4}
                for change in ({},{'candidate_limit':2,'departure_offsets_seconds':[0],'max_wave_height_m':.01}):
                    submitted=await client.post('/api/plans',json=request | change)
                    self.assertEqual(submitted.status_code,202,submitted.text)
                    key=submitted.json()['id']
                    for _ in range(500):
                        state=(await client.get('/api/plans/'+key)).json()
                        if state['status'] in ('completed','failed'):break
                        await asyncio.sleep(.05)
                    self.assertEqual(state['status'],'completed',state['reason'])
                    r=state['result'];self.assertEqual(r['geometry_search']['node_count'],21)
                    self.assertEqual(r['geometry_search']['policy']['max_nodes'],26)
                    self.assertEqual(r['geometry_search']['node_domain']['radius_m'],900)
                    self.assertEqual(r['weather_provenance']['source_qualification'],'unverified')
                    self.assertEqual(r['result_qualification'],'conditional_on_assumptions')
                    if change:
                        self.assertTrue(all(x['status']=='weather_limit' for x in r['alternatives']))
                        self.assertIsNone(r['alternative_comparison']['fastest_id'])
                    else:
                        self.assertEqual(len(r['alternatives']),16)
                        self.assertTrue(r['alternative_comparison']['same_winner'])
                        for x in r['alternatives']:
                            self.assertEqual(x['status'],'arrived')
                            self.assertEqual(x['weather_segment_status'],'verified')
                            self.assertEqual(x['arrival_weather_status'],'passed_at_arrival')
                        gpx=await client.get(f'/api/plans/{key}/routes/0-auto-0/gpx')
                        self.assertEqual(gpx.status_code,200)
                        self.assertNotIn('<trk',gpx.text)
            finally:await store.close()
