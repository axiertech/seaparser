"""Regional HTTP/process acceptance; real land + estimated frozen weather."""
import asyncio
from datetime import datetime,timedelta
import unittest
from xml.etree.ElementTree import fromstring
import httpx
from api.main import create_app
from infrastructure.planning_jobs import JobStore
from infrastructure.land import load_land,to_local
from infrastructure.synthetic_forecast import synthetic_snapshot,PLAN
from application.geographic_plan import scene


class VingaApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store=JobStore()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(self.store)),base_url='http://test')
        self.scene=(await self.client.get('/api/scene?profile=vinga')).json()
        a,b=self.scene['start'],self.scene['target']
        self.payload={'profile':'vinga','start':{'latitude':a[1],'longitude':a[0]},
                      'target':{'latitude':b[1],'longitude':b[0]},'margin_m':10.0,'departure_offsets_seconds':[0]}

    async def asyncTearDown(self):
        await self.store.close(); await self.client.aclose()

    async def finished(self,payload):
        response=await self.client.post('/api/plans',json=payload)
        self.assertEqual(response.status_code,202,response.text)
        key=response.json()['id']
        for _ in range(500):
            state=(await self.client.get('/api/plans/'+key)).json()
            if state['status'] in ('completed','failed'):
                self.assertEqual(state['status'],'completed',state['reason'])
                return key,state['result']
            await asyncio.sleep(.05)
        self.fail('Regionalt jobb slutfördes inte inom begränsad väntan')

    async def test_detour_full_segments_arrival_and_gpx(self):
        key,result=await self.finished(self.payload|{'departure_offsets_seconds':[0,600]})
        self.assertEqual(result['land']['completeness'],'unknown')
        self.assertEqual(result['depth_status'],'unknown')
        self.assertEqual(result['navigational_safety'],'not_assessed')
        self.assertEqual(result['planning']['manifest']['dataset_id'],'seaparser-estimated-vinga-weather')
        shapes=load_land(margin_m=10).obstacles
        start=to_local(**self.payload['start']); target=to_local(**self.payload['target'])
        self.assertTrue(any(p.intersects(start,target) for p in shapes))
        arrived=[r for r in result['alternatives'] if r['status']=='arrived']
        self.assertEqual(len(arrived),4)
        for objective in ('fastest', 'comfortable'):
            self.assertTrue(any(r[objective] for r in arrived))
        for route in arrived:
            self.assertEqual(route['weather_segment_status'],'verified')
            self.assertEqual(route['arrival_weather_status'],'passed_at_arrival')
            self.assertGreater(len(route['waypoints']),2)
            positions=[to_local(lat,lon) for lon,lat in route['waypoints']]
            for a,b in zip(positions,positions[1:]):
                self.assertFalse(any(p.intersects(a,b) for p in shapes))
            expected=datetime.fromisoformat(route['departure_time'])+timedelta(seconds=route['travel_seconds'])
            self.assertLess(abs((datetime.fromisoformat(route['arrival_time'])-expected).total_seconds()),.00001)
        for feature in result['routes']['features']:
            if feature['properties']['kind']=='accepted' and feature['geometry']['type']=='LineString':
                positions=[to_local(lat,lon) for lon,lat in feature['geometry']['coordinates']]
                for a,b in zip(positions,positions[1:]):
                    self.assertFalse(any(p.intersects(a,b) for p in shapes))
        route=arrived[0]
        response=await self.client.get(f'/api/plans/{key}/routes/{route["id"]}/gpx')
        self.assertEqual(response.status_code,200)
        xml=fromstring(response.content);ns={'g':'http://www.topografix.com/GPX/1/1'}
        description=xml.find('g:metadata/g:desc',ns).text
        self.assertIn('Djup och landfullständighet okända',description)
        self.assertIn(result['land']['sha256'],description)
        points=xml.findall('g:rte/g:rtept',ns)
        self.assertEqual(len(points),len(route['waypoints']))
        for p,(lon,lat) in zip(points,route['waypoints']):
            self.assertAlmostEqual(float(p.attrib['lon']),lon,places=9)
            self.assertAlmostEqual(float(p.attrib['lat']),lat,places=9)
        self.assertFalse(xml.findall('g:trk',ns))
        self.assertFalse(xml.findall('.//g:ele',ns))
        self.assertFalse(xml.findall('.//g:extensions',ns))
        self.assertIn('Ej navigationssäkert', description)

    async def test_weather_and_gap_rejections_export_denied(self):
        for scenario,status in (('weather-limit','weather_limit'),('missing-waves','data_unavailable')):
            key,result=await self.finished(self.payload|{'scenario':scenario})
            self.assertTrue(result['alternatives'])
            self.assertTrue(all(r['status']==status for r in result['alternatives']))
            identifier=result['alternatives'][0]['id']
            response=await self.client.get(f'/api/plans/{key}/routes/{identifier}/gpx')
            self.assertEqual(response.status_code,422)

    async def test_region_validation_and_synthetic_scene_preserved(self):
        self.assertEqual((await self.client.get('/api/scene')).json(),scene())
        self.assertEqual((await self.client.get('/api/scene?profile=unknown')).status_code,422)
        for change in ({'profile':'unknown'},{'profile':'synthetic'},
                       {'start':{'latitude':57.64,'longitude':11.605}},{'margin_m':11},
                       {'departure_offsets_seconds':[0,600,1200]}):
            response=await self.client.post('/api/plans',json=self.payload|change)
            self.assertEqual(response.status_code,422)
        self.assertEqual(self.store.jobs,{})

    def test_regional_forecast_is_frozen_and_traceable(self):
        dataset=synthetic_snapshot(regional=True)
        self.assertEqual(dataset.version,'vinga-v1-baseline')
        self.assertEqual(dataset.dataset_id,'seaparser-estimated-vinga-weather')
        for product in dataset.products:
            self.assertLess(product.metadata.issued_at,PLAN)
            self.assertEqual(product.metadata.coverage.origin_latitude,57.633)
            self.assertEqual(product.metadata.coverage.origin_longitude,11.605)
            self.assertIn('syntetiska',product.metadata.source)

    async def test_land_endpoint_is_rejected_without_navigability_claim(self):
        key,result=await self.finished(self.payload|{'start':{'latitude':57.633,'longitude':11.605}})
        self.assertEqual(result['geometry_search']['status'],'endpoint_blocked')
        self.assertIsNone(result['planning'])
        self.assertEqual(result['alternatives'],[])
        self.assertEqual(result['navigational_safety'],'not_assessed')
        self.assertEqual((await self.client.get(f'/api/plans/{key}/routes/none/gpx')).status_code,422)
