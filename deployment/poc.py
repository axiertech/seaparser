"""Publish a scoped static PoC through the existing atomic deployment helpers."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

from deployment.prepare_vinga import PUBLIC,ROOT,digest,PUBLIC_ASSETS
from deployment.vinga_upgrade import atomic_public_copy,tree_hashes

BUILD=ROOT/'artifacts/poc-site'
URL='https://seaparser.com/poc/'
ROOT_FILES=set(PUBLIC_ASSETS)-{'main.mjs'}|{'poc-main.mjs','poc-transport.mjs','poc.css','scene.json','catalog.json','uddevalla-main.mjs','vinga-uddevalla.json','coastal-view.mjs','coastal-voyage.json'}


def allowed(name):
    return name in ROOT_FILES or bool(re.fullmatch(r'bank/[abc]{2}-(normal|wind|waves)\.json',name)) or bool(re.fullmatch(r'gpx/[abc]{2}-(normal|wind|waves)-[0-3]-auto-[0-3]\.gpx',name)) or bool(re.fullmatch(r'gpx/coastal-water-[0-7]-estimated\.gpx',name))


def clean_commit():
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():
        raise ValueError('Clean reviewed checkout required')
    return subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()


def prepare(stage):
    commit=clean_commit();receipt=json.loads((BUILD/'build-receipt.json').read_text())
    files=receipt['files']
    if not ROOT_FILES <= set(files) or not all(allowed(n) for n in files):
        raise ValueError('PoC public allowlist mismatch')
    for name,sha in files.items():
        if digest(BUILD/name)!=sha:raise ValueError('PoC build changed: '+name)
    before=tree_hashes(PUBLIC)
    stage.mkdir(parents=True,mode=0o700,exist_ok=False)
    ready=stage/'public-ready';backup=stage/'public-before';public_files={}
    attributes={}
    for name,sha in files.items():
        relative='poc/'+name;target=ready/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(BUILD/name,target);public_files[relative]=sha
        if relative in before:
            target=backup/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PUBLIC/relative,target)
            info=(PUBLIC/relative).stat();attributes[relative]={'uid':info.st_uid,'gid':info.st_gid,'mode':stat.S_IMODE(info.st_mode)}
    manifest=dict(schema=1,commit=commit,checkout=str(ROOT),public_root=str(PUBLIC),url=URL,
                  public_files=public_files,public_before=before,attributes=attributes,published=False)
    (stage/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest


def verify(stage,check_public=True,check_checkout=True):
    m=json.loads((stage/'manifest.json').read_text())
    if m['schema']!=1 or m['checkout']!=str(ROOT) or m['public_root']!=str(PUBLIC) or m['url']!=URL:
        raise ValueError('PoC deployment identity mismatch')
    if not {'poc/'+n for n in ROOT_FILES} <= set(m['public_files']) or any(not n.startswith('poc/') or not allowed(n[4:]) for n in m['public_files']):
        raise ValueError('Only namespaced PoC resources may be published')
    if tree_hashes(stage/'public-ready')!=m['public_files']:raise ValueError('Staged resources differ')
    if check_checkout and clean_commit()!=m['commit']:raise ValueError('Commit changed after preparation')
    for n in m['public_files']:
        if n in m['public_before'] and digest(stage/'public-before'/n)!=m['public_before'][n]:raise ValueError('Rollback backup differs')
    if check_public and tree_hashes(PUBLIC)!=m['public_before']:raise ValueError('Public content changed; prepare a fresh stage')
    return m


def restore(stage,m):
    for name,new_sha in m['public_files'].items():
        target=PUBLIC/name
        for parent in (target,*target.parents):
            if parent==PUBLIC.parent:break
            if parent.is_symlink():raise ValueError('Symlink blocks scoped rollback')
        if name in m['public_before']:
            old=m['public_before'][name]
            if digest(target)==old:continue
            if digest(target)!=new_sha:raise ValueError('External change blocks rollback: '+name)
            atomic_public_copy(stage/'public-before'/name,target,m['attributes'][name])
        elif target.exists():
            if digest(target)!=new_sha:raise ValueError('External change blocks rollback: '+name)
            target.unlink()


def publish(stage):
    with (stage/'publish.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);m=verify(stage)
        os.umask(0o022)
        try:
            for name in sorted(m['public_files'],key=lambda n:n=='poc/index.html'):
                atomic_public_copy(stage/'public-ready'/name,PUBLIC/name,m['attributes'].get(name,{'uid':1000,'gid':1000,'mode':0o644}))
            if tree_hashes(PUBLIC)!=m['public_before']|m['public_files']:raise ValueError('Public content differs after activation')
        except Exception:
            restore(stage,m);raise
        result=dict(commit=m['commit'],url=URL,published=True,https_verified=False,
                    file_count=len(m['public_files']),index_sha256=digest(PUBLIC/'poc/index.html'),
                    previous_pages_unchanged=True)
        (stage/'publication-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def rollback(stage):
    with (stage/'publish.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        m=verify(stage,check_public=False,check_checkout=False);os.umask(0o022);restore(stage,m)
        return {'rolled_back':True,'url':URL,'commit':m['commit']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','verify','publish','rollback'));parser.add_argument('stage',type=Path);args=parser.parse_args()
    try:print(json.dumps(globals()[args.action](args.stage.absolute()),indent=2))
    except (ValueError,OSError,KeyError) as error:parser.exit(1,str(error)+'\n')
