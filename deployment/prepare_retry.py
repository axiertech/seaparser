"""Snapshot current operator-corrected config; add only the SeaParser API include."""
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
        if installed.is_symlink() or (installed.exists() and installed.read_bytes()!=saved.read_bytes()):
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


if __name__=='__main__':
    prepare()
