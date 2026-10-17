"""Public PoC has a scoped allowlist and working restoration, without root."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from deployment import poc


class PocPublicationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name)
        self.public=root/'public';self.public.mkdir();self.stage=root/'stage'
        for name in ('index.html','vinga-ruttjamforelse.html','vinga-ruttjamforelse-ramar.html','vinga-prognosprov.html'):
            (self.public/name).write_text('original '+name)
        self.original=poc.tree_hashes(self.public)
        self.addCleanup(patch.stopall)
        patch.object(poc,'PUBLIC',self.public).start()
        patch.object(poc.subprocess,'check_output',side_effect=lambda args,**kwargs:'' if 'status' in args else 'a'*40).start()
        patch.object(poc,'atomic_public_copy',side_effect=self.copy).start()
    def copy(self,source,target,attrs):
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    def test_publish_preserves_earlier_pages_and_rollback_removes_only_own_files(self):
        m=poc.prepare(self.stage);self.assertEqual(poc.tree_hashes(self.public),self.original)
        self.assertTrue(all(n.startswith('poc/') for n in m['public_files']))
        result=poc.publish(self.stage);self.assertTrue(result['published'])
        self.assertTrue((self.public/'poc/index.html').is_file())
        for name,sha in self.original.items():self.assertEqual(poc.digest(self.public/name),sha)
        poc.rollback(self.stage);self.assertEqual(poc.tree_hashes(self.public),self.original)
    def test_update_restores_previous_poc_and_modified_local_checkout_does_not_block_rollback(self):
        (self.public/'poc').mkdir();(self.public/'poc/index.html').write_text('previous PoC')
        before=poc.tree_hashes(self.public);poc.prepare(self.stage);poc.publish(self.stage)
        with patch.object(poc,'clean_commit',side_effect=ValueError('unrelated local work')):
            poc.rollback(self.stage)
        self.assertEqual(poc.tree_hashes(self.public),before)
    def test_extra_private_file_and_external_public_change_block_publication(self):
        poc.prepare(self.stage)
        p=self.stage/'public-ready/poc/app.env';p.write_text('private')
        with self.assertRaises(ValueError):poc.verify(self.stage)
        p.unlink();(self.public/'index.html').write_text('external update')
        with self.assertRaises(ValueError):poc.publish(self.stage)
        self.assertFalse((self.public/'poc/index.html').exists())
    def test_foreign_changes_are_never_removed_by_rollback(self):
        poc.prepare(self.stage);poc.publish(self.stage)
        (self.public/'poc/index.html').write_text('someone else changed this')
        with self.assertRaises(ValueError):poc.rollback(self.stage)
        self.assertEqual((self.public/'poc/index.html').read_text(),'someone else changed this')
