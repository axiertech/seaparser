"""Explicit loopback review server; static roots selected from public builds only."""
import argparse
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import uvicorn
from api.main import create_app


def review_app(profile='synthetic'):
    if profile not in ('synthetic','vinga'):
        raise ValueError('Okänd granskningsprofil')
    directory=Path(__file__).resolve().parents[1]/'frontend'/('land-dist' if profile=='vinga' else 'dist')
    app=create_app()
    app.mount('/',StaticFiles(directory=directory,html=True),name='public-demo')
    return app


def regional_app():
    return review_app('vinga')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=('synthetic','vinga'),default='synthetic')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 0<=args.port<=65535:
        parser.error('port måste ligga mellan 0 och 65535')
    uvicorn.run(review_app(args.profile),host='127.0.0.1',port=args.port,workers=1,access_log=False)


if __name__=='__main__':
    main()
