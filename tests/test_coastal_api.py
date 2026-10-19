"""Free regional HTTP jobs retain known-current results, barriers and export gates."""
import asyncio
import unittest
from unittest.mock import patch
from xml.etree.ElementTree import fromstring

import httpx
from api.main import create_app
from application.coastal_plan import plan_coastal
from application.coastal_presentation import coastal_view
from infrastructure.planning_jobs import JobStore
from tests import test_coastal_free_plan


class CoastalApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env,self.config,self.payload=test_coastal_free_plan.CoastalFreePlanTests().setup_plan()
        self.coverage={'bbox':[11,57,13,59],'valid_times':[self.env.start.isoformat(),self.env.end.isoformat()],'reference_time':self.env.start.isoformat()}
        self.cover=patch('application.coastal_presentation.coastal_coverage',return_value=self.coverage);self.cover.start()
        async def calculate(payload):
            with patch('application.coastal_plan.load_coastal_weather',return_value=(self.env,self.config,{},{})):
                return coastal_view(plan_coastal('reference-test',payload),allow_empty=True)
        self.regional=JobStore(runner=calculate,timeout=3,max_active=1,max_jobs=2)
        self.local=JobStore()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(self.local,coastal_store=self.regional)),base_url='http://test')

    async def asyncTearDown(self):
        await self.regional.close();await self.local.close();await self.client.aclose();self.cover.stop()

    async def finished(self,payload):
        r=await self.client.post('/api/coastal/plans',json=payload);self.assertEqual(r.status_code,202,r.text)
        key=r.json()['id']
        for _ in range(100):
            state=(await self.client.get('/api/coastal/plans/'+key)).json()
            if state['status'] in ('completed','failed'):return key,state
            await asyncio.sleep(.01)
        self.fail('Regional job did not finish')

    async def test_http_known_current_voyage_and_self_contained_uncertain_gpx(self):
        key,state=await self.finished(self.payload)
        self.assertEqual(state['status'],'completed',state['reason']);self.assertIn('elapsed_seconds',state)
        result=state['result'];route=result['routes'][0]
        self.assertAlmostEqual(route['travel_seconds'],2000/(5*1852/3600+1),delta=.01)
        self.assertFalse(result['weather_limits_verified']);self.assertTrue(result['reserve_evidence']['segments'])
        gpx=await self.client.get(f'/api/coastal/plans/{key}/routes/{route["id"]}/gpx')
        self.assertEqual(gpx.status_code,200);xml=fromstring(gpx.content)
        ns={'g':'http://www.topografix.com/GPX/1/1','sp':'https://seaparser.com/ns/estimate/1'}
        self.assertEqual(xml.findtext('g:metadata/g:extensions/sp:weather_limits_verified',namespaces=ns),'false')
        points=xml.findall('g:rte/g:rtept',ns);self.assertGreaterEqual(len(points),2)
        self.assertAlmostEqual(float(points[0].get('lat')),self.payload['start']['latitude'],places=9)
        self.assertEqual(xml.findall('g:trk',ns),[])

    async def test_weather_failure_never_creates_an_exportable_route(self):
        key,state=await self.finished(self.payload|{'max_wave_height_m':.1})
        self.assertEqual(state['status'],'completed');self.assertEqual(state['result']['routes'],[])
        self.assertTrue(state['result']['failures'])
        self.assertEqual((await self.client.get(f'/api/coastal/plans/{key}/routes/water-0/gpx')).status_code,422)

    async def test_bad_points_departures_and_resource_overrides_rejected_before_allocation(self):
        for changes in ({'start':{'latitude':0,'longitude':0}},{'departure':'2026-10-18T00:00:00'},
            {'departure':self.env.end.isoformat()},{'candidate_limit':3},{'job_seconds':1000},
            {'max_wind_m_s':True},{'margin_m':0},{'boat_profile':'invented'}):
            with self.subTest(changes=changes):
                self.assertEqual((await self.client.post('/api/coastal/plans',json=self.payload|changes)).status_code,422)
        self.assertFalse(self.regional.jobs)

    async def test_shared_capacity_keeps_poll_and_health_responsive(self):
        event=asyncio.Event()
        async def slow(payload):await event.wait();return {}
        self.regional.runner=slow
        r=await self.client.post('/api/coastal/plans',json=self.payload);self.assertEqual(r.status_code,202)
        self.assertEqual((await self.client.post('/api/coastal/plans',json=self.payload)).status_code,429)
        self.assertEqual((await self.client.get('/api/health')).status_code,200)
        key=r.json()['id'];self.assertIn((await self.client.get('/api/coastal/plans/'+key)).json()['status'],('queued','running'))
        payload={'profile':'synthetic','start':{'latitude':58,'longitude':11},'target':{'latitude':58.001,'longitude':11}}
        self.assertEqual((await self.client.post('/api/plans',json=payload)).status_code,429)
        self.assertEqual((await self.client.get(f'/api/coastal/plans/{key}/routes/water-0/gpx')).status_code,409)

    async def test_completed_result_eviction_admits_following_users_with_bounded_memory(self):
        self.regional.runner=lambda payload:asyncio.sleep(0,result={})
        keys=[]
        for _ in range(3):
            key,state=await self.finished(self.payload);keys.append(key);self.assertEqual(state['status'],'completed')
        self.assertEqual(len(self.regional.jobs),2)
        self.assertEqual((await self.client.get('/api/coastal/plans/'+keys[0])).status_code,404)
        self.assertEqual((await self.client.get('/api/coastal/plans/'+keys[-1])).status_code,200)

    async def test_cancel_reaps_real_worker_before_next_job_and_gpx(self):
        import os
        original=asyncio.create_subprocess_exec;children=[]
        async def spawn(*args,**kwargs):
            child=await original(*args,**kwargs);children.append(child);return child
        reference=self.regional.runner
        for store,path,payload in ((self.regional,'/api/coastal/plans',self.payload),
            (self.local,'/api/plans',{'profile':'synthetic','start':{'latitude':58,'longitude':11},'target':{'latitude':58.001,'longitude':11}})):
            with self.subTest(path=path),patch('infrastructure.planning_jobs.asyncio.create_subprocess_exec',side_effect=spawn):
                store.runner=store.compute;before=len(children)
                response=await self.client.post(path,json=payload);self.assertEqual(response.status_code,202)
                key=response.json()['id']
                for _ in range(100):
                    if len(children)>before:break
                    await asyncio.sleep(.01)
                self.assertGreater(len(children),before)
                cancelled=await asyncio.gather(self.client.delete(path+'/'+key),self.client.delete(path+'/'+key))
                self.assertTrue(all(r.status_code==200 and r.json()['active'] is False for r in cancelled))
                child=children[-1];self.assertIsNotNone(child.returncode)
                with self.assertRaises(ProcessLookupError):os.kill(child.pid,0)
                self.assertFalse(store.tasks_by_key)
                self.assertEqual((await self.client.get('/api/health')).json()['active_jobs'],{'local':0,'regional':0})
        self.regional.runner=reference
        key,state=await self.finished(self.payload);self.assertEqual(state['status'],'completed')
        route=state['result']['routes'][0]
        self.assertEqual((await self.client.get(f'/api/coastal/plans/{key}/routes/{route["id"]}/gpx')).status_code,200)

    async def test_cancel_before_start_does_not_leave_queued_capacity(self):
        called=[]
        async def runner(payload):called.append(True);return {}
        self.regional.runner=runner
        key=self.regional.submit(self.payload)
        await self.regional.cancel(key)
        self.assertFalse(called);self.assertEqual(self.regional.get(key).status,'failed')
        self.assertFalse(self.regional.tasks_by_key)
        _,state=await self.finished(self.payload);self.assertEqual(state['status'],'completed')
