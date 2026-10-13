"""Offline audit of the reviewed frozen MET DAP metadata, never a wind adapter."""
import argparse
from decimal import Decimal
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re

from pyproj import CRS, Transformer

MAX_BYTES = 512_000
SOURCE_FILES = {'met-forecast.dds', 'met-forecast.das', 'met-time-coordinates.txt',
                'native-axes.txt', 'vinga-latlon.txt'}
PROJ4 = '+proj=lcc +lat_0=63 +lon_0=15 +lat_1=63 +lat_2=63 +no_defs +R=6.371e+06'
TIME_UNITS = 'seconds since 1970-01-01 00:00:00 +00:00'


def time_metadata(dds, das, ascii_text):
    """Validate only the frozen DAP layout, not arbitrary DAP datasets."""
    for text in (dds, ascii_text.split('---------------------------------------------')[0]):
        if (re.findall(r'^    Float64 time[^\n]*$', text, re.M) != ['    Float64 time[time = 59];']
                or len(re.findall(r'^    Float64 forecast_reference_time;$', text, re.M)) != 1):
            raise ValueError('Reviewed DDS/ASCII time declarations required')
    for name in ('wind_speed_10m', 'wind_direction_10m'):
        declaration = f'Float32 {name}[time = 59][y = 2321][x = 1796];'
        if dds.count(declaration) != 1:
            raise ValueError('Reviewed wind DDS dimensions required')
    for name in ('time', 'forecast_reference_time'):
        blocks = re.findall(r'^    ' + name + r' \{\n([^{}]*)^    \}', das, re.M)
        if len(blocks) != 1:
            raise ValueError('Unambiguous DAS time attributes required')
        for attribute, value in (('units', TIME_UNITS), ('standard_name', name)):
            values = re.findall(r'^        String ' + attribute + r' "([^"]*)";$', blocks[0], re.M)
            if values != [value]:
                raise ValueError('Reviewed UTC time units and standard names required')
        if re.search(r'\bcalendar\b', blocks[0]):
            raise ValueError('Calendar attribute differs from reviewed absent metadata')
    references = re.findall(r'^forecast_reference_time, ([^\n]+)$', ascii_text, re.M)
    if len(references) != 1:
        raise ValueError('Unambiguous ASCII model reference required')
    reference = numbers(references[0], 1)[0]
    if reference != Decimal(1791849600):
        raise ValueError('Model reference differs from reviewed source value')
    return reference


def bounded_read(directory, filename, *, limit=MAX_BYTES):
    path = directory / filename
    with path.open('rb') as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Metadata byte budget exceeded')
    return data


def numbers(line, count):
    values = tuple(Decimal(value.strip()) for value in line.split(','))
    if len(values) != count or not all(value.is_finite() for value in values):
        raise ValueError('Finite coordinate values and exact dimensions required')
    return values


def axis(text, name, count):
    matches = re.findall(r'^' + re.escape(name) + r'\[' + str(count) + r'\]\n([^\n]+)', text, re.M)
    if len(matches) != 1:
        raise ValueError('Unambiguous reviewed ASCII axis required')
    return numbers(matches[0], count)


def matrix(text, name, rows, columns):
    matches = re.findall(r'^' + name + r'\.' + name + r'\[' + str(rows) + r'\]\[' +
                         str(columns) + r'\]\n(.*?)\n\n', text, re.M | re.S)
    if len(matches) != 1 or len(matches[0].splitlines()) != rows:
        raise ValueError('Exact reviewed ASCII matrix required')
    result = []
    for index, line in enumerate(matches[0].splitlines()):
        label, separator, values = line.partition(',')
        if not separator or label != f'[{index}]':
            raise ValueError('Ordered matrix rows required')
        result.append(numbers(values, columns))
    return result


