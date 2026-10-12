"""Explicit local review server, loopback only, with a strict public static root."""
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import uvicorn
from api.main import create_app


def main():
    app=create_app()
    app.mount('/',StaticFiles(directory=Path(__file__).resolve().parents[1]/'frontend/dist',html=True),name='public-demo')
    uvicorn.run(app,host='127.0.0.1',port=8765,workers=1,access_log=False)


if __name__=='__main__':
    main()
