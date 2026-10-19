"""Thin HTTP interface to bounded planning jobs; no route calculations here."""
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI,HTTPException,Response
from application.geographic_plan import scene
from infrastructure.planning_jobs import JobStore,BusyError
from presentation.gpx import export_gpx,export_estimated_coastal_gpx
from .models import PlanInput,CoastalPlanInput
from .limits import BodyLimit


def create_app(store=None,*,resource_profile='local',coastal_store=None):
    from application.geographic_budget import resource_budget,coastal_api_budget
    resources=resource_budget(resource_profile)
    jobs=store or JobStore(timeout=resources['job_seconds'],max_result_bytes=resources['result_bytes'],
                          max_active=1 if resource_profile=='regional' else 2,
                          max_jobs=2 if resource_profile=='regional' else 8)
    from time import monotonic
    policy=coastal_api_budget()
    regional=coastal_store or JobStore(timeout=policy['job_seconds'],max_active=policy['max_active'],
        max_jobs=policy['max_jobs'],ttl=policy['ttl_seconds'],max_result_bytes=policy['result_bytes'],
        worker_module='scripts.coastal_worker')
    active=lambda store:any(j.status in ('queued','running') for j in store.jobs.values())
    @asynccontextmanager
    async def lifespan(app):
        yield
        await jobs.close()
        await regional.close()
    app=FastAPI(title='SeaParser utvecklingsplanering med verkliga väderdata',lifespan=lifespan,docs_url=None,redoc_url=None)
    app.add_middleware(BodyLimit)

    @app.get('/api/health')
    async def health():
        return {'status':'ok','synthetic':False}

    @app.get('/api/scene')
    async def get_scene(profile:Literal['synthetic','vinga','vinga-native','vinga-poc']='vinga'):
        return scene(profile)

    @app.post('/api/plans',status_code=202)
    async def create_plan(request:PlanInput):
        try:
            if active(regional):raise BusyError('En regional beräkning pågår; försök igen när den är klar')
            key=jobs.submit(request.model_dump())
        except BusyError as error:
            raise HTTPException(429,str(error),headers={'Retry-After':'2'}) from error
        return {'id':key,'status':'queued','status_url':'/api/plans/'+key,'server_timeout_seconds':jobs.timeout,'poll_timeout_seconds':jobs.timeout+10}

    @app.get('/api/coastal/scene')
    async def coastal_scene():
        from application.coastal_presentation import coastal_coverage
        return {**coastal_coverage(),'profile':'vinga-uddevalla',
            'qualification':'estimated_high_uncertainty','weather_limits_verified':False,
            'server_timeout_seconds':regional.timeout,'max_active':regional.max_active,
            'performance_target_seconds':policy['performance_target_seconds']}

    @app.post('/api/coastal/plans',status_code=202)
    async def create_coastal_plan(request:CoastalPlanInput):
        try:
            if active(jobs):raise BusyError('Beräkningskapaciteten är upptagen; försök igen senare')
            key=regional.submit(request.model_dump())
        except BusyError as error:
            raise HTTPException(429,str(error),headers={'Retry-After':'5'}) from error
        return {'id':key,'status':'queued','server_timeout_seconds':regional.timeout,
                'poll_timeout_seconds':regional.timeout+15}

    def regional_job(key):
        found=regional.get(key)
        if found is None:raise HTTPException(404,'Jobbet saknas eller har gått ut; beräkna på nytt')
        return found

    @app.get('/api/coastal/plans/{key}')
    async def get_coastal_plan(key:str):
        found=regional_job(key)
        return {'id':key,'status':found.status,'reason':found.reason,'result':found.result,
                'elapsed_seconds':round(monotonic()-found.created,1),'server_timeout_seconds':regional.timeout}

    @app.get('/api/coastal/plans/{key}/routes/{route_id}/gpx')
    async def coastal_download(key:str,route_id:str):
        found=regional_job(key)
        if found.status!='completed':raise HTTPException(409,'Beräkningen är inte slutförd')
        try:content=export_estimated_coastal_gpx(found.result,route_id)
        except ValueError as error:raise HTTPException(422,str(error)) from error
        return Response(content,media_type='application/gpx+xml',headers={
            'Content-Disposition':'attachment; filename="seaparser-regional-estimate.gpx"'})

    def job(key):
        found=jobs.get(key)
        if found is None:
            raise HTTPException(404,'Jobbet saknas eller har gått ut')
        return found

    @app.get('/api/plans/{key}')
    async def get_plan(key:str):
        found=job(key)
        return {'id':key,'status':found.status,'reason':found.reason,'result':found.result}

    @app.get('/api/plans/{key}/routes/{route_id}/gpx')
    async def download(key:str,route_id:str):
        found=job(key)
        if found.status!='completed':
            raise HTTPException(409,'Beräkningen är inte slutförd')
        try:
            content=export_gpx(found.result,route_id)
        except ValueError as error:
            raise HTTPException(422,str(error)) from error
        return Response(content,media_type='application/gpx+xml',headers={'Content-Disposition':'attachment; filename="seaparser-plan.gpx"'})
    return app


app=create_app()


def poc_app():
    """Use the PoC's regional result/time budgets for its existing Vinga jobs."""
    return create_app(resource_profile='regional')