def audit(directory):
    directory = Path(directory)
    manifest = json.loads(bounded_read(directory, 'manifest.json'))
    entries = manifest.get('files', [])
    if (manifest.get('schema') != 1 or len(entries) != len(SOURCE_FILES)
            or {entry['filename'] for entry in entries} != SOURCE_FILES):
        raise ValueError('Complete reviewed five-file metadata manifest required')
    texts, hashes = {}, {}
    for entry in entries:
        data = bounded_read(directory, entry['filename'])
        digest = sha256(data).hexdigest()
        if digest != entry['sha256'] or len(data) != entry['bytes']:
            raise ValueError('Metadata hash or byte count mismatch')
        texts[entry['filename']] = data.decode('utf-8')
        hashes[entry['filename']] = digest
    das = texts['met-forecast.das']
    reference = time_metadata(texts['met-forecast.dds'], das, texts['met-time-coordinates.txt'])
    if f'String proj4 "{PROJ4}";' not in das:
        raise ValueError('Only the reviewed native spherical LCC is supported')
    axes = {name: axis(texts['native-axes.txt'], name, count)
            for name, count in (('x', 1796), ('y', 2321))}
    for values in axes.values():
        if any(b - a != 1000 for a, b in zip(values, values[1:])):
            raise ValueError('Exact 1000 metre increasing native axis required')
    times = axis(texts['met-time-coordinates.txt'], 'time', 59)
    if (times[0] != 1791849600 or times[-1] != 1792058400
            or any(b - a != 3600 for a, b in zip(times, times[1:]))):
        raise ValueError('Reviewed exact hourly validity required')
    subset = manifest['coordinate_subset']
    indices = [subset[key] for key in ('x_first', 'x_last', 'y_first', 'y_last')]
    if any(type(value) is not int for value in indices):
        raise ValueError('Integer source indices required')
    xf, xl, yf, yl = indices
    if not (0 <= xf < xl < len(axes['x']) and 0 <= yf < yl < len(axes['y'])):
        raise ValueError('Subset indices outside native axes')
    rows, columns = yl - yf + 1, xl - xf + 1
    if rows * columns > 1024:
        raise ValueError('Coordinate matrix node budget exceeded')
    text = texts['vinga-latlon.txt']
    latitude, longitude = (matrix(text, name, rows, columns) for name in ('latitude', 'longitude'))
    for name in ('latitude', 'longitude'):
        if (axis(text, name + '.x', columns) != axes['x'][xf:xl + 1]
                or axis(text, name + '.y', rows) != axes['y'][yf:yl + 1]):
            raise ValueError('Subset maps differ from native axes')
    native = CRS.from_proj4(PROJ4)
    inverse = Transformer.from_crs(native, native.geodetic_crs, always_xy=True)
    local = CRS.from_proj4('+proj=aeqd +lat_0=57.633 +lon_0=11.605 +ellps=WGS84 +units=m +no_defs')
    local_transform = Transformer.from_crs('EPSG:4326', local, always_xy=True)
    geod, errors, east, north = native.get_geod(), [], [], []
    for j in range(rows):
        east_row, north_row = [], []
        for i in range(columns):
            lat, lon = float(latitude[j][i]), float(longitude[j][i])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('Geographic coordinate outside bounds')
            plon, plat = inverse.transform(float(axes['x'][xf + i]), float(axes['y'][yf + j]), errcheck=True)
            errors.append(geod.inv(lon, lat, plon, plat)[2])
            e, n = local_transform.transform(lon, lat, errcheck=True)
            east_row.append(e); north_row.append(n)
        east.append(east_row); north.append(north_row)
    east_spread = max(max(row[i] for row in east) - min(row[i] for row in east) for i in range(columns))
    north_spread = max(max(row) - min(row) for row in north)
    if not all(isfinite(value) for value in errors + [east_spread, north_spread]):
        raise ValueError('Nonfinite geometry diagnostic')
    return {'schema': 1, 'scope': 'offline_coordinate_diagnostic_not_routing_qualification',
            'source_hashes': hashes, 'source_node_count': rows * columns,
            'native_axes': {name: {'count': len(values), 'first_m': str(values[0]),
                                  'last_m': str(values[-1]), 'step_m': '1000'}
                            for name, values in axes.items()},
            'validity': {'count': len(times), 'first_epoch_seconds': str(times[0]),
                         'last_epoch_seconds': str(times[-1]), 'step_seconds': '3600'},
            'model_reference': {'epoch_seconds': str(reference), 'units': TIME_UNITS,
                                'calendar_attribute': None, 'meaning': 'model_reference_not_issuance'},
            'source_projection_vs_provider_latlon_max_spherical_distance_m': max(errors),
            'east_variation_across_rows_m': east_spread, 'north_variation_across_columns_m': north_spread,
            'separable_axis_max_error_lower_bound_m': max(east_spread, north_spread) / 2,
            'local_axis_diagnostic': 'Existing WGS84 AEQD; datum equivalence not certified',
            'issued_at': None, 'routing_status': 'data_unavailable',
            'blockers': ['regional_wind_not_imported', 'native_grid_to_local_geometry_unqualified',
                         'model_issue_time_unverified', 'cross_product_model_run_compatibility_unverified']}


