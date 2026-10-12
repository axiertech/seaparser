"""Bounded ephemeral job store; each calculation has a killable child process."""
import asyncio
from dataclasses import dataclass,field
import json
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]


class BusyError(ValueError):
    pass


@dataclass
class Job:
    status: str='queued'
    result: dict | None=None
    reason: str=''
    created: float=field(default_factory=monotonic)


class JobStore:
    def __init__(self,runner=None,timeout=20,max_active=2,max_jobs=8,ttl=300):
        self.runner=runner or self.compute
        self.timeout=timeout;self.max_active=max_active;self.max_jobs=max_jobs;self.ttl=ttl
        self.jobs={};self.tasks=set()

    def prune(self):
        now=monotonic()
        for key,job in list(self.jobs.items()):
            if job.status not in ('queued','running') and now-job.created > self.ttl:
                del self.jobs[key]

    def submit(self,payload):
        self.prune()
        if len(self.jobs)>=self.max_jobs or sum(j.status in ('queued','running') for j in self.jobs.values())>=self.max_active:
            raise BusyError('Beräkningskapaciteten är upptagen; försök igen senare')
        key=uuid4().hex;self.jobs[key]=Job()
        task=asyncio.create_task(self.run(key,payload));self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return key

    def get(self,key):
        self.prune()
        return self.jobs.get(key)

    async def run(self,key,payload):
        job=self.jobs[key];job.status='running'
        try:
            job.result=await asyncio.wait_for(self.runner(payload),self.timeout)
            job.status='completed'
        except TimeoutError:
            job.status='failed';job.reason='Beräkningens tidsgräns överskreds'
        except asyncio.CancelledError:
            job.status='failed';job.reason='Beräkningen avbröts';raise
        except Exception:
            job.status='failed';job.reason='Beräkningen misslyckades; ingen rutt godkänns'

    async def compute(self,payload):
        startup=asyncio.create_task(asyncio.create_subprocess_exec(sys.executable,'-B','-m','scripts.geographic_worker',
                    cwd=ROOT,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL))
        process=None
        try:
            # Cancellation during spawn must still obtain and reap the child.
            process=await asyncio.shield(startup)
            output,_=await process.communicate(json.dumps(payload,allow_nan=False).encode())
            if process.returncode or len(output)>8_000_000:
                raise ValueError('Beräkningsprocessen misslyckades')
            return json.loads(output)
        finally:
            if process is None:
                process=await startup
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()

    async def close(self):
        pending=tuple(self.tasks)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending,return_exceptions=True)
