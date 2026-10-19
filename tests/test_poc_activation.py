"""PoC activation isolates its service and proxy; failure/rollback retain the old demo."""
from pathlib import Path
import json,tempfile,unittest,subprocess,os
from types import SimpleNamespace
from unittest.mock import patch
from deployment import poc_api as p

class PocActivationTests(unittest.TestCase):
    def test_rollback_requires_unloaded_manager_zero_pid_and_empty_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);unit=stage/'absent.service';manifest={'commit':'a'*40}
            state='LoadState=not-found\nActiveState=inactive\nMainPID=0\nControlGroup=\n'
            with patch.object(p,'UNIT',unit),patch.object(p,'check_system'),patch.object(p.subprocess,'run') as manager,patch.object(p.subprocess,'check_output',return_value='') as port,patch.object(p.Path,'rglob',return_value=()) as cgroups:
                for invalid in (state.replace('not-found','loaded'),state.replace('MainPID=0','MainPID=123'),state.replace('inactive','active')):
                    manager.return_value=SimpleNamespace(returncode=0,stdout=invalid)
                    with self.assertRaises(ValueError):p.restored_state(stage,manifest)
                    self.assertFalse((stage/'restoration-check.json').exists())
                manager.return_value=SimpleNamespace(returncode=0,stdout=state);port.return_value='LISTEN 8766'
                with self.assertRaises(ValueError):p.restored_state(stage,manifest)
                port.return_value='';self.assertTrue(p.restored_state(stage,manifest)['verified'])
                processes=stage/'cgroup.procs';processes.write_text('123\n');cgroups.return_value=(processes,)
                with self.assertRaisesRegex(ValueError,'cgroup still contains processes'):p.restored_state(stage,manifest)

    def test_failed_sequential_public_flow_stops_before_removing_unit_and_reloads(self):
        # Exercise the actual shell's ERR path with simulated system commands only.
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);(stage/'release').mkdir();(stage/'manifest.json').write_text(json.dumps({'release':str(stage/'release')}))
            fake=stage/'fake';fake.write_text('''#!/bin/bash
echo "$*" >> "$TRACE"
if [[ "$1 $2" == 'poc verify-restored' ]]; then echo '{"verified":true}' > "$STAGE/restoration-check.json"; fi
if [[ "$1" == runuser ]]; then exit 7; fi
if [[ "$1 $2" == 'systemctl show' ]]; then echo 123; fi
''');fake.chmod(0o700)
            source=(Path(__file__).resolve().parents[1]/'deployment/activate-poc-api.sh').read_text()
            source=source.replace('/usr/bin/test "$(/usr/bin/id -u)" -eq 0','true').replace('/home/web/seaparser/autonomy/run.lock',str(stage/'run.lock'))
            source=source.replace('/usr/bin/python3 -B -m deployment.poc_api',str(fake)+' poc')
            for command,path in (('systemctl','/usr/bin/systemctl'),('apache2ctl','/usr/sbin/apache2ctl'),('curl','/usr/bin/curl'),('ss','/usr/bin/ss'),('runuser','/usr/sbin/runuser')):
                source=source.replace(path,str(fake)+' '+command)
            script=stage/'activate.sh';script.write_text(source)
            result=subprocess.run(['/bin/bash',str(script)],env=os.environ|{'TRACE':str(stage/'trace'),'STAGE':str(stage)},capture_output=True,text=True)
            self.assertEqual(result.returncode,7,result.stdout+result.stderr)
            lines=(stage/'trace').read_text().splitlines();start=next(i for i,s in enumerate(lines) if s.startswith('runuser'))
            tail=lines[start+1:]
            expected=('systemctl stop seaparser-poc-api.service','poc restore ','systemctl daemon-reload','apache2ctl configtest','systemctl reload apache2','curl ','poc verify-restored ')
            self.assertEqual(len(tail),len(expected),tail)
            self.assertTrue(all(line.startswith(prefix) for line,prefix in zip(tail,expected)),tail)
            self.assertTrue((stage/'rollback-success.json').exists())

    def test_existing_confinement_is_retained_in_isolated_service(self):
        before=(Path(__file__).resolve().parents[1]/'deployment/seaparser-api.service').read_text()
        result=p.unit_for_release(before,Path('/home/web/seaparser/releases/poc-'+'a'*40))
        filtered=[line for line in result.splitlines() if not line.startswith(('Environment=','ReadWritePaths='))]
        changed=[(a,b) for a,b in zip(before.splitlines(),filtered) if a!=b]
        self.assertEqual(len(changed),4)
        self.assertEqual({b.split('=')[0] for _,b in changed},{'Description','WorkingDirectory','ExecStart','MemoryMax'})
        self.assertIn(str(p.RUNTIME/'bin/python'),result);self.assertIn('--port 8766',result)
        for key in ('User=seaparser','ProtectSystem=strict','InaccessiblePaths=/home/web/seaparser/config','MemoryMax=1024M','CPUQuota=200%','TasksMax=32'):
            self.assertIn(key,result)
        self.assertIn('ReadWritePaths=/home/web/seaparser/autonomy/cache/coastal-inputs-v1',result)
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
