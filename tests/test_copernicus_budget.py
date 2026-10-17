"""Budget requirements and snapshot-cache integrity, without network or DB."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from infrastructure.copernicus_fields import WAVE_FIELDS
from scripts.copernicus_budget import DownloadBudget, cached_entry, digest, request_key


class BudgetTests(unittest.TestCase):
    def check(self, file_mb=10, transfer_mb=2048, spent=0, free=20_000_000_000, **budgets):
        with patch('scripts.copernicus_budget.shutil.disk_usage', return_value=NS(free=free)):
            return DownloadBudget(**budgets).check(NS(file_size=file_mb, data_transfer_size=transfer_mb), spent, ['.'])

    def test_gb_transfer_and_small_result_are_separate(self):
        self.assertEqual(self.check(), (10 * 1_048_000, 2048 * 1_048_000))
        with self.assertRaisesRegex(ValueError, 'per-request'):
            self.check(transfer_gb=1)
        with self.assertRaisesRegex(ValueError, 'file GB'):
            self.check(file_mb=3000)

    def test_session_budget_and_disk_reserve(self):
        with self.assertRaisesRegex(ValueError, 'session'):
            self.check(spent=19_000_000_000)
        with self.assertRaisesRegex(ValueError, 'disk'):
            self.check(free=1_000_000_001)

    def test_missing_invalid_estimates_and_budgets(self):
        for v in (None, float('nan'), float('inf'), -1):
            with self.subTest(v=v), self.assertRaises(ValueError):
                self.check(transfer_mb=v)
        for v in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                DownloadBudget(transfer_gb=v)

    def test_cache_identity_and_corruption_and_age(self):
        request = dict(dataset_id='waves', start_datetime='2026-10-17T00:00:00Z',
                       variables=['VHM0'], minimum_longitude=11.58)
        self.assertEqual(request_key(request), request_key(dict(request, output_directory='/other')))
        for k, v in [('variables', ['VTM02']), ('minimum_longitude', 11.59),
                     ('start_datetime', '2026-10-17T01:00:00Z'), ('minimum_depth', 2)]:
            self.assertNotEqual(request_key(request), request_key(dict(request, **{k: v})))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertIsNone(cached_entry(root, request, 60, now=100))
            p = root / 'data.nc'; p.write_bytes(b'known snapshot')
            entry = dict(key=request_key(request), bytes=p.stat().st_size,
                         sha256=digest(p), cached_at_epoch=90, retrieved_at='2026-10-17T00:00:00Z',
                         estimated_result_bytes=100, estimated_transfer_bytes=1000)
            (root / 'entry.json').write_text(json.dumps(entry))
            self.assertEqual(cached_entry(root, request, 60, now=100), entry)
            self.assertIsNone(cached_entry(root, request, 60, now=200))
            self.assertIsNone(cached_entry(root, request, 60, now=80))
            p.write_bytes(b'broken snapshot')
            self.assertIsNone(cached_entry(root, request, 60, now=100))


class DownloadWorkflowTests(unittest.TestCase):
    def test_identical_second_request_reuses_snapshot_without_subset(self):
        from scripts.download_copernicus import main
        from tests.test_copernicus_import import RequestSelectionTests
        catalogue = RequestSelectionTests().catalogue(WAVE_FIELDS)
        catalogue.products[0].datasets[0].dataset_id = 'cmems_mod_bal_wav_anfc_PT1H-i'
        calls = []
        def subset(**kwargs):
            calls.append(kwargs)
            if kwargs.get('dry_run'):
                return NS(file_size=.1, data_transfer_size=40)
            (kwargs['output_directory'] / kwargs['output_filename']).write_bytes(b'netcdf test snapshot')
        marine = NS(__version__='2.5.0', describe=lambda **kw: catalogue, subset=subset)
        with tempfile.TemporaryDirectory() as temp, patch.dict('sys.modules', copernicusmarine=marine), patch(
                'scripts.download_copernicus.socket.getaddrinfo'), patch(
                'scripts.copernicus_budget.shutil.disk_usage', return_value=NS(free=30_000_000_000)):
            root = Path(temp)
            common = ['--products', 'waves', '--cache', str(root/'cache')]
            main(['--output', str(root/'first'), *common])
            main(['--output', str(root/'second'), *common])
            self.assertEqual(len(calls), 2)  # one estimate and one download total
            record = json.loads((root/'second'/'manifest.json').read_text())['files'][0]
            self.assertTrue(record['cache_hit'])
            self.assertEqual(record['estimated_transfer_bytes_this_run'], 0)
            self.assertEqual(record['estimated_transfer_bytes'], 40 * 1_048_000)
            self.assertEqual((root/'first'/'waves.nc').read_bytes(), (root/'second'/'waves.nc').read_bytes())

    def test_bad_scope_is_rejected_before_network(self):
        from scripts.download_copernicus import main
        for scope in (['--bbox', '12', '58', '11', '59'],
                      ['--minimum-depth', '2'], ['--variables', 'unreviewed']):
            with self.subTest(scope=scope), patch('scripts.download_copernicus.socket.getaddrinfo') as dns:
                with self.assertRaises(ValueError):
                    main(['--output', '/unused', *scope])
                dns.assert_not_called()

    def test_transfer_cap_prevents_download_after_estimate(self):
        from scripts.download_copernicus import main
        from tests.test_copernicus_import import RequestSelectionTests
        catalogue = RequestSelectionTests().catalogue(WAVE_FIELDS)
        catalogue.products[0].datasets[0].dataset_id = 'cmems_mod_bal_wav_anfc_PT1H-i'
        calls = []
        def subset(**kwargs):
            calls.append(kwargs)
            if not kwargs.get('dry_run'):
                self.fail('No download is allowed after budget rejection')
            return NS(file_size=.01, data_transfer_size=2048)
        marine = NS(__version__='2.5.0', describe=lambda **kw: catalogue, subset=subset)
        with tempfile.TemporaryDirectory() as temp, patch.dict('sys.modules', copernicusmarine=marine), patch(
                'scripts.download_copernicus.socket.getaddrinfo'):
            with self.assertRaisesRegex(ValueError, 'per-request'):
                main(['--output', str(Path(temp)/'out'), '--cache', str(Path(temp)/'cache'),
                      '--products', 'waves', '--transfer-budget-gb', '1'])
            self.assertEqual(len(calls), 1)
            self.assertFalse(list(Path(temp).rglob('data.nc')))
