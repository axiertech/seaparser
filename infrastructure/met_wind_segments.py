"""Native MET wind sampling and conservative whole-segment model bounds.

This is an offline diagnostic adapter. It uses the MET sphere's declared LCC
coordinates and the Vinga WGS84-AEQD route frame; it does not qualify provider
mask, issue time, temporal averaging or compatibility with marine products.
"""
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from math import isfinite, radians, sin, cos

from pyproj import CRS, Geod, Transformer, network

from infrastructure.native_wind import NATIVE_PROJECTION, NativeWindSample
from infrastructure.native_wind_geometry import (
    Interval, cos_interval, enclose_source_box, pi_interval, sqrt_interval,
)
from prototype.forecast import utc_time
from prototype.model import Vector

network.set_network_enabled(False)
MET_CRS = CRS.from_proj4(NATIVE_PROJECTION)
MET_FORWARD = Transformer.from_crs(MET_CRS.geodetic_crs, MET_CRS, always_xy=True)
WGS84_GEOD = Geod(ellps='WGS84')
WGS84_A = Fraction(6378137)
WGS84_F = Fraction(10**9, 298257223563)
WGS84_E2 = WGS84_F * (2 - WGS84_F)
WGS84_MIN_MERIDIONAL_RADIUS = WGS84_A * (1 - WGS84_E2)
COORDINATE_TOLERANCE_M = Fraction(1)


class WindDataUnavailable(ValueError):
    pass


def _axis_cell(axis, value, name):
    if not isfinite(value) or value < axis[0] or value > axis[-1]:
        raise WindDataUnavailable(f'{name} outside native support')
    i = min(bisect_right(axis, value) - 1, len(axis) - 2)
    width = float(axis[i + 1] - axis[i])
    return i, (value - float(axis[i])) / width


def _time_cell(axis, value):
    seconds = value.timestamp()
    return _axis_cell(tuple(t.timestamp() for t in axis), seconds, 'time')


def _closed_cells(axis, low, high):
    if low > high or len(axis) < 2:
        raise WindDataUnavailable('Invalid native-grid interval')
    return tuple(i for i in range(len(axis) - 1)
                 if axis[i] <= high and axis[i + 1] >= low)


def direction_from_to_components(speed_m_s, from_degrees):
    """MET's FROM bearing (north=0°, east=90°) to true east/north TO vector."""
    if not (isfinite(speed_m_s) and speed_m_s >= 0
            and isfinite(from_degrees) and 0 <= from_degrees <= 360):
        raise WindDataUnavailable('Invalid native wind value')
    angle = radians(from_degrees)
    return Vector(-speed_m_s * sin(angle), -speed_m_s * cos(angle))


def _lerp(a, b, f):
    return a + (b - a) * f


def _bound_text(value):
    """Preserve the geometry module's outward 1e-30 m rational bounds."""
    with localcontext() as context:
        context.prec = 60
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f')


@dataclass(frozen=True)
class VingaRouteSegment:
    """One affine segment in the WGS84 AEQD frame centered at Vinga."""
    start: Vector
    end: Vector
    start_time: datetime
    end_time: datetime

    def __post_init__(self):
        start, end = (utc_time(t, 'Route segment time') for t in
                      (self.start_time, self.end_time))
        if start >= end:
            raise ValueError('Positive segment duration required')
        object.__setattr__(self, 'start_time', start)
        object.__setattr__(self, 'end_time', end)


