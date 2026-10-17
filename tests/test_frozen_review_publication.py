"""Separate review publication must preserve the demo and exact public allowlist."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from deployment import frozen_review as deploy


class FrozenReviewPublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.stage = root / 'stage'
        self.public = root / 'public'
        self.public.mkdir()
        (self.public / 'index.html').write_text('existing demo')
        (self.public / 'demo.mjs').write_text('existing module')
        before = deploy.tree_hashes(self.public)
        self.before = before
        self.addCleanup(patch.stopall)
        patch.object(deploy, 'PUBLIC', self.public).start()
        patch.object(deploy.subprocess, 'check_output', side_effect=lambda args, **kwargs:
                     '' if 'status' in args else 'a' * 40).start()
        deploy.prepare(self.stage)

    def test_prepare_has_exactly_one_public_file_and_never_touches_demo(self):
        self.assertEqual(set(deploy.tree_hashes(self.stage / 'public-ready')), {deploy.NAME})
        self.assertEqual(deploy.tree_hashes(self.public), self.before)
        self.assertFalse(deploy.verify(self.stage)['published'])
        self.assertFalse((self.stage / 'public-ready/index.receipt.json').exists())

    def test_publish_uses_existing_atomic_copy_only_for_separate_url(self):
        with patch.object(deploy, 'atomic_public_copy', side_effect=lambda source, target, attrs:
                          shutil.copyfile(source, target)) as copy:
            result = deploy.publish(self.stage)
        copy.assert_called_once_with(self.stage / 'public-ready' / deploy.NAME,
                                     self.public / deploy.NAME,
                                     {'uid':1000, 'gid':1000, 'mode':0o644})
        self.assertTrue(result['existing_public_content_unchanged'])
        self.assertFalse(result['https_verified'])
        self.assertEqual((self.public / 'index.html').read_text(), 'existing demo')
        with self.assertRaises(ValueError):
            deploy.publish(self.stage)

    def test_extra_private_or_modified_ready_files_block_activation(self):
        path = self.stage / 'public-ready/app.env'
        path.write_text('not public')
        with self.assertRaisesRegex(ValueError, 'allowlist/hash'):
            deploy.verify(self.stage)
        path.unlink()
        (self.stage / 'public-ready' / deploy.NAME).write_text('modified HTML')
        with self.assertRaisesRegex(ValueError, 'allowlist/hash'):
            deploy.verify(self.stage)
        self.assertEqual(deploy.tree_hashes(self.public), self.before)

    def test_changed_demo_or_existing_target_blocks_before_copy(self):
        for filename in ('index.html', deploy.NAME):
            with self.subTest(filename=filename):
                (self.public / filename).write_text('external change')
                with patch.object(deploy, 'atomic_public_copy') as copy:
                    with self.assertRaises(ValueError):
                        deploy.publish(self.stage)
                    copy.assert_not_called()
                (self.public / filename).unlink()
                if filename == 'index.html':
                    (self.public / filename).write_text('existing demo')

    def test_alternate_public_destination_in_manifest_is_rejected(self):
        path = self.stage / 'manifest.json'
        data = json.loads(path.read_text())
        data['public_files'] = {'index.html': next(iter(data['public_files'].values()))}
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'identity/allowlist'):
            deploy.verify(self.stage)

    def test_removed_historical_nonrouting_notice_is_rejected(self):
        page = deploy.ARTIFACT.read_bytes()
        for old, new in ((b'"historical":true', b'"historical":false'),
                         (b'"routing_qualified":false', b'"routing_qualified":true'),
                         (b'Ingen rutt ber', b'Nu en rutt ber')):
            with self.subTest(change=old):
                self.assertNotEqual(page.replace(old, new, 1), page)
                with self.assertRaises(ValueError):
                    deploy.validate_page(page.replace(old, new, 1))
