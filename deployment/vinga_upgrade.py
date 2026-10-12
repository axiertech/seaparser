"""Content-verified root upgrade/restore. No permissions, Apache, TLS or DB edits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import os
import stat
try:
    from .prepare_vinga import verify,digest,SYSTEM_FILES,PUBLIC,ROOT
except ImportError:
    from prepare_vinga import verify,digest,SYSTEM_FILES,PUBLIC,ROOT


def tree_hashes(root):
    return {p.relative_to(root).as_posix():digest(p) for p in root.rglob('*') if p.is_file()}


def check_system(manifest):
    for kind,path in SYSTEM_FILES.items():
        p=Path(path)
        if p.stat().st_uid!=0 or digest(p)!=manifest['system_before'][kind]:
            raise ValueError('Systemfil avviker från verifierad deployment: '+kind)


def check_backup(manifest):
    backup=Path(manifest['backup'])
    if tree_hashes(backup/'public-before')!=manifest['public_before']:
        raise ValueError('Publik backup avviker')
    for kind,expected in manifest['system_before'].items():
        if digest(backup/(kind+'-before'))!=expected:
            raise ValueError('Systembackup avviker: '+kind)


def preflight(stage,manifest):
    head=subprocess.check_output(['/usr/sbin/runuser','-u','seaparser','--','/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['/usr/sbin/runuser','-u','seaparser','--','/usr/bin/git','-C',str(ROOT),'status','--porcelain'],text=True).strip()
    if head!=manifest['commit'] or dirty:
        raise ValueError('Granskad checkout har ändrats')
    check_system(manifest)
    modules=subprocess.check_output(['/usr/sbin/apache2ctl','-M'],text=True,stderr=subprocess.PIPE)
    if not all(name in modules for name in ('proxy_module','proxy_http_module')):
        raise ValueError('Befintliga nödvändiga Apache-moduler saknas')
    pid=subprocess.check_output(['/usr/bin/systemctl','show','seaparser-api.service','--property=MainPID','--value'],text=True).strip()
    listeners=subprocess.check_output(['/usr/bin/ss','-H','-ltnp','sport = :8765'],text=True)
    if not pid.isdigit() or pid=='0' or ('pid='+pid+',') not in listeners or Path('/proc/'+pid).stat().st_uid!=1000:
        raise ValueError('Port 8765 tillhör inte verifierad seaparser-tjänst')
    for name,attrs in manifest['public_attributes'].items():
        info=(PUBLIC/name).stat()
        if {'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode)}!=attrs:
            raise ValueError('Publika filattribut har ändrats')
    if tree_hashes(PUBLIC)!=manifest['public_before']:
        raise ValueError('Nuvarande publicering har ändrats; ny backup/granskning krävs')
    ready={name.removeprefix('public-ready/'):sha for name,sha in manifest['prepared'].items() if name.startswith('public-ready/')}
    if any((PUBLIC/name).exists() and name not in manifest['public_before'] for name in ready):
        raise ValueError('Ny publiceringsfil kolliderar med tidigare okänd fil')
    if digest(ROOT/'requirements.lock')!=digest(Path('/home/web/seaparser/app/requirements.lock')):
        raise ValueError('Ny release kräver annan Pythonmiljö; stoppar')


def backup(stage,manifest):
    preflight(stage,manifest)
    target=Path(manifest['backup'])
    if target.exists():
        check_backup(manifest); return
    target.mkdir(parents=True)
    for name in manifest['public_before']:
        out=target/'public-before'/name;out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(PUBLIC/name,out)
    for kind,path in SYSTEM_FILES.items():
        shutil.copyfile(path,target/(kind+'-before'))
    shutil.copyfile(stage/'manifest.json',target/'manifest.json')
    check_backup(manifest)


def install(stage,manifest):
    check_backup(manifest)
    release=Path(manifest['release'])
    if release.exists():
        if tree_hashes(release)!=manifest['release_files']:
            raise ValueError('Befintlig release avviker; skriv inte över')
    else:
        release.mkdir(parents=True)
        with tarfile.open(stage/'source.tar') as archive:
            for member in archive.getmembers():
                if not (member.isfile() or member.isdir()) or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                    raise ValueError('Otillåten arkivpost')
            archive.extractall(release,filter='data')
        if tree_hashes(release)!=manifest['release_files']:
            raise ValueError('Releaseinnehåll avviker')
    shutil.copyfile(stage/'unit-ready.service',SYSTEM_FILES['unit'])


def atomic_public_copy(source,target,attributes):
    if os.geteuid()!=1000:
        raise ValueError('Publika atomiska kopior ska köras som seaparser')
    for parent in (target,*target.parents):
        if parent==PUBLIC.parent:break
        if parent.is_symlink():raise ValueError('Symlänk blockerar publicering')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.vinga-pending')
    created=False
    try:
        with temporary.open('xb') as stream:
            created=True
            stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
        info=temporary.stat()
        actual={'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode)}
        if actual!=attributes:
            raise ValueError('Nya filattribut matchar inte tidigare publicering; inga rättigheter ändras')
        os.replace(temporary,target)
    finally:
        if created and temporary.exists():temporary.unlink()


def publish(stage,manifest):
    files=[name for name in manifest['prepared'] if name.startswith('public-ready/')]
    for name in sorted(files,key=lambda name:name=='public-ready/index.html'):
        relative=name.removeprefix('public-ready/')
        attrs=manifest['public_attributes'].get(relative,{'uid':1000,'gid':1000,'mode':0o644})
        atomic_public_copy(stage/name,PUBLIC/relative,attrs)


def restore_public(stage,manifest):
    check_backup(manifest)
    backup=Path(manifest['backup'])
    for name in manifest['public_before']:
        atomic_public_copy(backup/'public-before'/name,PUBLIC/name,manifest['public_attributes'][name])
    for name,expected in manifest['prepared'].items():
        if not name.startswith('public-ready/'):continue
        relative=name.removeprefix('public-ready/');target=PUBLIC/relative
        if relative not in manifest['public_before'] and target.exists():
            if digest(target)!=expected:raise ValueError('Ny publik fil har ändrats; stoppar radering: '+relative)
            target.unlink()
    if tree_hashes(PUBLIC)!=manifest['public_before']:
        raise ValueError('Återställd publicering avviker')


def restore(stage,manifest):
    check_backup(manifest);check_unchanged_apache(manifest)
    subprocess.run(['/usr/sbin/runuser','-u','seaparser','--','/usr/bin/python3',str(ROOT/'deployment/vinga_upgrade.py'),'restore-public',str(stage)],check=True)
    shutil.copyfile(Path(manifest['backup'])/'unit-before',SYSTEM_FILES['unit'])


def check_unchanged_apache(manifest):
    for kind in ('apache','proxy'):
        if digest(Path(SYSTEM_FILES[kind]))!=manifest['system_before'][kind]:
            raise ValueError('Apache har ändrats externt; återställ inte över administratörsändringar')


def verify_public(stage,manifest):
    check_unchanged_apache(manifest)
    if digest(Path(SYSTEM_FILES['unit']))!=digest(stage/'unit-ready.service'):
        raise ValueError('Aktiv tjänstfil avviker')
    for name,expected in manifest['prepared'].items():
        if name.startswith('public-ready/') and digest(PUBLIC/name.removeprefix('public-ready/'))!=expected:
            raise ValueError('Publik fil avviker: '+name)
    pid=subprocess.check_output(['/usr/bin/systemctl','show','seaparser-api.service','--property=MainPID','--value'],text=True).strip()
    if not pid.isdigit() or Path('/proc/'+pid+'/cwd').resolve()!=Path(manifest['release']):
        raise ValueError('Aktiva API-processen kör inte verifierad release')
    Path(manifest['backup'],'activation-success.json').write_text(json.dumps({'commit':manifest['commit'],'https_flow':'passed','public_url':'https://seaparser.com/'},sort_keys=True)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('preflight','backup','install','publish','restore','restore-public','verify-public'));parser.add_argument('stage',type=Path)
    args=parser.parse_args();manifest=verify(args.stage)
    {'preflight':preflight,'backup':backup,'install':install,'publish':publish,'restore':restore,'restore-public':restore_public,'verify-public':verify_public}[args.action](args.stage,manifest)
