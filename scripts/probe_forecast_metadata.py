"""Bounded metadata investigation, never a weather subset or original-file fetch.

MET: fixed operational forecast DDS/DAS and time-coordinate ASCII only.
Copernicus: original-file listing with create_file_list AND dry_run enabled.
Neither a file modification date nor a filename is accepted as model issuance.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import socket
from urllib.request import Request, urlopen


MET_BASE = ('https://thredds.met.no/thredds/dodsC/metpparchive/2026/10/13/'
            'met_forecast_1_0km_nordic_20261013T00Z.nc')
MET_URLS = {'met-forecast.dds': MET_BASE + '.dds',
            'met-forecast.das': MET_BASE + '.das',
            'met-time-coordinates.txt': MET_BASE + '.ascii?forecast_reference_time,time'}
MAX_METADATA_BYTES = 512_000
MARINE_LISTS = (('waves', 'cmems_mod_bal_wav_anfc_PT1H-i', '202311'),
                ('current', 'cmems_mod_bal_phy_anfc_PT1H-i', '202411'))


def read_met_metadata(url):
    if url not in MET_URLS.values():
        raise ValueError('Only the reviewed metadata endpoints are allowed')
    request = Request(url, headers={'User-Agent': 'SeaParser-metadata-audit/0.1 (+https://seaparser.com)',
                                   'Accept-Encoding': 'identity'})
    with urlopen(request, timeout=15) as response:
        data = response.read(MAX_METADATA_BYTES + 1)
    if len(data) > MAX_METADATA_BYTES:
        raise ValueError('Metadata response size budget exceeded')
    text = data.decode('utf-8')
    if not text.lstrip().startswith(('Dataset {', 'Attributes {')):
        raise ValueError('Response is not DAP metadata')
    return data


def list_marine_metadata(marine, output):
    if marine.__version__ != '2.5.0':
        raise ValueError('Reviewed Toolbox 2.5.0 required')
    # Fail before starting Toolbox retry loops if the catalogue cannot resolve.
    socket.getaddrinfo('stac.marine.copernicus.eu', 443)
    entries = []
    for label, dataset_id, version in MARINE_LISTS:
        filename = f'{label}-original-files.csv'
        response = marine.get(dataset_id=dataset_id, dataset_version=version,
                              filter='*20261013*', create_file_list=filename,
                              output_directory=output, dry_run=True,
                              disable_progress_bar=True, max_concurrent_requests=1)
        if response.files or response.number_of_files_to_download != 0:
            raise ValueError('Metadata-only operation must not download original files')
        path = output / filename
        if not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
            raise ValueError('File-list metadata missing or exceeds budget')
        entries.append({'product': label, 'dataset_id': dataset_id, 'version': version,
                        'filename': filename, 'sha256': sha256(path.read_bytes()).hexdigest(),
                        'status': 'file_list_only', 'model_issue_time': None})
    return entries


def probe(output, met_reader=read_met_metadata, marine=None):
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {'schema': 1, 'started_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'metadata_only', 'met': [], 'copernicus': [],
              'routing_status': 'data_unavailable',
              'blockers': ['regional_wind_not_imported', 'marine_model_issue_time_unverified',
                           'cross_product_model_run_compatibility_unverified']}
    for filename, url in MET_URLS.items():
        entry = {'filename': filename, 'url': url}
        try:
            data = met_reader(url)
            (output / filename).write_bytes(data)
            entry.update(status='metadata_received', bytes=len(data), sha256=sha256(data).hexdigest())
        except Exception as error:
            # Type only: do not echo library messages which could include auth/URLs.
            entry.update(status='blocked', error_type=type(error).__name__)
        report['met'].append(entry)
    try:
        if marine is None:
            import copernicusmarine as marine
        report['copernicus'] = list_marine_metadata(marine, output)
    except Exception as error:
        report['copernicus'] = [{'status': 'blocked', 'error_type': type(error).__name__}]
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    report['metadata_complete'] = (all(x['status'] == 'metadata_received' for x in report['met'])
                                   and len(report['copernicus']) == 2
                                   and all(x['status'] == 'file_list_only' for x in report['copernicus']))
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
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
