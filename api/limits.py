"""Bound incoming planning bodies before JSON validation; no unbounded buffering."""
import asyncio
from starlette.responses import JSONResponse


class BodyLimit:
    def __init__(self,app,max_bytes=8192):
        self.app=app;self.max_bytes=max_bytes

    async def __call__(self,scope,receive,send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope,receive,send)
        body=bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message=await receive()
                    if message['type'] != 'http.request':
                        return
                    chunk=message.get('body',b'')
                    if len(body)+len(chunk)>self.max_bytes:
                        return await JSONResponse({'detail':'För stor begäran'},status_code=413)(scope,receive,send)
                    body.extend(chunk)
                    if not message.get('more_body',False):
                        break
        except TimeoutError:
            return await JSONResponse({'detail':'Begäran tog för lång tid'},status_code=408)(scope,receive,send)
        sent=False
        async def replay():
            nonlocal sent
            if sent:
                return await receive()
            sent=True
            return {'type':'http.request','body':bytes(body),'more_body':False}
        await self.app(scope,replay,send)
