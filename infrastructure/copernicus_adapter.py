"""Pure adapter for a frozen, small Copernicus Baltic CF subset.

NetCDF I/O belongs to the acquisition script. This module accepts its detached
metadata/array mapping and returns immutable domain products; it performs no I/O.
"""
from datetime import datetime, timezone
from math import isfinite

from pyproj import CRS, Transformer

from prototype.forecast import utc_time
from prototype.forecast_data import ForecastDataset, GridProduct
from prototype.forecast_metadata import Coverage, ProductMetadata
from .copernicus_fields import BATHY_FIELDS, CURRENT_FIELDS, WAVE_FIELDS, current_node, validate_fields, wave_node


VINGA_ORIGIN = (57.633, 11.605)
VINGA_BBOX = (11.58, 57.62, 11.63, 57.65)
PROJECTION_TOLERANCE_M = 1.0
LICENSE_URL = 'https://marine.copernicus.eu/user-corner/service-commitments-and-license'
WAVE_URL = 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_WAV_003_010/description'
CURRENT_URL = 'https://data.marine.copernicus.eu/product/BALTICSEA_ANALYSISFORECAST_PHY_003_006/description'


def _time(value):
    if not isinstance(value, str):
        raise ValueError('UTC-giltighetstid saknas')
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return utc_time(datetime.fromisoformat(value), 'Giltighetstid')


def _axis(values, name, lower, upper):
    values = tuple(values)
    if (len(values) < 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                               for v in values)
            or any(a >= b for a, b in zip(values, values[1:]))
            or values[0] < lower or values[-1] > upper):
        raise ValueError(f'{name}: koordinaterna måste öka och ligga inom det granskade Vinga-uttaget')
    return values


def _matrix(values, rows, columns, name):
    values = tuple(tuple(row) for row in values)
    if len(values) != rows or any(len(row) != columns for row in values):
        raise ValueError(f'{name}: matrisens dimensioner stämmer inte med koordinaterna')
    return values


def _local_axes(latitude, longitude):
    crs = CRS.from_proj4(
        f'+proj=aeqd +lat_0={VINGA_ORIGIN[0]} +lon_0={VINGA_ORIGIN[1]} '
        '+ellps=WGS84 +units=m +no_defs')
    transformer = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    east = tuple(transformer.transform(lon, VINGA_ORIGIN[0], errcheck=True)[0] for lon in longitude)
    north = tuple(transformer.transform(VINGA_ORIGIN[1], lat, errcheck=True)[1] for lat in latitude)
    for j, lat in enumerate(latitude):
        for i, lon in enumerate(longitude):
            actual_east, actual_north = transformer.transform(lon, lat, errcheck=True)
            if (abs(actual_east-east[i]) > PROJECTION_TOLERANCE_M
                    or abs(actual_north-north[j]) > PROJECTION_TOLERANCE_M):
                raise ValueError('Native lat/lon-grid kan inte representeras i lokala öst/nordaxlar inom 1 m')
    return east, north


