from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.probe_forecast_metadata import MAX_METADATA_BYTES, MET_URLS, list_marine_metadata, probe, read_met_metadata


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
            with patch('scripts.probe_forecast_metadata.urlopen') as opener:
                opener.return_value.__enter__.return_value = response
                with self.assertRaises(ValueError):
                    read_met_metadata(next(iter(MET_URLS.values())))

    def test_marine_get_is_strictly_listing_and_dry_run(self):
        calls = []
        def get(**kwargs):
            calls.append(kwargs)
            (kwargs['output_directory'] / kwargs['create_file_list']).write_text('filename,size,last_modified_datetime,etag\n')
            return SimpleNamespace(files=[], number_of_files_to_download=0)
        marine = SimpleNamespace(__version__='2.5.0', get=get)
        with tempfile.TemporaryDirectory() as directory, patch('scripts.probe_forecast_metadata.socket.getaddrinfo'):
            entries = list_marine_metadata(marine, Path(directory))
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(k['dry_run'] and k['create_file_list'].endswith('.csv') for k in calls))
        self.assertTrue(all('username' not in k and 'password' not in k for k in calls))
        self.assertTrue(all(x['model_issue_time'] is None for x in entries))

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
