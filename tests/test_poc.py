"""Functional PoC uses the existing calculation, source data and hard limits."""
import json
from pathlib import Path
import unittest
from pydantic import ValidationError
from api.models import PlanInput
from application.geographic_plan import calculate_geographic,scene
from application.poc import local_position,route_metrics
from infrastructure.land import to_geo
from prototype.model import Vector

ROOT=Path(__file__).resolve().parents[1]


class PocTests(unittest.TestCase):
    def test_profile_reuses_projected_motion_and_expanded_real_inputs(self):
        s=scene('vinga-poc')
        self.assertEqual(len(s['places']),3)
        self.assertEqual(len(s['land_display']['features']),24)
        self.assertEqual(s['weather_provenance']['motion_frame'],'wgs84-aeqd-proj-differential-v1')
        self.assertEqual(s['boat_profiles'][0]['id'],'constant-5kn')
        self.assertTrue(s['boat_profiles'][0]['estimated'])
        self.assertIn('2026-10-17',s['departure'])

    def test_poC_coordinates_use_real_900m_support_not_legacy_bbox(self):
        longitude,latitude=to_geo(Vector(700,100))
        self.assertAlmostEqual(local_position(latitude,longitude).east,700,delta=1e-6)
        for lat,lon in ((float('nan'),11.605),(57.633,181)):
            with self.assertRaises(ValueError):local_position(lat,lon)
        longitude,latitude=to_geo(Vector(901,0))
        with self.assertRaises(ValueError):local_position(latitude,longitude)

    def test_fixed_boat_and_existing_work_budgets_are_enforced(self):
        s=scene('vinga-poc');a,b=s['places'][:2]
        request=dict(profile='vinga-poc',start={k:a[k] for k in ('longitude','latitude')},target={k:b[k] for k in ('longitude','latitude')},candidate_limit=4,departure_offsets_seconds=[0,600,3600,10800],boat_profile='constant-5kn')
        self.assertEqual(PlanInput(**request).boat_profile,'constant-5kn')
        for changes in ({'boat_profile':'invented'},{'candidate_limit':8},{'scenario':'weather-limit'},{'motion_frame':'arbitrary'}):
            with self.assertRaises(ValidationError):PlanInput(**(request|changes))
        with self.assertRaises(ValueError):calculate_geographic(request|{'boat_profile':'invented'})

    def test_metric_integration_never_fills_missing_weather(self):
        route={'legs':[{'steps':[{'start':{'time':'2026-10-17T01:00:00+00:00'},'end_time':'2026-10-17T01:00:10+00:00','midpoint':{'ground':{'east':3,'north':4},'wind':None,'current':{'east':0,'north':1},'waves':{'height_m':.5}}}]}]}
        metrics=route_metrics(route)
        self.assertEqual(metrics['distance_m'],50)
        self.assertEqual(metrics['weather_summary']['wind_m_s']['missing_samples'],1)
        self.assertIsNone(metrics['weather_summary']['wind_m_s']['max'])
        self.assertEqual(metrics['weather_summary']['current_m_s']['max'],1)
        self.assertIsNone(route_metrics({'legs':[]})['distance_m'])

    def test_published_catalog_has_real_traces_and_no_export_for_failed_routes(self):
        root=ROOT/'artifacts/poc-site';catalog=json.loads((root/'catalog.json').read_text())
        self.assertEqual(len(catalog['cases']),18)
        for key,entry in catalog['cases'].items():
            result=json.loads((root/entry['file']).read_text())
            self.assertEqual(result['input_sha256'],entry['input_sha256'])
            self.assertEqual(result['weather_provenance']['source_qualification'],'unverified')
            self.assertEqual(len(result['obstacles']['features']),24)
            self.assertEqual(result['result_qualification'],'conditional_on_assumptions')
            for r in result['alternatives']:
                file=root/'gpx'/f'{key}-{r["id"]}.gpx'
                if r['status']=='arrived':
                    self.assertGreater(r['distance_m'],0);self.assertTrue(file.is_file())
                    self.assertIn('rtept',file.read_text())
                else:self.assertFalse(file.exists())


class PocApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_worker_poc_selection_metrics_and_gpx(self):
        import asyncio,httpx
        from api.main import create_app
        from infrastructure.planning_jobs import JobStore
        store=JobStore()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(store)),base_url='http://test') as client:
            try:
                response=await client.get('/api/scene?profile=vinga-poc');self.assertEqual(response.status_code,200)
                s=response.json();a,b=s['places'][:2]
                a=a|{'latitude':a['latitude']+.0001,'longitude':a['longitude']+.0001};b=b|{'latitude':b['latitude']-.0001,'longitude':b['longitude']+.0001}
                request=dict(profile='vinga-poc',start={k:a[k] for k in ('longitude','latitude')},target={k:b[k] for k in ('longitude','latitude')},candidate_limit=4,departure_offsets_seconds=[0],boat_profile='constant-5kn',margin_m=10)
                created=await client.post('/api/plans',json=request);self.assertEqual(created.status_code,202,created.text)
                key=created.json()['id']
                for _ in range(500):
                    state=(await client.get('/api/plans/'+key)).json()
                    if state['status'] in ('completed','failed'):break
                    await asyncio.sleep(.05)
                self.assertEqual(state['status'],'completed',state['reason'])
                result=state['result'];self.assertEqual(result['profile'],'vinga-poc')
                self.assertTrue(result['weather_provenance']['motion_frame'])
                arrived=next(r for r in result['alternatives'] if r['status']=='arrived')
                self.assertGreater(arrived['distance_m'],0);self.assertIsNotNone(arrived['weather_summary']['wind_m_s']['max'])
                gpx=await client.get(f'/api/plans/{key}/routes/{arrived["id"]}/gpx');self.assertEqual(gpx.status_code,200)
                self.assertIn('rtept',gpx.text)
                self.assertEqual(store.timeout,20);self.assertEqual(store.max_active,2)
            finally:await store.close()
