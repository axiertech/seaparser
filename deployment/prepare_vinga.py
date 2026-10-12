"""Prepare content-verified upgrade; no system or public writes, no network."""
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
import subprocess
import tarfile
PUBLIC_ASSETS=('index.html','map.css','main.mjs','map-component.mjs','controller.mjs','client.mjs',
               'vendor/leaflet.js','vendor/leaflet.css','vendor/leaflet-LICENSE.txt',
               'vendor/images/marker-shadow.png','vendor/images/marker-icon.png','vendor/images/marker-icon-2x.png',
               'vendor/images/layers.png','vendor/images/layers-2x.png')

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=Path('/home/web/seaparser/public')
SYSTEM_FILES={'unit':'/etc/systemd/system/seaparser-api.service','apache':'/etc/apache2/sites-available/seaparser.conf','proxy':'/etc/apache2/seaparser-api.conf'}


def digest(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError('Vanlig fil krävs: '+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(stage):
    manifest=json.loads((stage/'manifest.json').read_text())
    commit=manifest['commit']
    if not re.fullmatch('[0-9a-f]{40}',commit) or manifest['checkout']!=str(ROOT) or manifest['release']!='/home/web/seaparser/releases/vinga-'+commit or manifest['backup']!='/home/web/seaparser/backups/vinga-'+commit:
        raise ValueError('Avvikande deploymentidentitet/sökvägar')
    for name in (*manifest['prepared'],*manifest['release_files'],*manifest['public_before']):
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Avvikande relativ sökväg')
    for name,expected in manifest['prepared'].items():
        if digest(stage/name)!=expected:
            raise ValueError('Förberett innehåll har ändrats: '+name)
    return manifest


def prepare(stage):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('Kräver ren granskad checkout')
    if stage.exists():
        raise ValueError('Använd en ny förberedelsekatalog; skriv inte över en deployment')
    stage.mkdir(parents=True)
    subprocess.run(['git','archive','--format=tar','HEAD','--output='+str(stage/'source.tar')],cwd=ROOT,check=True)
    release_files={}
    with tarfile.open(stage/'source.tar') as archive:
        for member in archive.getmembers():
            if member.isdir():continue
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise ValueError('Oväntad arkivpost')
            release_files[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    bundle=ROOT/'frontend/land-dist'
    names=(*PUBLIC_ASSETS,'vinga.html','land-review.html','land-review.mjs','land.geojson','routing.geojson')
    prepared={};(stage/'public-ready').mkdir()
    for name in names:
        target=stage/'public-ready'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((bundle/name).read_bytes())
    (stage/'public-ready/synthetic.html').write_bytes((bundle/'index.html').read_bytes())
    (stage/'public-ready/index.html').write_bytes((bundle/'vinga.html').read_bytes())
    release='/home/web/seaparser/releases/vinga-'+commit
    unit=(ROOT/'deployment/seaparser-api.service').read_text().replace('WorkingDirectory=/home/web/seaparser/app','WorkingDirectory='+release)
    (stage/'unit-ready.service').write_text(unit)
    (stage/'unit-before.service').write_bytes(Path(SYSTEM_FILES['unit']).read_bytes())
    if (stage/'unit-before.service').read_bytes()!=(ROOT/'deployment/seaparser-api.service').read_bytes():
        raise ValueError('Befintlig tjänst avviker från verifierad deployment')
    if Path(SYSTEM_FILES['proxy']).read_bytes()!=(ROOT/'deployment/apache-api.conf').read_bytes():
        raise ValueError('Befintlig proxy avviker från verifierad deployment')
    for path in stage.rglob('*'):
        if path.is_file():prepared[path.relative_to(stage).as_posix()]=digest(path)
    before={p.relative_to(PUBLIC).as_posix():digest(p) for p in PUBLIC.rglob('*') if p.is_file()}
    manifest={'commit':commit,'checkout':str(ROOT),'release':release,
              'backup':'/home/web/seaparser/backups/vinga-'+commit,
              'prepared':prepared,'release_files':release_files,'public_before':before,
              'public_attributes':{name:{'uid':(PUBLIC/name).stat().st_uid,'gid':(PUBLIC/name).stat().st_gid,'mode':stat.S_IMODE((PUBLIC/name).stat().st_mode)} for name in before},
              'system_before':{k:digest(Path(v)) for k,v in SYSTEM_FILES.items()},
              'notice':'Real land, synthetic weather only. No real forecast activation.'}
    (stage/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    verify(stage)
    print('Förberett commit '+commit+'; inga publika/systemfiler ändrade.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',type=Path);parser.add_argument('--verify',action='store_true')
    args=parser.parse_args();(verify if args.verify else prepare)(args.stage)