class NativeMetWind:
    """Read-only interpolation over one hash-frozen MET native-grid sample."""
    def __init__(self, sample: NativeWindSample):
        if sample.projection != NATIVE_PROJECTION:
            raise WindDataUnavailable('Unreviewed MET projection')
        if min(len(sample.x_m), len(sample.y_m), len(sample.times)) < 2:
            raise WindDataUnavailable('Insufficient native grid dimensions')
        self.sample = sample

    def _xy(self, longitude, latitude):
        if not (isfinite(longitude) and isfinite(latitude)
                and 5 <= longitude <= 25 and 50 <= latitude <= 70):
            raise WindDataUnavailable('Point outside reviewed MET region')
        return MET_FORWARD.transform(longitude, latitude, errcheck=True)

    def at(self, longitude, latitude, when):
        """Interpolate E/N components bilinearly in space, linearly in time."""
        when = utc_time(when, 'Wind query time')
        x, y = self._xy(longitude, latitude)
        i, fx = _axis_cell(self.sample.x_m, x, 'x')
        j, fy = _axis_cell(self.sample.y_m, y, 'y')
        k, ft = _time_cell(self.sample.times, when)
        planes = []
        for tk in (k, k + 1):
            rows = []
            for yj in (j, j + 1):
                values = []
                for xi in (i, i + 1):
                    speed = self.sample.speed_m_s[tk][yj][xi]
                    direction = self.sample.direction_from_degrees[tk][yj][xi]
                    if not (isinstance(speed, Decimal) and speed.is_finite()
                            and isinstance(direction, Decimal) and direction.is_finite()):
                        raise WindDataUnavailable('Missing native interpolation node')
                    values.append(direction_from_to_components(float(speed), float(direction)))
                rows.append(Vector(_lerp(values[0].east, values[1].east, fx),
                                   _lerp(values[0].north, values[1].north, fx)))
            planes.append(Vector(_lerp(rows[0].east, rows[1].east, fy),
                                 _lerp(rows[0].north, rows[1].north, fy)))
        result = Vector(_lerp(planes[0].east, planes[1].east, ft),
                        _lerp(planes[0].north, planes[1].north, ft))
        if not (isfinite(result.east) and isfinite(result.north)):
            raise WindDataUnavailable('Non-finite interpolated wind')
        return result

    def at_vinga_local(self, position, when):
        """Return the sampled true E/N wind in Vinga AEQD coordinate rates.

        The local differential is computed from symmetric 10 m geodesic
        displacements and the checked-in WGS84 AEQD transform. The one-metre
        source-grid alignment tolerance is separately included in segment
        support; this Jacobian is for vessel-motion integration only.
        """
        from infrastructure.land import FORWARD, to_geo
        longitude, latitude = to_geo(position)
        true_wind = self.at(longitude, latitude, when)
        h = 10.0

        def differential(azimuth):
            lon_p, lat_p, _ = WGS84_GEOD.fwd(longitude, latitude, azimuth, h)
            lon_m, lat_m, _ = WGS84_GEOD.fwd(longitude, latitude, (azimuth + 180) % 360, h)
            x_p, y_p = FORWARD.transform(lon_p, lat_p, errcheck=True)
            x_m, y_m = FORWARD.transform(lon_m, lat_m, errcheck=True)
            return Vector((x_p - x_m) / (2 * h), (y_p - y_m) / (2 * h))

        east_column, north_column = differential(90), differential(0)
        return Vector(east_column.east * true_wind.east + north_column.east * true_wind.north,
                      east_column.north * true_wind.east + north_column.north * true_wind.north)

    def bound_segment(self, segment: VingaRouteSegment, *, max_wind_m_s):
        """Check data support and conservatively bound all trilinear cell values.

        The entire affine local segment is inside the Vinga-centered AEQD disk
        whose radius is the larger endpoint radius. WGS84 ellipsoid metric lower
        bounds enclose that disk in geographic coordinates. Exact interval LCC
        arithmetic then encloses all touched native cells. Norm convexity bounds
        trilinear E/N wind by the greatest raw corner speed. One metre is added
        for the documented source-coordinate alignment tolerance.
        """
        if (isinstance(max_wind_m_s, bool) or not isinstance(max_wind_m_s, (int, float))
                or not isfinite(max_wind_m_s) or max_wind_m_s < 0):
            raise ValueError('Finite nonnegative wind limit required')
        radius_sq = max(
            Fraction.from_float(p.east) ** 2 + Fraction.from_float(p.north) ** 2
            for p in (segment.start, segment.end))
        radius = sqrt_interval(Interval.point(radius_sq)).high
        if radius > 1500:
            raise WindDataUnavailable('Segment outside Vinga route frame')
        pi = pi_interval()
        lat0, lon0 = Fraction('57.633'), Fraction('11.605')
        dlat = radius / WGS84_MIN_MERIDIONAL_RADIUS * 180 / pi.low
        latitude = Interval(lat0 - dlat, lat0 + dlat)
        max_abs_lat = max(abs(latitude.low), abs(latitude.high)) * pi.high / 180
        min_cos = cos_interval(Interval(-max_abs_lat, max_abs_lat)).low
        if min_cos <= 0:
            raise WindDataUnavailable('Geographic enclosure reaches a pole')
        dlon = radius / (WGS84_A * min_cos) * 180 / pi.low
        longitude = Interval(lon0 - dlon, lon0 + dlon)
        x, y = enclose_source_box((latitude.low, latitude.high),
                                  (longitude.low, longitude.high), self.sample.projection)
        x = Interval(x.low - COORDINATE_TOLERANCE_M, x.high + COORDINATE_TOLERANCE_M)
        y = Interval(y.low - COORDINATE_TOLERANCE_M, y.high + COORDINATE_TOLERANCE_M)
        east = _closed_cells(self.sample.x_m, x.low, x.high)
        north = _closed_cells(self.sample.y_m, y.low, y.high)
        times = _closed_cells(self.sample.times, segment.start_time, segment.end_time)
        inside = (self.sample.x_m[0] <= x.low <= x.high <= self.sample.x_m[-1]
                  and self.sample.y_m[0] <= y.low <= y.high <= self.sample.y_m[-1]
                  and self.sample.times[0] <= segment.start_time
                  and segment.end_time <= self.sample.times[-1])
        if not inside or not east or not north or not times:
            return {'status': 'insufficient_evidence', 'reason': 'outside_frozen_grid',
                    'provider_mask': 'unknown', 'wind_limit_m_s': max_wind_m_s}
        cells = [(k, j, i) for k in times for j in north for i in east]
        node_ids = {(k + dt, j + dy, i + dx) for k, j, i in cells
                    for dt in (0, 1) for dy in (0, 1) for dx in (0, 1)}
        speeds = []
        for k, j, i in node_ids:
            speed, direction = (self.sample.speed_m_s[k][j][i],
                                self.sample.direction_from_degrees[k][j][i])
            if not (isinstance(speed, Decimal) and speed.is_finite() and speed >= 0
                    and isinstance(direction, Decimal) and direction.is_finite()
                    and 0 <= direction <= 360):
                return {'status': 'insufficient_evidence', 'reason': 'missing_native_node',
                        'provider_mask': 'unknown', 'wind_limit_m_s': max_wind_m_s}
            speeds.append(speed)
        upper_decimal = max(speeds)
        limit_decimal = Decimal(str(max_wind_m_s))
        # A point on the segment above the limit proves an exceedance. Sampling
        # points alone never proves the within-limit state.
        from infrastructure.land import to_geo
        observed = False
        for f in (0.0, 0.5, 1.0):
            point = Vector(_lerp(segment.start.east, segment.end.east, f),
                           _lerp(segment.start.north, segment.end.north, f))
            longitude_q, latitude_q = to_geo(point)
            when = segment.start_time + (segment.end_time-segment.start_time)*f
            if self.at(longitude_q, latitude_q, when).speed > max_wind_m_s + 1e-9:
                observed = True
                break
        if observed:
            status, reason = 'observed_exceedance', 'on-segment query exceeds limit'
        elif upper_decimal <= limit_decimal:
            status, reason = 'within_interpolation_model', None
        else:
            status, reason = 'insufficient_evidence', 'conservative bound crosses limit'
        return {
            'status': status, 'reason': reason, 'upper_bound_m_s': str(upper_decimal),
            'wind_limit_m_s': max_wind_m_s, 'intersecting_cells': len(cells),
            'source_nodes': len(node_ids),
            'source_grid_enclosure_m': {'x': [_bound_text(x.low), _bound_text(x.high)],
                                        'y': [_bound_text(y.low), _bound_text(y.high)]},
            'provider_mask': 'unknown', 'provider_averaging_window': 'unverified',
            'coordinate_mapping_tolerance_m': float(COORDINATE_TOLERANCE_M),
            'overall_planning_qualification': 'blocked',
            'remaining_gates': ['wind_validity_mask_unverified',
                                'wind_mean_window_unverified', 'model_issue_time_unverified',
                                'cross_product_model_run_compatibility_unverified'],
        }
