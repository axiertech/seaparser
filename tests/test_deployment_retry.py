"""Independent preservation and fail-closed retry checks; no system writes."""
from pathlib import Path
import subprocess
import os
import json
import hashlib
import tempfile
import unittest
from deployment.prepare_retry import add_api_include,verify_snapshot

ROOT=Path(__file__).resolve().parents[1]
CONFIG='''<VirtualHost *:80>
 ServerName seaparser.com
</VirtualHost>
<VirtualHost *:443>
 ServerName seaparser.com
 DocumentRoot /home/web/seaparser/public
 <Directory /home/web/seaparser>
  AllowOverride None
  Require all denied
 </Directory>
 <Directory /home/web/seaparser/public>
  AllowOverride None
  Require all granted
 </Directory>
 SSLEngine on
</VirtualHost>
'''

class DeploymentRetryTests(unittest.TestCase):
    def test_directory_and_tls_policy_are_byte_preserved(self):
        result=add_api_include(CONFIG)
        added='    Include /etc/apache2/seaparser-api.conf\n'
        self.assertEqual(result.replace(added,''),CONFIG)
        self.assertEqual(result.count(added),1)
        self.assertNotIn('AllowOverride All',result)
        self.assertIn('Require all denied',result)

    def test_unexpected_vhost_or_existing_proxy_are_rejected(self):
        for config in (CONFIG.replace('ServerName seaparser.com','ServerName other.test'),
                       CONFIG+CONFIG, add_api_include(CONFIG)):
            with self.assertRaises(ValueError):
                add_api_include(config)

    def test_retry_accepts_missing_and_exact_owned_files_only(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'expected';target=Path(folder)/'installed'
            source.write_text('SeaParser deployment fixture')
            def check(owner=None):
                return subprocess.run(['/bin/bash','-c','source "$1"; require_owned_or_missing "$2" "$3" "$4"',
                                       '_',str(ROOT/'deployment/activation-preflight.sh'),str(source),str(target),str(os.getuid() if owner is None else owner)],
                                      capture_output=True).returncode
            self.assertEqual(check(),0)
            target.write_bytes(source.read_bytes());self.assertEqual(check(),0)
            self.assertNotEqual(check(os.getuid()+1),0)
            target.write_text('unrelated');self.assertNotEqual(check(),0)
            self.assertEqual(target.read_text(),'unrelated')
            target.unlink();target.symlink_to(source);self.assertNotEqual(check(),0)

    def test_deployment_receipt_rejects_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for name in ('apache-api.conf','seaparser-api.service'):
                (base/name).write_text('fixture-'+name)
            (base/'apache-before.conf').write_text(CONFIG)
            (base/'apache-ready.conf').write_text(add_api_include(CONFIG))
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            manifest={'identity':'seaparser-synthetic-map-c6b0b4f',
                      'deployment_files':{n:sha(base/n) for n in ('apache-api.conf','seaparser-api.service')},
                      'apache_before_sha256':sha(base/'apache-before.conf')}
            (base/'manifest.json').write_text(json.dumps(manifest))
            verify_snapshot(base)
            (base/'seaparser-api.service').write_text('other deployment')
            with self.assertRaises(ValueError):
                verify_snapshot(base)
