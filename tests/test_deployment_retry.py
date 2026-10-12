"""Independent preservation and fail-closed retry checks; no system writes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from deployment.prepare_retry import add_api_include

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
            def check():
                return subprocess.run(['/bin/bash','-c','source "$1"; require_owned_or_missing "$2" "$3"',
                                       '_',str(ROOT/'deployment/activation-preflight.sh'),str(source),str(target)],
                                      capture_output=True).returncode
            self.assertEqual(check(),0)
            target.write_bytes(source.read_bytes());self.assertEqual(check(),0)
            target.write_text('unrelated');self.assertNotEqual(check(),0)
            self.assertEqual(target.read_text(),'unrelated')
            target.unlink();target.symlink_to(source);self.assertNotEqual(check(),0)
