"""Single-file real-route publishing reuses preservation and validation guards."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from deployment import frozen_review as deploy


class RealRoutePublicationTests(unittest.TestCase):
    def setUp(self):
        deploy.select_review('routes')
        self.addCleanup(deploy.select_review,'forecast')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.stage=root/'stage';self.public=root/'public';self.public.mkdir()
        (self.public/'index.html').write_text('existing start page')
        (self.public/'vinga-prognosprov.html').write_text('existing forecast page')
        self.addCleanup(patch.stopall)
        patch.object(deploy,'PUBLIC',self.public).start()
        patch.object(deploy.subprocess,'check_output',side_effect=lambda args,**kwargs:
                     '' if 'status' in args else 'a'*40).start()

    def test_only_route_html_published_and_previous_pages_preserved(self):
        before=deploy.tree_hashes(self.public)
        manifest=deploy.prepare(self.stage)
        self.assertEqual(set(manifest['public_files']),{'vinga-ruttjamforelse.html'})
        self.assertEqual(deploy.tree_hashes(self.public),before)
        with patch.object(deploy,'atomic_public_copy',side_effect=lambda src,dst,attrs:shutil.copyfile(src,dst)):
            result=deploy.publish(self.stage)
        self.assertTrue(result['existing_public_content_unchanged'])
        self.assertEqual(deploy.tree_hashes(self.public),before|manifest['public_files'])
        with self.assertRaises(ValueError):deploy.verify(self.stage)

    def test_extra_resource_or_changed_page_blocks_publish(self):
        deploy.prepare(self.stage)
        (self.stage/'public-ready/result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'allowlist/hash'):deploy.verify(self.stage)
        page=deploy.ARTIFACT.read_bytes()
        with self.assertRaises(ValueError):deploy.validate_page(page.replace(b'13 oktober 2026',b'aktuella data',1))
        with self.assertRaises(ValueError):deploy.validate_page(page.replace(b'Konfigurerade antaganden',b'Dolda antaganden',1))