class CopernicusMarineAdapter:
    """Normalize only the reviewed Baltic wave/current fixture schema.

    Missing forecast issuance is preserved as None. Such a snapshot cannot pass
    ForecastPolicy and is not a routable forecast. Land/depth are not route
    obstacles; the static mask is used only to preserve missing wave cells.
    """

    def normalize(self, payload):
        try:
            if payload['schema'] != 1:
                raise ValueError('Unsupported Copernicus fixture schema')
            wave = payload['products']['waves']
            current = payload['products']['current']
            static = payload['products']['static']
            wave_product = self._waves(wave, static)
            current_product = self._current(current)
            if (wave_product.metadata.coverage.origin_latitude,
                    wave_product.metadata.coverage.origin_longitude) != VINGA_ORIGIN:
                raise ValueError('Unexpected projection origin')
            return ForecastDataset(payload['bundle_id'], payload['bundle_version'],
                                   (current_product, wave_product))
        except (KeyError, TypeError, IndexError) as error:
            raise ValueError('Incomplete or malformed Copernicus CF fixture') from error

    def _waves(self, raw, static):
        validate_fields(raw['variables'], WAVE_FIELDS)
        validate_fields(static['variables'], BATHY_FIELDS)
        latitude = _axis(raw['latitude'], 'wave latitude', VINGA_BBOX[1], VINGA_BBOX[3])
        longitude = _axis(raw['longitude'], 'wave longitude', VINGA_BBOX[0], VINGA_BBOX[2])
        if tuple(static['latitude']) != latitude or tuple(static['longitude']) != longitude:
            raise ValueError('Static mask grid differs from wave grid; no mask interpolation is allowed')
        mask = _matrix(static['data']['mask'], len(latitude), len(longitude), 'mask')
        _matrix(static['data']['deptho'], len(latitude), len(longitude), 'deptho')
        times = tuple(_time(value) for value in raw['times'])
        if len(times) < 2 or any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError('Wave valid times must increase')
        fields = {name: tuple(_matrix(plane, len(latitude), len(longitude), name)
                              for plane in raw['data'][name]) for name in WAVE_FIELDS}
        if any(len(planes) != len(times) for planes in fields.values()):
            raise ValueError('Wave time axis and samples disagree')
        east, north = _local_axes(latitude, longitude)
        values = tuple(tuple(tuple(wave_node(fields['VHM0'][k][j][i],
                                              fields['VTM02'][k][j][i],
                                              fields['VMDR'][k][j][i], mask[j][i])
                                   for i in range(len(east)))
                             for j in range(len(north))) for k in range(len(times)))
        return self._product(raw, 'waves', east, north, times, values,
                             ('m', 's', '1', '1'), 'ground-from-true-east-north-tm02')

    def _current(self, raw):
        validate_fields(raw['variables'], CURRENT_FIELDS)
        latitude = _axis(raw['latitude'], 'current latitude', VINGA_BBOX[1], VINGA_BBOX[3])
        longitude = _axis(raw['longitude'], 'current longitude', VINGA_BBOX[0], VINGA_BBOX[2])
        depth = tuple(raw['depth_m'])
        if (len(depth) != 1 or isinstance(depth[0], bool) or not isinstance(depth[0], (int, float))
                or not isfinite(depth[0]) or depth[0] <= 0 or depth[0] > 2):
            raise ValueError('Only the documented near-surface current layer is accepted')
        times = tuple(_time(value) for value in raw['times'])
        if len(times) < 2 or any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError('Current valid times must increase')
        fields = {}
        for name in CURRENT_FIELDS:
            planes = tuple(raw['data'][name])
            if len(planes) != len(times):
                raise ValueError('Current time axis and samples disagree')
            # NetCDF depth has already been selected to one near-surface layer.
            fields[name] = tuple(_matrix(plane, len(latitude), len(longitude), name)
                                 for plane in planes)
        east, north = _local_axes(latitude, longitude)
        values = tuple(tuple(tuple(current_node(fields['uo'][k][j][i], fields['vo'][k][j][i])
                                   for i in range(len(east)))
                             for j in range(len(north))) for k in range(len(times)))
        return self._product(raw, 'current', east, north, times, values,
                             ('m/s', 'm/s'), 'ground-to-true-east-north')

    @staticmethod
    def _product(raw, name, east, north, times, values, units, reference_frame):
        if len(east) < 2 or len(north) < 2:
            raise ValueError('At least a 2×2 native grid is required')
        metadata = ProductMetadata(
            product=name, dataset_id=raw['dataset_id'], version=raw['version'],
            source=raw['source'], issued_at=raw.get('issued_at'),
            valid_from=times[0], valid_until=times[-1],
            coverage=Coverage(east[0], north[0], east[-1], north[-1], *VINGA_ORIGIN),
            units=units, reference_frame=reference_frame,
            retrieved_at=_time(raw['retrieved_at']), source_url=raw['source_url'],
            license_url=raw['license_url'], source_sha256=raw['source_sha256'])
        return GridProduct(metadata, east, north, times, values)
