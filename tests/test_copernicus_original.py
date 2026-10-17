"""Original-file acquisition checks; no live network or database."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from scripts.copernicus_budget import DownloadBudget
from scripts.download_copernicus_original import PREFIX, fetch


class OriginalFetchTests(unittest.TestCase):
    filename = 'BAL-WAM_WAV2026101700.nc'

    def marine(self, *, count=1, changed=False):
        calls = []
        def get(**kwargs):
            calls.append(kwargs)
            remote = NS(filename=self.filename, s3_url=PREFIX+'2026/10/'+self.filename,
                        file_size=16/1024**2, etag='"abcdef-1"',
                        last_modified_datetime='2026-10-17T08:02:01Z')
            if not kwargs.get('dry_run'):
                (kwargs['output_directory']/self.filename).write_bytes(b'0123456789abcdef')
                if changed:
                    remote.etag = 'deadbeef-2'
            return NS(files=[remote]*count, number_of_files_to_download=count,
                      total_size=16/1024**2)
        return NS(__version__='2.5.0', get=get), calls

    def test_exact_original_and_cache_hit_preserve_source_identity(self):
        marine, calls = self.marine()
        with tempfile.TemporaryDirectory() as temp, patch(
                'scripts.copernicus_budget.shutil.disk_usage', return_value=NS(free=20_000_000_000)):
            root = Path(temp)
            first = fetch(marine,self.filename,root/'first',root/'cache',DownloadBudget())
            second = fetch(marine,self.filename,root/'second',root/'cache',DownloadBudget())
            self.assertEqual(len(calls),3)  # two source HEAD/list checks, one original download
            self.assertEqual(calls[0]['filter'],'*/'+self.filename)
            self.assertTrue(calls[0]['dry_run'])
            self.assertFalse(first['cache_hit'])
            self.assertTrue(second['cache_hit'])
            self.assertEqual(second['estimated_transfer_bytes_this_run'],0)
            self.assertEqual(first['sha256'],second['sha256'])
            self.assertEqual(first['retrieved_at'],second['retrieved_at'])
            self.assertEqual(first['actual_result_bytes'],16)
            self.assertFalse(second['arco_lineage_verified'])
            self.assertIsNone(second['issued_at'])

    def test_budget_or_multiple_candidates_never_download(self):
        for count,budget in ((2,DownloadBudget()),(1,DownloadBudget(transfer_gb=1e-9))):
            marine,calls=self.marine(count=count)
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                root=Path(temp)
                fetch(marine,self.filename,root/'out',root/'cache',budget)
            self.assertEqual(len(calls),1)

    def test_changed_object_is_not_admitted_to_cache(self):
        marine,calls=self.marine(changed=True)
        with tempfile.TemporaryDirectory() as temp, patch(
                'scripts.copernicus_budget.shutil.disk_usage', return_value=NS(free=20_000_000_000)):
            root=Path(temp)
            with self.assertRaisesRegex(ValueError,'changed'):
                fetch(marine,self.filename,root/'out',root/'cache',DownloadBudget())
            self.assertFalse(list((root/'cache').rglob('entry.json')))

    def test_wildcard_filename_rejected_before_get(self):
        marine,calls=self.marine()
        with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):
            fetch(marine,'*.nc',Path(temp)/'out',Path(temp)/'cache',DownloadBudget())
        self.assertEqual(calls,[])