def audit_wind_sample(directory, metadata_directory):
    """Describe frozen raw values; no normalization, masks or routing import."""
    metadata = audit(metadata_directory)
    directory, metadata_directory = Path(directory), Path(metadata_directory)
    manifest = json.loads(bounded_read(directory, 'manifest.json'))
    data = bounded_read(directory, 'native-wind-land.txt', limit=128_000)
    digest = sha256(data).hexdigest()
    if len(data) > 128_000 or manifest.get('sha256') != digest or manifest.get('bytes') != len(data):
        raise ValueError('Wind sample hash, byte count or budget mismatch')
    text = data.decode('utf-8')
    references = re.findall(r'^forecast_reference_time, ([^\n]+)$', text, re.M)
    if len(references) != 1 or numbers(references[0], 1)[0] != Decimal(metadata['model_reference']['epoch_seconds']):
        raise ValueError('Wind sample model reference differs from frozen metadata')
    native_axes = bounded_read(metadata_directory, 'native-axes.txt').decode('utf-8')
    expected_axes = {'x': axis(native_axes, 'x', 1796)[692:699],
                     'y': axis(native_axes, 'y', 2321)[509:517]}
    expected_times = axis(bounded_read(metadata_directory, 'met-time-coordinates.txt').decode('utf-8'),
                          'time', 59)[12:17]
    values = {}
    for name in ('wind_speed_10m', 'wind_direction_10m', 'land_area_fraction'):
        for coordinate, expected in expected_axes.items():
            if axis(text, name + '.' + coordinate, len(expected)) != expected:
                raise ValueError('Wind sample maps differ from frozen native axes')
        if name == 'land_area_fraction':
            values[name] = tuple(value for row in matrix(text, name, 8, 7) for value in row)
            continue
        if axis(text, name + '.time', 5) != expected_times:
            raise ValueError('Wind sample times differ from frozen validity')
        blocks = re.findall(r'^' + name + r'\.' + name + r'\[5\]\[8\]\[7\]\n(.*?)\n\n', text, re.M | re.S)
        if len(blocks) != 1 or len(blocks[0].splitlines()) != 40:
            raise ValueError('Reviewed five-plane wind sample required')
        nodes = []
        for index, line in enumerate(blocks[0].splitlines()):
            label, separator, row = line.partition(',')
            if not separator or label != f'[{index // 8}][{index % 8}]':
                raise ValueError('Ordered wind sample rows required')
            nodes.extend(numbers(row, 7))
        values[name] = tuple(nodes)
    if (min(values['wind_speed_10m']) < 0 or min(values['wind_direction_10m']) < 0
            or max(values['wind_direction_10m']) > 360 or min(values['land_area_fraction']) < 0
            or max(values['land_area_fraction']) > 1):
        raise ValueError('Raw wind or land fraction outside physical bounds')
    return {'scope': 'raw_native_sample_not_routing_qualified', 'sha256': digest,
            'metadata_source_hashes': metadata['source_hashes'], 'native_node_count': 56,
            'time_count': 5, 'value_ranges': {name: {'count': len(nodes), 'min': str(min(nodes)),
                                                   'max': str(max(nodes))} for name, nodes in values.items()},
            'land_fraction_nonzero_nodes': sum(value != 0 for value in values['land_area_fraction']),
            'land_fraction_is_validity_mask': False, 'issued_at': None,
            'routing_status': 'data_unavailable', 'blockers': metadata['blockers']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--wind-sample', type=Path, help='Audit the frozen native sample; never qualify routing')
    args = parser.parse_args()
    report = audit(args.directory)
    if args.wind_sample:
        report['wind_sample'] = audit_wind_sample(args.wind_sample, args.directory)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
