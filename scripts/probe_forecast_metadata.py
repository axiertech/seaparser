"""Bounded metadata investigation, never a weather subset or original-file fetch.

MET: fixed operational forecast DDS/DAS and time-coordinate ASCII only.
Copernicus: original-file listing with create_file_list AND dry_run enabled.
Neither a file modification date nor a filename is accepted as model issuance.
"""
import argparse
import csv
from io import StringIO
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import socket
from urllib.request import HTTPRedirectHandler, Request, build_opener


MET_BASE = ('https://thredds.met.no/thredds/dodsC/metpparchive/2026/10/13/'
            'met_forecast_1_0km_nordic_20261013T00Z.nc')
MET_URLS = {'met-forecast.dds': MET_BASE + '.dds',
            'met-forecast.das': MET_BASE + '.das',
            'met-time-coordinates.txt': MET_BASE + '.ascii?forecast_reference_time,time'}
MAX_METADATA_BYTES = 512_000
MARINE_LISTS = (('waves', 'cmems_mod_bal_wav_anfc_PT1H-i', '202311'),
                ('current', 'cmems_mod_bal_phy_anfc_PT1H-i', '202411'))


class MetadataRedirectRejected(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A reviewed metadata URL must not silently become a weather-file fetch.
        # Do not include the destination, which could contain private query data.
        raise ValueError('Metadata redirects require separate source review')


MET_OPENER = build_opener(MetadataRedirectRejected())


def read_met_metadata(url):
    if url not in MET_URLS.values():
        raise ValueError('Only the reviewed metadata endpoints are allowed')
    request = Request(url, headers={'User-Agent': 'SeaParser-metadata-audit/0.1 (+https://seaparser.com)',
                                   'Accept-Encoding': 'identity'})
    with MET_OPENER.open(request, timeout=15) as response:
        data = response.read(MAX_METADATA_BYTES + 1)
    if len(data) > MAX_METADATA_BYTES:
        raise ValueError('Metadata response size budget exceeded')
    text = data.decode('utf-8')
    expected = 'Attributes {' if url == MET_URLS['met-forecast.das'] else 'Dataset {'
    if not text.lstrip().startswith(expected):
        raise ValueError('Response does not match the requested DAP metadata type')
    return data


def list_marine_metadata(marine, output, progress=None, *, product=None):
    if product is not None and product not in ('waves', 'current'):
        raise ValueError('Only reviewed marine products may be selected')
    if marine.__version__ != '2.5.0':
        raise ValueError('Reviewed Toolbox 2.5.0 required')
    # Fail before starting Toolbox retry loops if the catalogue cannot resolve.
    socket.getaddrinfo('stac.marine.copernicus.eu', 443)
    entries = []
    for label, dataset_id, version in MARINE_LISTS:
        if product is not None and label != product:
            continue
        filename = f'{label}-original-files.csv'
        entry = {'product': label, 'dataset_id': dataset_id, 'version': version,
                 'filename': filename, 'model_issue_time': None, 'status': 'in_progress'}
        entries.append(entry)
        if progress is not None:
            progress(entries)
        try:
            response = marine.get(dataset_id=dataset_id, dataset_version=version,
                                  filter='*20261013*', create_file_list=filename,
                                  output_directory=output, dry_run=True,
                                  disable_progress_bar=True, max_concurrent_requests=1)
            if response.files or response.number_of_files_to_download != 0:
                raise ValueError('Metadata-only operation must not download original files')
            path = output / filename
            if not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
                raise ValueError('File-list metadata missing or exceeds budget')
            # Recheck bytes actually read: a preceding stat is not a read budget.
            with path.open('rb') as handle:
                data = handle.read(MAX_METADATA_BYTES + 1)
            if len(data) > MAX_METADATA_BYTES:
                raise ValueError('File-list metadata exceeds read budget')
            # Preserve bounded transport evidence even if CSV validation fails.
            entry.update(bytes=len(data), sha256=sha256(data).hexdigest())
            rows = list(csv.reader(StringIO(data.decode('utf-8'), newline=''), strict=True))
            if not rows or rows[0] != ['filename', 'size', 'last_modified_datetime', 'etag']:
                raise ValueError('Unexpected file-list columns')
            if any(len(row) != 4 or not row[0] or not row[1].isdigit() for row in rows[1:]):
                raise ValueError('Invalid file-list row')
            entry.update(file_count=len(rows) - 1,
                         status='file_list_only' if len(rows) > 1 else 'no_matching_files')
        except Exception as error:
            # Preserve other products' evidence without disclosing library messages.
            entry.update(status='blocked', error_type=type(error).__name__)
        if progress is not None:
            progress(entries)
    return entries


def write_report(output, report):
    # Readers see either the preceding complete JSON or the new complete JSON.
    temporary = output / '.report.json.tmp'
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(output / 'report.json')


def probe(output, met_reader=read_met_metadata, marine=None):
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {'schema': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'metadata_only', 'met': [], 'copernicus': [],
              'attempt_status': 'in_progress', 'active_step': 'starting',
              'finished_at': None, 'metadata_complete': False,
              'routing_status': 'data_unavailable',
              'blockers': ['regional_wind_not_imported', 'marine_model_issue_time_unverified',
                           'cross_product_model_run_compatibility_unverified']}
    write_report(output, report)
    for filename, url in MET_URLS.items():
        report['active_step'] = filename
        write_report(output, report)
        entry = {'filename': filename, 'url': url}
        try:
            data = met_reader(url)
            (output / filename).write_bytes(data)
            entry.update(status='metadata_received', bytes=len(data), sha256=sha256(data).hexdigest())
        except Exception as error:
            # Type only: do not echo library messages which could include auth/URLs.
            entry.update(status='blocked', error_type=type(error).__name__)
        report['met'].append(entry)
        write_report(output, report)
    report['active_step'] = 'copernicus_preflight'
    write_report(output, report)

    def marine_progress(entries):
        report['copernicus'] = entries
        report['active_step'] = 'copernicus:' + entries[-1]['product']
        write_report(output, report)

    try:
        if marine is None:
            import copernicusmarine as marine
        report['copernicus'] = list_marine_metadata(marine, output, progress=marine_progress)
    except Exception as error:
        report['copernicus'] = [{'status': 'blocked', 'error_type': type(error).__name__}]
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    report['attempt_status'] = 'finished'
    report['active_step'] = None
    report['metadata_complete'] = (all(x['status'] == 'metadata_received' for x in report['met'])
                                   and len(report['copernicus']) == 2
                                   and all(x['status'] == 'file_list_only' for x in report['copernicus']))
    write_report(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    # Use saved auth only. No login, credential copy, or values in the arguments.
    for name in ('COPERNICUSMARINE_SERVICE_USERNAME', 'COPERNICUSMARINE_SERVICE_PASSWORD'):
        os.environ.pop(name, None)
    report = probe(args.output)
    print(f'METADATA_COMPLETE={report["metadata_complete"]}; REPORT={args.output / "report.json"}')
    return 0 if report['metadata_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
