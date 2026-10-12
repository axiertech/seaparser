"""Root-flow primitives checked in temp directories; no system/public mutations."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from deployment.vinga_upgrade import atomic_public_copy,check_unchanged_apache,restore_public,tree_hashes
from deployment.prepare_vinga import digest


class PublicationTests(unittest.TestCase):
    def setUp(self):
        role=patch('deployment.vinga_upgrade.os.geteuid',return_value=1000)
        role.start();self.addCleanup(role.stop)

    def test_atomic_copy_preserves_attributes_and_existing_pending_file(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);public=root/'public';public.mkdir();source=root/'source';source.write_text('new')
            target=public/'index.html';target.write_text('old');info=target.stat()
            attrs={'uid':info.st_uid,'gid':info.st_gid,'mode':0o644}
            with patch('deployment.vinga_upgrade.PUBLIC',public):
                atomic_public_copy(source,target,attrs)
                self.assertEqual(target.read_text(),'new')
                self.assertEqual(target.stat().st_uid,info.st_uid)
                pending=public/'index.html.vinga-pending';pending.write_text('unrelated')
                with self.assertRaises(FileExistsError):atomic_public_copy(source,target,attrs)
                self.assertEqual(pending.read_text(),'unrelated')
                self.assertEqual(target.read_text(),'new')

    def test_unexpected_mode_and_symlink_stop_before_replacement(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);public=root/'public';public.mkdir();source=root/'source';source.write_text('new')
            target=public/'index.html';target.write_text('old')
            with patch('deployment.vinga_upgrade.PUBLIC',public):
                with self.assertRaises(ValueError):atomic_public_copy(source,target,{'uid':1000,'gid':1000,'mode':0o600})
                self.assertEqual(target.read_text(),'old')
                link=public/'alias.html';link.symlink_to(target)
                with self.assertRaises(ValueError):atomic_public_copy(source,link,{'uid':1000,'gid':1000,'mode':0o644})
                self.assertEqual(target.read_text(),'old')

    def test_apache_external_change_blocks_overwrite(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);apache=root/'apache';proxy=root/'proxy';apache.write_text('Directory corrected');proxy.write_text('proxy')
            manifest={'system_before':{'apache':digest(apache),'proxy':digest(proxy)}}
            with patch('deployment.vinga_upgrade.SYSTEM_FILES',{'apache':str(apache),'proxy':str(proxy)}):
                check_unchanged_apache(manifest)
                apache.write_text('administrator update')
                with self.assertRaises(ValueError):check_unchanged_apache(manifest)
                self.assertEqual(apache.read_text(),'administrator update')

    def test_public_rollback_restores_old_bytes_and_removes_only_own_new_file(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);public=root/'public';public.mkdir();stage=root/'stage';stage.mkdir()
            backup=root/'backup';old=backup/'public-before';old.mkdir(parents=True)
            (old/'index.html').write_text('old synthetic')
            (public/'index.html').write_text('new Vinga');(public/'vinga.html').write_text('own new page')
            info=(public/'index.html').stat()
            manifest={'backup':str(backup),'public_before':{'index.html':digest(old/'index.html')},
                      'system_before':{},'public_attributes':{'index.html':{'uid':info.st_uid,'gid':info.st_gid,'mode':0o644}},
                      'prepared':{'public-ready/index.html':digest(public/'index.html'),'public-ready/vinga.html':digest(public/'vinga.html')}}
            with patch('deployment.vinga_upgrade.PUBLIC',public):
                restore_public(stage,manifest)
                self.assertEqual((public/'index.html').read_text(),'old synthetic')
                self.assertFalse((public/'vinga.html').exists())
                self.assertEqual(tree_hashes(public),manifest['public_before'])
