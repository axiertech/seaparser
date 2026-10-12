"""Snapshot current operator-corrected config; add only the SeaParser API include."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

OLD=Path('/home/web/seaparser/backups/activation-20261012-c6b0b4f')
RETRY=Path('/home/web/seaparser/backups/activation-retry-20261012-81522f7')
APACHE=Path('/etc/apache2/sites-available/seaparser.conf')
PUBLIC=Path('/home/web/seaparser/public')


def add_api_include(text):
    blocks=list(re.finditer(r'<VirtualHost\s+[^>]*:443\s*>.*?</VirtualHost>',text,re.S))
    if len(blocks)!=1 or not re.search(r'^\s*ServerName\s+seaparser\.com\s*$',blocks[0].group(),re.M):
        raise ValueError('Oväntad HTTPS-vhost; stoppar utan ändring')
    block=blocks[0].group()
    include='    Include /etc/apache2/seaparser-api.conf\n'
    if '/etc/apache2/seaparser-api.conf' in text or 'ProxyPass' in block:
        raise ValueError('Förväntar korrigerad konfiguration efter rollback utan API-inkludering')
    return text[:blocks[0].start()]+block.replace('</VirtualHost>',include+'</VirtualHost>')+text[blocks[0].end():]


def prepare():
    if RETRY.exists():
        raise ValueError('Retry-backup finns redan; skriv inte över den')
    original=APACHE.read_text();updated=add_api_include(original)
    for installed,saved in ((Path('/etc/apache2/seaparser-api.conf'),OLD/'apache-api.conf'),
                            (Path('/etc/systemd/system/seaparser-api.service'),OLD/'seaparser-api.service')):
        if installed.is_symlink() or (installed.exists() and (installed.stat().st_uid!=0 or installed.read_bytes()!=saved.read_bytes())):
            raise ValueError('Avvikande tidigare deploymentfil: '+str(installed))
    RETRY.mkdir()
    shutil.copyfile(APACHE,RETRY/'apache-before.conf')
    (RETRY/'apache-ready.conf').write_text(updated)
    shutil.copytree(PUBLIC,RETRY/'public-before')
    shutil.copytree(OLD/'frontend-ready',RETRY/'frontend-ready')
    for name in ('apache-api.conf','seaparser-api.service'):
        shutil.copyfile(OLD/name,RETRY/name)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'apache_before_sha256':sha(APACHE),'apache_ready_sha256':sha(RETRY/'apache-ready.conf'),
              'public_before':{str(p.relative_to(PUBLIC)):sha(p) for p in PUBLIC.rglob('*') if p.is_file()},
              'deployment_files':{name:sha(RETRY/name) for name in ('apache-api.conf','seaparser-api.service')},
              'identity':'seaparser-synthetic-map-c6b0b4f','directory_policy':'preserved operator config'}
    (RETRY/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (RETRY/'originals.sha256').write_text(manifest['apache_before_sha256']+'  '+str(APACHE)+'\n'+
                                        manifest['public_before']['index.html']+'  '+str(PUBLIC/'index.html')+'\n')
    assert sha(RETRY/'apache-before.conf')==manifest['apache_before_sha256']
    for name,expected in manifest['public_before'].items():
        assert sha(RETRY/'public-before'/name)==expected
    print('Aktuell Apache och publik visning säkerhetskopierade; endast Include-rad tillagd i kandidat.')
    print('Retry-underlag:',RETRY)


def verify_snapshot(base):
    base=Path(base)
    manifest=json.loads((base/'manifest.json').read_text())
    if manifest.get('identity')!='seaparser-synthetic-map-c6b0b4f':
        raise ValueError('Okänd deploymentidentitet')
    for name in ('apache-api.conf','seaparser-api.service'):
        path=base/name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['deployment_files'][name]:
            raise ValueError('Deploymentunderlag avviker: '+name)
    before=(base/'apache-before.conf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=manifest['apache_before_sha256']:
        raise ValueError('Apache-backup avviker')
    if (base/'apache-ready.conf').read_text()!=add_api_include(before.decode()):
        raise ValueError('Apache-kandidat ändrar mer än tillåten Include-rad')
    print('Deploymentidentitet, filhashar och bevarad Apache-konfiguration verifierade.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify:
        verify_snapshot(args.verify)
    else:
        prepare()
