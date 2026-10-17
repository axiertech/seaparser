"""Thin HTTP interface to bounded planning jobs; no route calculations here."""
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI,HTTPException,Response
from application.geographic_plan import scene
from infrastructure.planning_jobs import JobStore,BusyError
from presentation.gpx import export_gpx
from .models import PlanInput
from .limits import BodyLimit


def create_app(store=None):
    jobs=store or JobStore()
    @asynccontextmanager
    async def lifespan(app):
        yield
        await jobs.close()
    app=FastAPI(title='SeaParser utvecklingsplanering med verkliga väderdata',lifespan=lifespan,docs_url=None,redoc_url=None)
    app.add_middleware(BodyLimit)

    @app.get('/api/health')
    async def health():
        return {'status':'ok','synthetic':False}

    @app.get('/api/scene')
    async def get_scene(profile:Literal['synthetic','vinga']='vinga'):
        return scene(profile)

    @app.post('/api/plans',status_code=202)
    async def create_plan(request:PlanInput):
        try:
            key=jobs.submit(request.model_dump())
        except BusyError as error:
            raise HTTPException(429,str(error),headers={'Retry-After':'2'}) from error
        return {'id':key,'status':'queued','status_url':'/api/plans/'+key}

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
