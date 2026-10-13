from pathlib import Path
from contextlib import nullcontext
from io import BytesIO
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request

from scripts.probe_forecast_metadata import MAX_METADATA_BYTES, MET_URLS, MetadataRedirectRejected, list_marine_metadata, probe, read_met_metadata


class MetadataProbeTests(unittest.TestCase):
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
            self.assertFalse(report['metadata_complete'])
            self.assertTrue(all(x['status'] == expected for x in report['copernicus']))
            self.assertEqual(report['routing_status'], 'data_unavailable')

    def test_complete_transport_never_removes_planning_blockers(self):
        def get(**kwargs):
            (kwargs['output_directory'] / kwargs['create_file_list']).write_text(
                'filename,size,last_modified_datetime,etag\nforecast.nc,123,date,hash\n')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            report = probe(Path(directory)/'probe', met_reader=lambda url: b'Dataset { } test;', marine=marine)
        self.assertTrue(report['metadata_complete'])
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
