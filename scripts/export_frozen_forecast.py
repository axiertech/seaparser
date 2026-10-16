"""Build an offline Vinga raw-sample review; never publish or qualify routing."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from shlex import join as shell_join

from application.native_wind_support import SourceLocalSegment, inspect_native_segment, inspect_source_local_segment
from presentation.frozen_forecast_html import render_frozen_forecast
from scripts.audit_met_metadata import PROJ4, read_wind_sample
from scripts.freeze_copernicus_reference import freeze_with_audit
from scripts.native_wind_segment import read_segment_snapshot
from scripts.regional_forecast import native_wind_from_snapshot

ROOT = Path(__file__).resolve().parents[1]


def build_review(fixtures, segment_path=None, *, max_cells=512):
    fixtures = Path(fixtures)
    snapshot = read_wind_sample(
        fixtures / 'met-nordic-wind-sample', fixtures / 'met-nordic-metadata')
    metadata, digest, axes, epochs, values = snapshot
    payload, audit = freeze_with_audit(fixtures / 'vinga-copernicus')
    rows, columns = len(axes['y']), len(axes['x'])
    def planes(flat):
        return [[[float(v) for v in flat[k * rows * columns + j * columns:
                                        k * rows * columns + (j + 1) * columns]]
                 for j in range(rows)] for k in range(len(epochs))]
    def instant(epoch):
        return datetime.fromtimestamp(int(epoch), timezone.utc).isoformat()
    def field(label, unit, data):
        return {'label': label, 'unit': unit, 'values': data}
    coordinates = metadata['source_coordinates']
    wind = {
        'id': 'wind', 'label': 'Vind · MET Norway',
        'dataset': 'MET Nordic · met_forecast_1_0km_nordic_20261013T00Z',
        'times': [instant(t) for t in epochs],
        'x': [float(v) for v in axes['x']], 'y': [float(v) for v in axes['y']],
        'axis_labels': ['Projektion x (m)', 'Projektion y (m)'],
        'latitude': [[float(v) for v in row] for row in coordinates['latitude']],
        'longitude': [[float(v) for v in row] for row in coordinates['longitude']],
        'projection': PROJ4,
        'fields': {
            'speed': field('Vindstyrka på 10 m', 'm/s', planes(values['wind_speed_10m'])),
            'direction': field('Vindriktning FRÅN', '°', planes(values['wind_direction_10m']))},
        'mask': None,
        'land_fraction': [[float(v) for v in values['land_area_fraction'][j*columns:(j+1)*columns]]
                          for j in range(rows)],
        'mask_note': 'Ingen kvalificerad giltighetsmask. Markandel visas separat och avgör inte vindens giltighet.',
        'semantics': '10 m över mark, 600 s medel. Medelperiodens placering i tiden är okänd. '
                     'Riktningen anger varifrån vinden kommer; sann nord eller modellens nord är inte kvalificerat. '
                     'Inga pilar eller vektoromvandlingar visas. Geodetisk överensstämmelse är inte verifierad.',
        'model_reference_time': instant(Decimal(metadata['model_reference']['epoch_seconds'])),
        'issued_at': None, 'run_identity': None,
        'mask_source': None,
        'source_hashes': dict(metadata['source_hashes'], **{'native-wind-land.txt': digest}),
        'attribution': 'Norwegian Meteorological Institute, met.no',
        'source_url': 'https://thredds.met.no/thredds/catalog/metpparchive/2026/10/13/catalog.html',
        'license_url': 'https://www.met.no/en/free-meteorological-data/Licensing-and-crediting',
    }
    products = [wind]
    labels = {'VHM0': ('Signifikant våghöjd', 'm'), 'VTM02': ('Vågperiod Tm02', 's'),
              'VMDR': ('Vågriktning FRÅN sann nord', '°'),
              'uo': ('Ström mot öster', 'm/s'), 'vo': ('Ström mot norr', 'm/s')}
    for name, title in [('waves', 'Vågor'), ('current', 'Ström')]:
        raw = payload['products'][name]
        lat, lon = raw['latitude'], raw['longitude']
        products.append({
            'id': name, 'label': title + ' · Copernicus Marine',
            'dataset': raw['dataset_id'] + ' · katalogversion ' + raw['version'],
            'times': raw['times'], 'x': lon, 'y': lat,
            'axis_labels': ['Longitud (° öst)', 'Latitud (° nord)'],
            'latitude': [[v for _ in lon] for v in lat],
            'longitude': [list(lon) for _ in lat],
            'projection': 'Källans latitud/longitud; inget gemensamt rutnät antas.',
            'fields': {key: field(*labels[key], data) for key, data in raw['data'].items()},
            'source_time_means': {key: audit[name]['variables'][key]['cell_methods']
                                  for key in raw['data']},
            'mask': payload['products']['static']['data']['mask'] if name == 'waves' else None,
            'land_fraction': None,
            'mask_note': ('Separat vågmask: 1 = hav, 0 = land, okänt = saknat. '
                          'Den beskriver inte navigerbarhet eller strömmens giltighet.' if name == 'waves' else
                          'Strömmens egen våt-/giltighetsmask saknas. Finita värden är råprov, inte kvalificerat stöd.'),
            'semantics': ('Tm02 är spektral vågmedelperiod, inte prognosens tidsmedel. '
                          'Vågriktning är FRÅN sann nord enligt källfältet. Källan anger tidsmedel, '
                          'men dess längd och placering i tiden är okända.' if name == 'waves' else
                          'Ström mot öster och norr, relativt marken. Negativa värden betyder väster '
                          'respektive söder. Djup: ' + str(raw['depth_m']) +
                          ' m. Källan beskriver inte tidsmedlet; dess längd och placering i tiden är okända. '
                          'Omvandling till ruttens lokala ram är inte kvalificerad.'),
            'model_reference_time': audit[name]['forecast_reference_time'],
            'issued_at': None, 'run_identity': None,
            'mask_source': (payload['products']['static']['dataset_id'] + ' · katalogversion ' +
                            payload['products']['static']['version']) if name == 'waves' else None,
            'source_hashes': {filename: value for filename, value in audit['manifest_file_hashes'].items()
                              if filename == ('waves.nc' if name == 'waves' else 'current.nc')
                              or name == 'waves' and filename == 'wave-mask.nc'},
            'attribution': 'Generated using E.U. Copernicus Marine Service Information; '
                           'DOI: 10.48670/moi-00010, 10.48670/moi-00011',
            'source_url': raw['source_url'], 'license_url': raw['license_url'],
        })
    segment,segment_hash = read_segment_snapshot(
        Path(segment_path) if segment_path is not None else ROOT / 'fixtures/met-source-local-segment.json')
    inspect = inspect_source_local_segment if isinstance(segment,SourceLocalSegment) else inspect_native_segment
    segment_review = inspect(native_wind_from_snapshot(snapshot),segment,max_cells=max_cells)
    return {'schema': 1, 'historical': True, 'routing_qualified': False,
            'products': products, 'run_compatibility': None, 'segment_review': segment_review,
            'segment_source_sha256':segment_hash}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=ROOT / 'fixtures')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--segment', type=Path, help='Explicit mathematical source-sphere segment JSON')
    parser.add_argument('--segment-max-cells', type=int, default=512)
    args = parser.parse_args()
    review = build_review(args.fixtures,args.segment,max_cells=args.segment_max_cells)
    page = render_frozen_forecast(review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding='utf-8')
    command=['python','-B','-m','scripts.export_frozen_forecast','--output',str(args.output)]
    if args.segment is not None:
        command.extend(['--segment',str(args.segment)])
    if args.segment_max_cells != 512:
        command.extend(['--segment-max-cells',str(args.segment_max_cells)])
    if args.fixtures != ROOT / 'fixtures':
        command.extend(['--fixtures',str(args.fixtures)])
    receipt = {'artifact': args.output.name, 'sha256': sha256(page.encode()).hexdigest(),
               'data_sha256': sha256(json.dumps(review, sort_keys=True).encode()).hexdigest(),
               'segment_source_sha256':review['segment_source_sha256'],
               'build_command': shell_join(command),
               'published': False}
    args.output.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
