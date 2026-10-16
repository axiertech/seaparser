from pathlib import Path
from contextlib import nullcontext
from io import BytesIO
from hashlib import sha256
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request

from scripts.probe_forecast_metadata import MAX_METADATA_BYTES, MET_URLS, MetadataRedirectRejected, list_marine_metadata, probe, read_met_metadata


class MetadataProbeTests(unittest.TestCase):
    def test_interrupted_marine_step_preserves_completed_product_and_met(self):
        def get(**kwargs):
            if kwargs['create_file_list'].startswith('current'):
                raise KeyboardInterrupt('synthetic interruption; must not be logged')
            (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                'filename,size,last_modified_datetime,etag\nforecast.nc,123,date,hash\n')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            output = Path(directory)/'probe'
            with self.assertRaises(KeyboardInterrupt):
                probe(output, met_reader=lambda url: b'Dataset { } test;', marine=marine)
            report = json.loads((output/'report.json').read_text())
        self.assertEqual(report['attempt_status'], 'in_progress')
        self.assertEqual(report['active_step'], 'copernicus:current')
        self.assertIsNone(report['finished_at'])
        self.assertFalse(report['metadata_complete'])
        self.assertEqual([x['status'] for x in report['copernicus']], ['file_list_only', 'in_progress'])
        self.assertEqual(len(report['copernicus'][0]['sha256']), 64)
        self.assertEqual([x['status'] for x in report['met']], ['metadata_received'] * 3)
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertEqual(len(report['blockers']), 3)
        self.assertNotIn('synthetic interruption', str(report))

    def test_interrupted_met_step_leaves_parseable_initial_checkpoint(self):
        def interrupted(url):
            raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'probe'
            with self.assertRaises(KeyboardInterrupt):
                probe(output, met_reader=interrupted, marine=object())
            report = json.loads((output/'report.json').read_text())
            self.assertFalse((output/'.report.json.tmp').exists())
        self.assertEqual(report['attempt_status'], 'in_progress')
        self.assertEqual(report['active_step'], 'met-forecast.dds')
        self.assertEqual(report['met'], [])
        self.assertFalse(report['metadata_complete'])

    def test_never_fetches_full_netcdf_or_wind_values(self):
        for url in ('https://example.com/file.nc', next(iter(MET_URLS.values())).removesuffix('.dds')):
            with self.assertRaises(ValueError):
                read_met_metadata(url)
        self.assertTrue(all('.nc.' in u for u in MET_URLS.values()))
        self.assertNotIn('wind_speed_10m', MET_URLS['met-time-coordinates.txt'])

    def test_metadata_size_and_html_rejected(self):
        for content in (b'X' * (MAX_METADATA_BYTES + 1), b'<html>not data</html>'):
            response = SimpleNamespace(read=lambda n: content)
            with patch('scripts.probe_forecast_metadata.MET_OPENER.open') as opener:
                opener.return_value.__enter__.return_value = response
                with self.assertRaises(ValueError):
                    read_met_metadata(next(iter(MET_URLS.values())))

    def test_met_response_type_matches_requested_endpoint(self):
        # Synthetic DAP envelopes: transport validation, not real source evidence.
        for filename, url in MET_URLS.items():
            expected = b'Attributes { }' if filename.endswith('.das') else b'Dataset { } test;'
            wrong = b'Dataset { } test;' if filename.endswith('.das') else b'Attributes { }'
            for content, accepted in ((expected, True), (wrong, False)):
                with self.subTest(filename=filename, accepted=accepted):
                    with patch('scripts.probe_forecast_metadata.MET_OPENER.open') as opener:
                        opener.return_value.__enter__.return_value.read.return_value = content
                        if accepted:
                            self.assertEqual(read_met_metadata(url), content)
                        else:
                            with self.assertRaises(ValueError):
                                read_met_metadata(url)

    def test_redirect_rejected_before_any_destination_request(self):
        original = Request(MET_URLS['met-forecast.dds'])
        handler = MetadataRedirectRejected()
        handler.parent = Mock()
        for code in (301, 302, 303, 307, 308):
            for destination in (MET_URLS['met-forecast.dds'],
                                MET_URLS['met-forecast.dds'].removesuffix('.dds'),
                                'https://example.com/private?token=synthetic-secret'):
                with self.subTest(code=code, destination=destination):
                    with self.assertRaises(ValueError) as error:
                        getattr(handler, f'http_error_{code}')(
                            original, BytesIO(), code, 'redirect', {'location': destination})
                    self.assertNotIn('synthetic-secret', str(error.exception))
                    handler.parent.open.assert_not_called()

    def test_redirect_failure_preserves_independent_probe_results(self):
        def open_metadata(request, **kwargs):
            if request.full_url.endswith('.dds'):
                return MetadataRedirectRejected().redirect_request(
                    request, None, 302, 'redirect', {}, 'https://example.com/full.nc')
            content = b'Attributes { }' if request.full_url.endswith('.das') else b'Dataset { } test;'
            response = SimpleNamespace(read=lambda n: content)
            return nullcontext(response)
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.probe_forecast_metadata.MET_OPENER.open', side_effect=open_metadata), \
                    patch('scripts.probe_forecast_metadata.list_marine_metadata', return_value=[]):
                report = probe(Path(directory)/'probe', marine=object())
            self.assertFalse((Path(directory)/'probe'/'met-forecast.dds').exists())
        self.assertEqual([x['status'] for x in report['met']],
                         ['blocked', 'metadata_received', 'metadata_received'])
        self.assertFalse(report['metadata_complete'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertEqual(len(report['blockers']), 3)

    def test_marine_get_is_strictly_listing_and_dry_run(self):
        calls = []
        def get(**kwargs):
            calls.append(kwargs)
            (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                'filename,size,last_modified_datetime,etag\nforecast.nc,123,2026-10-13T00:00:00Z,hash\n')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            entries = list_marine_metadata(marine, Path(directory))
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(k['dry_run'] and k['create_file_list'].endswith('.csv') for k in calls))
        self.assertTrue(all('username' not in k and 'password' not in k for k in calls))
        self.assertTrue(all(x['model_issue_time'] is None for x in entries))
        self.assertTrue(all(x['file_count'] == 1 and x['status'] == 'file_list_only' for x in entries))

    def test_independent_marine_selection_never_calls_the_other_product(self):
        for product in ('waves', 'current'):
            calls = []
            def get(**kwargs):
                calls.append(kwargs)
                (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                    'filename,size,last_modified_datetime,etag\nforecast.nc,123,date,hash\n')
                return SimpleNamespace(files=[], number_of_files_to_download=0)
            marine = SimpleNamespace(__version__='2.5.0', get=get)
            with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
                entries = list_marine_metadata(marine, Path(directory), product=product)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]['create_file_list'], product + '-original-files.csv')
            self.assertTrue(calls[0]['dry_run'])
            self.assertEqual([e['product'] for e in entries], [product])
            self.assertEqual(entries[0]['status'], 'file_list_only')
            self.assertIsNone(entries[0]['model_issue_time'])

    def test_unknown_marine_selection_rejected_before_transport(self):
        with patch('scripts.probe_forecast_metadata.socket.getaddrinfo') as dns:
            with self.assertRaises(ValueError):
                list_marine_metadata(object(), Path('/unused'), product='unreviewed')
        dns.assert_not_called()

    def test_marine_failure_preserves_other_product_and_redacts_error(self):
        for failed_product in ('waves', 'current'):
            calls = []
            def get(**kwargs):
                calls.append(kwargs['dataset_id'])
                if kwargs['create_file_list'].startswith(failed_product):
                    raise OSError('private credential must not be logged')
                (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                    'filename,size,last_modified_datetime,etag\nforecast.nc,123,date,hash\n')
                return SimpleNamespace(files=[], number_of_files_to_download=0)
            marine = SimpleNamespace(__version__='2.5.0', get=get)
            with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
                entries = list_marine_metadata(marine, Path(directory))
            self.assertEqual(len(calls), 2)
            self.assertEqual([x['status'] for x in entries],
                             ['blocked', 'file_list_only'] if failed_product == 'waves'
                             else ['file_list_only', 'blocked'])
            self.assertNotIn('private credential', str(entries))
            self.assertTrue(all(x['model_issue_time'] is None for x in entries))

    def test_empty_and_invalid_marine_lists_are_not_complete(self):
        for content, expected in (
            ('filename,size,last_modified_datetime,etag\n', 'no_matching_files'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,112961233.0,date,hash\n', 'file_list_only'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,123.00,date,hash\n', 'file_list_only'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,123.5,date,hash\n', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,-1,date,hash\n', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,NaN,date,hash\n', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,Infinity,date,hash\n', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,1e3,date,hash\n', 'blocked'),
            ('<html>not a file list</html>', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,unknown,date,hash\n', 'blocked'),
            ('filename,size,last_modified_datetime,etag\nfile.nc,123,date\n', 'blocked'),
            ('X' * (MAX_METADATA_BYTES + 1), 'blocked'),
        ):
            def get(**kwargs):
                (kwargs['output_directory'] / kwargs['create_file_list']).write_text(content)
                return SimpleNamespace(files=[], number_of_files_to_download=0)
            marine = SimpleNamespace(__version__='2.5.0', get=get)
            with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
                report = probe(Path(directory)/'probe', met_reader=lambda url: b'Dataset { } test;', marine=marine)
            self.assertEqual(report['metadata_complete'], expected == 'file_list_only')
            self.assertTrue(all(x['status'] == expected for x in report['copernicus']))
            self.assertEqual(report['routing_status'], 'data_unavailable')

    def test_bounded_invalid_csv_retains_transport_hash_not_validation(self):
        data = b'not the expected CSV header\n'
        def get(**kwargs):
            (kwargs['output_directory'] / kwargs['create_file_list']).write_bytes(data)
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            entries = list_marine_metadata(marine, Path(directory))
        for entry in entries:
            self.assertEqual(entry['status'], 'blocked')
            self.assertEqual(entry['bytes'], len(data))
            self.assertEqual(entry['sha256'], sha256(data).hexdigest())
            self.assertNotIn('file_count', entry)
            self.assertIsNone(entry['model_issue_time'])

    def test_file_growth_cannot_bypass_metadata_read_budget(self):
        def get(**kwargs):
            (kwargs['output_directory'] / kwargs['create_file_list']).write_bytes(b'small at stat')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        original_open = Path.open
        handles = []
        def open_file(path, mode='r', *args, **kwargs):
            if mode == 'rb':
                handle = Mock(wraps=BytesIO(b'X' * (MAX_METADATA_BYTES + 2)))
                handle.__enter__ = Mock(return_value=handle)
                handle.__exit__ = Mock(return_value=False)
                handles.append(handle)
                return handle
            return original_open(path, mode, *args, **kwargs)
        with tempfile.TemporaryDirectory() as directory, \
                patch('scripts.probe_forecast_metadata.socket.getaddrinfo'), \
                patch.object(Path, 'open', open_file):
            entries = list_marine_metadata(marine, Path(directory))
        self.assertEqual(len(handles), 2)
        for handle in handles:
            handle.read.assert_called_once_with(MAX_METADATA_BYTES + 1)
        self.assertTrue(all(entry['status'] == 'blocked' for entry in entries))
        self.assertTrue(all('sha256' not in entry for entry in entries))

    def test_complete_transport_never_removes_planning_blockers(self):
        def get(**kwargs):
            (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                'filename,size,last_modified_datetime,etag\nforecast.nc,123,date,hash\n')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            report = probe(Path(directory)/'probe', met_reader=lambda url: b'Dataset { } test;', marine=marine)
        self.assertTrue(report['metadata_complete'])
        self.assertEqual(report['attempt_status'], 'finished')
        self.assertIsNotNone(report['finished_at'])
        self.assertIsNone(report['active_step'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertEqual(len(report['blockers']), 3)
        self.assertTrue(all(x['model_issue_time'] is None for x in report['copernicus']))

    def test_partial_blocker_does_not_skip_independent_metadata(self):
        calls = []
        def reader(url):
            calls.append(url)
            if url.endswith('.das'):
                raise OSError('private diagnostic must not be logged')
            return b'Dataset { Float64 time[time = 5]; } test;'
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.probe_forecast_metadata.list_marine_metadata', return_value=[]):
                report = probe(Path(directory)/'probe', met_reader=reader, marine=object())
        self.assertEqual(len(calls), 3)
        self.assertFalse(report['metadata_complete'])
        self.assertEqual(report['routing_status'], 'data_unavailable')
        self.assertEqual(report['met'][1]['error_type'], 'OSError')
        self.assertNotIn('private diagnostic', str(report))
