"""PoC activation isolates its service and proxy; failure/rollback retain the old demo."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from deployment import poc_api as p

class PocActivationTests(unittest.TestCase):
    def test_existing_confinement_is_retained_in_isolated_service(self):
        before=(Path(__file__).resolve().parents[1]/'deployment/seaparser-api.service').read_text()
        result=p.unit_for_release(before,Path('/home/web/seaparser/releases/poc-'+'a'*40))
        filtered=[line for line in result.splitlines() if not line.startswith('Environment=')]
        changed=[(a,b) for a,b in zip(before.splitlines(),filtered) if a!=b]
        self.assertEqual(len(changed),3)
        self.assertEqual({b.split('=')[0] for _,b in changed},{'Description','WorkingDirectory','ExecStart'})
        self.assertIn(str(p.RUNTIME/'bin/python'),result);self.assertIn('--port 8766',result)
        for key in ('User=seaparser','ProtectSystem=strict','InaccessiblePaths=/home/web/seaparser/config','MemoryMax=512M','CPUQuota=200%','TasksMax=32'):
            self.assertIn(key,result)
        with self.assertRaises(ValueError):p.unit_for_release('ExecStart=/unknown/python\n',Path('/reviewed'))

    def test_proxy_addition_precedes_and_retains_legacy_rules(self):
        before='ProxyPass /api/ http://127.0.0.1:8765/api/ connectiontimeout=2 timeout=25\n'
        result=p.proxy_for_poc(before);self.assertTrue(result.endswith(before))
        self.assertLess(result.index('ProxyPass /api/poc/'),result.index('ProxyPass /api/ '))
        with self.assertRaises(ValueError):p.proxy_for_poc(result)

    def test_install_restore_stale_ci_and_external_change_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);unit=stage/'poc.service';proxy=stage/'proxy';proxy.write_text('old proxy\n')
            (stage/'proxy-before.conf').write_bytes(proxy.read_bytes());(stage/'proxy-ready.conf').write_text('new proxy\n');(stage/'unit-ready.service').write_text('reviewed PoC service\n');(stage/'release').mkdir()
            m={'release':str(stage/'installed-release'),'release_files':{'old.html':'hash'},'commit':'a'*40,'system_before':{'proxy':p.digest(proxy)},'prepared':{n:p.digest(stage/n) for n in ('unit-ready.service','proxy-ready.conf')},'public_before':{'old.html':'hash'}}
            (stage/'ci-success.json').write_text(json.dumps({'commit':'wrong','conclusion':'success'}))
            with patch.object(p.os,'geteuid',return_value=0),patch.object(p,'UNIT',unit),patch.object(p,'PROXY',proxy),patch.object(p,'verify',return_value=m) as verify,patch.object(p,'tree_hashes',return_value=m['public_before']),patch.object(p,'check_system'),patch.object(p.subprocess,'check_output',side_effect=lambda args,**kw:'a'*40+'\n' if 'rev-parse' in args else ''):
                with self.assertRaises(ValueError):p.root_action('install',stage)
                self.assertFalse(unit.exists());self.assertEqual(proxy.read_text(),'old proxy\n')
                (stage/'ci-success.json').write_text(json.dumps({'commit':'a'*40,'conclusion':'success'}));p.root_action('install',stage)
                self.assertEqual(unit.read_text(),'reviewed PoC service\n');self.assertEqual(proxy.read_text(),'new proxy\n')
                with self.assertRaises(ValueError):p.root_action('preflight',stage)
                self.assertEqual(unit.read_text(),'reviewed PoC service\n');self.assertEqual(proxy.read_text(),'new proxy\n')
                p.root_action('restore',stage);self.assertFalse(unit.exists());self.assertEqual(proxy.read_text(),'old proxy\n');verify.assert_called_with(stage,runtime=False)
                proxy.write_text('external admin change')
                with self.assertRaises(ValueError):p.root_action('restore',stage)
                self.assertEqual(proxy.read_text(),'external admin change')
