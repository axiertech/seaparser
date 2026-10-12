"""Independent coordinate references and HTTP → child process → geometry → GPX."""
import asyncio
from math import radians,sin,sqrt
import unittest
from xml.etree.ElementTree import fromstring
import httpx
from api.main import create_app
from application.geographic_plan import scene
from infrastructure.geography import to_local,to_geo,network
from infrastructure.planning_jobs import JobStore,BusyError
from prototype.model import Vector


class GeographicReferenceTests(unittest.TestCase):
    def test_independent_geod_direct_reference(self):
        # System geod +ellps=WGS84 direct solutions, not inverse/forward roundtrip.
        for latitude,longitude,east,north in ((57.999999988763,11.001691107052,100,0),
                                            (58.003174224454,11.005979495474,500/sqrt(2),500/sqrt(2)),
                                            (57.991919378923,11,0,-900)):
            p=to_local(latitude,longitude)
            self.assertAlmostEqual(p.east,east,delta=.00001)
            self.assertAlmostEqual(p.north,north,delta=.00001)

    def test_independent_meridian_integral_and_roundtrip(self):
        a=6378137;f=1/298.257223563;e2=f*(2-f)
        lo=radians(58);hi=radians(58.004);steps=1000;h=(hi-lo)/steps
        def radius(phi):
            return a*(1-e2)/(1-e2*sin(phi)**2)**1.5
        reference=h/3*(radius(lo)+radius(hi)+sum((4 if i%2 else 2)*radius(lo+i*h) for i in range(1,steps)))
        self.assertAlmostEqual(to_local(58.004,11).north,reference,delta=.000001)
        for p in (Vector(0,0),Vector(-50,-50),Vector(150,50),Vector(700,500)):
            lon,lat=to_geo(p)
            self.assertLess((to_local(lat,lon)-p).speed,.00001)
            self.assertAlmostEqual(lon,11,delta=.03)
            self.assertAlmostEqual(lat,58,delta=.02)
        self.assertFalse(network.is_network_enabled())

    def test_region_nonfinite_axis_order_and_limits(self):
        for lat,lon in ((11,58),(90,11),(58,180),(58.02,11),(float('nan'),11),(True,11)):
            with self.assertRaises(ValueError):
                to_local(lat,lon)
        with self.assertRaises(ValueError):
            to_geo(Vector(1001,0))


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store=JobStore();self.app=create_app(self.store)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test')
        s=scene();a,b=s['start'],s['target']
        self.payload={'start':{'latitude':a[1],'longitude':a[0]},'target':{'latitude':b[1],'longitude':b[0]},'departure_offsets_seconds':[0]}

    async def asyncTearDown(self):
        await self.store.close();await self.client.aclose()

    async def finished(self,payload):
        response=await self.client.post('/api/plans',json=payload)
        self.assertEqual(response.status_code,202)
        key=response.json()['id']
        for _ in range(150):
            job=(await self.client.get('/api/plans/'+key)).json()
            if job['status'] in ('completed','failed'):
                return key,job
            await asyncio.sleep(.03)
        self.fail('Jobbet slutfördes inte')

    async def test_real_process_geojson_and_gpx(self):
        key,job=await self.finished(self.payload|{'margin_m':3})
        self.assertEqual(job['status'],'completed',job['reason'])
        result=job['result'];self.assertTrue(result['synthetic'])
        self.assertEqual(result['obstacles']['features'][0]['properties']['margin_m'],3)
        arrived=[r for r in result['alternatives'] if r['status']=='arrived']
        self.assertTrue(arrived)
        self.assertTrue(all(r['weather_segment_status']=='verified' for r in arrived))
        self.assertEqual(result['planning']['manifest']['boat']['model'],'PolarBoat')
        for feature in result['routes']['features']:
            if feature['geometry']['type']=='Point':
                lon,lat=feature['geometry']['coordinates']
                self.assertAlmostEqual(lon,11,delta=.003);self.assertAlmostEqual(lat,58,delta=.002)
        route=arrived[0]
        response=await self.client.get(f'/api/plans/{key}/routes/{route["id"]}/gpx')
        self.assertEqual(response.status_code,200)
        xml=fromstring(response.content);ns={'g':'http://www.topografix.com/GPX/1/1'}
        points=xml.findall('g:rte/g:rtept',ns)
        self.assertEqual(len(points),len(route['waypoints']))
        self.assertFalse(xml.findall('g:trk',ns))
        for point,(lon,lat) in zip(points,route['waypoints']):
            self.assertAlmostEqual(float(point.attrib['lat']),lat,places=9)
            self.assertAlmostEqual(float(point.attrib['lon']),lon,places=9)

    async def test_invalid_requests_and_body_work_limits(self):
        for change in ({'extra':1},{'margin_m':-1},{'margin_m':11},{'margin_m':True},
                       {'departure_offsets_seconds':[0,600,0]}, {'departure_offsets_seconds':[300]},
                       {'start':{'latitude':11,'longitude':58}}):
            response=await self.client.post('/api/plans',json=self.payload|change)
            self.assertEqual(response.status_code,422)
        response=await self.client.post('/api/plans',content=b'x'*8193)
        self.assertEqual(response.status_code,413)
        self.assertEqual(self.store.jobs,{})

    async def test_weather_failure_and_no_gpx(self):
        key,job=await self.finished(self.payload|{'scenario':'weather-limit'})
        self.assertEqual(job['status'],'completed')
        self.assertTrue(all(r['status']=='weather_limit' for r in job['result']['alternatives']))
        identifier=job['result']['alternatives'][0]['id']
        response=await self.client.get(f'/api/plans/{key}/routes/{identifier}/gpx')
        self.assertEqual(response.status_code,422)
        self.assertEqual((await self.client.get('/api/plans/missing')).status_code,404)

    async def test_health_remains_responsive_during_job_and_busy(self):
        event=asyncio.Event()
        async def slow(payload):
            await event.wait();return {}
        store=JobStore(runner=slow,max_active=1)
        client=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(store)),base_url='http://test')
        try:
            response=await client.post('/api/plans',json=self.payload);self.assertEqual(response.status_code,202)
            self.assertEqual((await client.get('/api/health')).status_code,200)
            self.assertEqual((await client.post('/api/plans',json=self.payload)).status_code,429)
            key=response.json()['id']
            self.assertEqual((await client.get(f'/api/plans/{key}/routes/0/gpx')).status_code,409)
        finally:
            await store.close();await client.aclose()

    async def test_process_timeout_terminates_child(self):
        store=JobStore(timeout=.001)
        key=store.submit(self.payload)
        for _ in range(100):
            if store.get(key).status == 'failed':
                break
            await asyncio.sleep(.02)
        self.assertEqual(store.get(key).status,'failed')
        self.assertIn('tidsgräns',store.get(key).reason)
        await store.close()
