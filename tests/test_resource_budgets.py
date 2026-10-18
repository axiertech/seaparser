"""Multiday simulation and bounded memory are independent of server wall time."""
import asyncio,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import xarray as xr
from application.geographic_budget import resource_budget,available_voyage_seconds
from scripts.audit_copernicus import finite_statistics
from infrastructure.planning_jobs import JobStore
from prototype.environment import SyntheticEnvironment,Conditions
from prototype.model import Vector,KNOT
from prototype.routes import compare_routes,RouteCandidate


class ResourceBudgetTests(unittest.TestCase):
    def test_multiday_known_distance_uses_simulated_not_server_seconds(self):
        start=datetime(2026,10,18,tzinfo=timezone.utc);budget=resource_budget('offshore')
        seconds=available_voyage_seconds(budget,start,[0],start+timedelta(days=4))
        result=compare_routes(SyntheticEnvironment(lambda p,t:Conditions(Vector(0,0))),start,Vector(100000,0),
            (RouteCandidate('direct'),),speed_knots=1/KNOT,step_seconds=300,max_seconds=seconds,max_steps=budget['max_steps'])
        self.assertAlmostEqual(result.fastest.travel_seconds,100000,delta=.01)
        self.assertGreater(result.fastest.travel_seconds,86400);self.assertEqual(budget['job_seconds'],90)
    def test_decoded_fields_are_scanned_in_bounded_hyperslabs(self):
        values=np.ones((10,60,70),dtype='float32');values[0,0,0]=np.nan;values[-1,-1,-1]=np.nan
        report=finite_statistics(xr.DataArray(values,dims=('time','latitude','longitude')),4096)
        self.assertEqual(report['missing'],2);self.assertEqual(report['count'],42000)
        self.assertLessEqual(report['largest_decoded_chunk_bytes'],4096)
        with self.assertRaises(ValueError):finite_statistics(xr.DataArray(values),0)
    def test_invalid_budget_cannot_admit_nan_boolean_or_insufficient_steps(self):
        good=resource_budget()
        for changes in ({'job_seconds':True},{'result_bytes':0},{'step_seconds':float('nan')},{'max_steps':1}):
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'budget.json';p.write_text(json.dumps({'local':good|changes}))
                with self.assertRaises(ValueError):resource_budget(path=p)


class ResultBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_worker_output_limit_stops_before_unbounded_buffering(self):
        store=JobStore(max_result_bytes=32)
        try:
            key=store.submit({'profile':'synthetic','start':{'latitude':57.633,'longitude':11.605},'target':{'latitude':57.633,'longitude':11.606}})
            for _ in range(500):
                if store.get(key).status=='failed':break
                await asyncio.sleep(.01)
            self.assertEqual(store.get(key).status,'failed');self.assertIsNone(store.get(key).result)
        finally:await store.close()
