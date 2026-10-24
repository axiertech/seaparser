"""PoC API activation through the existing proxy, preserving the legacy demo API."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from deployment.prepare_vinga import ROOT,PUBLIC,SYSTEM_FILES,digest
from deployment.vinga_upgrade import tree_hashes,check_system
from application.geographic_budget import coastal_api_budget

CHECKOUT=Path('/home/web/seaparser/worktrees/real-map-data')
RUNTIME=Path('/home/web/seaparser/venvs/poc-'+digest(ROOT/'requirements.lock')[:12])
UNIT=Path('/etc/systemd/system/seaparser-poc-api.service')
PROXY=Path(SYSTEM_FILES['proxy'])
PREPARED=('unit-ready.service','proxy-before.conf','proxy-ready.conf','activate.sh')


def unit_for_release(before,release):
    ready='\n'.join('Description=SeaParser real-data PoC API' if line.startswith('Description=') else 'WorkingDirectory='+str(release) if line.startswith('WorkingDirectory=') else line.replace('/home/web/seaparser/app/.venv/bin/python',str(RUNTIME/'bin/python')).replace('--port 8765','--port 8766').replace('api.main:app','api.main:poc_app --factory') if line.startswith('ExecStart=') else line for line in before.splitlines())+'\n'
    if str(RUNTIME/'bin/python') not in ready or '--port 8766' not in ready or str(release) not in ready:raise ValueError('Unexpected installed service command')
    policy=coastal_api_budget()
    ready=ready.replace('MemoryMax=512M','MemoryMax='+str(policy['service_memory_mib'])+'M')
    return ready.replace('[Install]', 'Environment=OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1\nReadWritePaths=/home/web/seaparser/autonomy/cache/coastal-inputs-v1\n[Install]')


def proxy_for_poc(before):
    if '/api/poc/' in before or 'ProxyPass /api/ http://127.0.0.1:8765/api/' not in before:raise ValueError('Unexpected installed API proxy')
    return 'ProxyPass /api/poc/ http://127.0.0.1:8766/api/ connectiontimeout=2 timeout=25\nProxyPassReverse /api/poc/ http://127.0.0.1:8766/api/\n'+before


def runtime_check():
    code="from importlib.metadata import version; from pathlib import Path; import sys; assert sys.prefix==sys.argv[1]; lines=Path(sys.argv[1]+'/requirements.lock').read_text().splitlines(); pins=[s.split(' --hash=',1)[0].split('==') for s in lines if s and not s.startswith('#')]; assert all(version(n)==p for n,p in pins); import pyproj,uvicorn"
    command=[str(RUNTIME/'bin/python'),'-B','-c',code,str(RUNTIME)]
    if os.geteuid()==0:command=['/usr/sbin/runuser','-u','seaparser','--',*command]
    subprocess.run(command,check=True)


def prepare(stage):
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('Clean reviewed checkout required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='development/real-map-data':raise ValueError('Wrong branch')
    if UNIT.exists() or UNIT.is_symlink():raise ValueError('PoC service already exists; review its upgrade separately')
    stage.mkdir(mode=0o700,parents=True,exist_ok=False)
    release=Path('/home/web/seaparser/releases/poc-'+commit)
    subprocess.run(['git','archive','HEAD','--output='+str(stage/'source.tar')],cwd=ROOT,check=True)
    source=stage/'release';source.mkdir()
    with tarfile.open(stage/'source.tar') as archive:archive.extractall(source,filter='data')
    (stage/'unit-ready.service').write_text(unit_for_release(Path(SYSTEM_FILES['unit']).read_text(),release))
    before=PROXY.read_text();(stage/'proxy-before.conf').write_text(before);(stage/'proxy-ready.conf').write_text(proxy_for_poc(before))
    shutil.copyfile(ROOT/'deployment/activate-poc-api.sh',stage/'activate.sh')
    m=dict(checkout=str(CHECKOUT),commit=commit,release=str(release),runtime=str(RUNTIME),release_files=tree_hashes(source),
           system_before={k:digest(Path(v)) for k,v in SYSTEM_FILES.items()},public_before=tree_hashes(PUBLIC),prepared={n:digest(stage/n) for n in PREPARED})
    (stage/'manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    verify(stage);return {'prepared':True,'started':False,'commit':commit,'release':str(release),'root_command':'/bin/bash '+str(stage/'activate.sh')}


def verify(stage,*,runtime=True):
    m=json.loads((stage/'manifest.json').read_text())
    if m.get('checkout')!=str(CHECKOUT) or m['release']!='/home/web/seaparser/releases/poc-'+m['commit'] or m['runtime']!=str(RUNTIME):raise ValueError('Deployment identity mismatch')
    if set(m['prepared'])!=set(PREPARED):raise ValueError('Prepared file set mismatch')
    for n,h in m['prepared'].items():
        if digest(stage/n)!=h:raise ValueError('Prepared file changed')
    if (stage/'proxy-ready.conf').read_text()!=proxy_for_poc((stage/'proxy-before.conf').read_text()):raise ValueError('Proxy change exceeds PoC namespace')
    if runtime:
        if tree_hashes(stage/'release')!=m['release_files']:raise ValueError('Release changed')
        if digest(stage/'release/requirements.lock')!=digest(RUNTIME/'requirements.lock'):raise ValueError('Runtime lock mismatch')
        runtime_check()
    return m


def atomic_root_copy(source,target):
    if target.is_symlink():raise ValueError('Symlink blocks activation')
    pending=target.with_name(target.name+'.poc-pending');created=False
    try:
        with pending.open('xb') as stream:
            created=True;os.fchmod(stream.fileno(),0o644);stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
        os.replace(pending,target)
    finally:
        if created and pending.exists():pending.unlink()


def restored_state(stage,manifest):
    """Check disk AND systemd after daemon-reload, including leftover workers."""
    from datetime import datetime,timezone
    if UNIT.exists() or UNIT.is_symlink():raise ValueError('PoC unit still exists after rollback')
    check_system(manifest)
    r=subprocess.run(['/usr/bin/systemctl','show','seaparser-poc-api.service',
        '--property=LoadState,ActiveState,MainPID,ControlGroup'],capture_output=True,text=True)
    fields=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    if (r.returncode not in (0,1,4) or fields.get('LoadState')!='not-found'
            or fields.get('ActiveState') not in ('inactive','failed') or fields.get('MainPID')!='0'):
        raise ValueError('PoC manager state not cleared; daemon-reload/stop must finish: '+str(fields))
    group=fields.get('ControlGroup','')
    groups={'system.slice/seaparser-poc-api.service'}
    if group:groups.add(group.lstrip('/'))
    for name in groups:
        root=Path('/sys/fs/cgroup')/name
        if any(p.read_text().strip() for p in root.rglob('cgroup.procs')):
            raise ValueError('PoC cgroup still contains processes')
    if subprocess.check_output(['/usr/bin/ss','-H','-ltn','sport = :8766'],text=True).strip():
        raise ValueError('PoC port 8766 still has a listener')
    result={'verified':True,'commit':manifest['commit'],'systemd':fields,'port_8766':'not_listening',
            'worker_processes':'none in stopped PoC cgroup','checked_at':datetime.now(timezone.utc).isoformat()}
    (stage/'restoration-check.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def root_action(action,stage):
    if os.geteuid()!=0:raise ValueError('Run activation as root in the ordinary SSH terminal')
    with (stage/'activation.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);m=verify(stage,runtime=action not in ('restore','verify-restored'))
        if action=='verify-restored':return restored_state(stage,m)
        if action in ('preflight','install'):
            if subprocess.check_output(['/usr/sbin/runuser','-u','seaparser','--','git','-C',str(CHECKOUT),'rev-parse','HEAD'],text=True).strip()!=m['commit'] or subprocess.check_output(['/usr/sbin/runuser','-u','seaparser','--','git','-C',str(CHECKOUT),'status','--porcelain'],text=True).strip():raise ValueError('Reviewed checkout changed')
            ci=json.loads((stage/'ci-success.json').read_text())
            if ci.get('commit')!=m['commit'] or ci.get('conclusion')!='success':raise ValueError('Exact successful CI commit required')
            check_system(m)
            if UNIT.exists() or UNIT.is_symlink():raise ValueError('PoC unit already exists')
            if tree_hashes(PUBLIC)!=m['public_before']:raise ValueError('Public files changed; prepare fresh activation')
            if action=='preflight':return
            release=Path(m['release'])
            if not release.exists():shutil.copytree(stage/'release',release)
            if tree_hashes(release)!=m['release_files']:raise ValueError('Installed release differs; no service activated')
            atomic_root_copy(stage/'unit-ready.service',UNIT);atomic_root_copy(stage/'proxy-ready.conf',PROXY)
        elif action=='restore':
            if UNIT.is_symlink() or PROXY.is_symlink():raise ValueError('Symlink blocks rollback')
            if UNIT.exists() and digest(UNIT)!=m['prepared']['unit-ready.service']:raise ValueError('PoC service changed externally')
            if digest(PROXY) not in (m['system_before']['proxy'],m['prepared']['proxy-ready.conf']):raise ValueError('Proxy changed externally')
            atomic_root_copy(stage/'proxy-before.conf',PROXY)
            if UNIT.exists():UNIT.unlink()
        else:raise ValueError('Unknown action')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','verify','preflight','install','restore','verify-restored'));p.add_argument('stage',type=Path);a=p.parse_args()
    try:
        result=prepare(a.stage) if a.action=='prepare' else verify(a.stage) if a.action=='verify' else root_action(a.action,a.stage)
        if a.action in ('prepare','verify-restored'):print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError) as e:p.exit(1,str(e)+'\n')
