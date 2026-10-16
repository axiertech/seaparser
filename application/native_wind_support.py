"""Bind a source-sphere segment's whole mathematical enclosure to frozen raw nodes.

This inventory is never an interpolation, valid-mask proof or routing approval.
A local/WGS84 route cannot be relabelled as a segment on the source sphere.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json

from infrastructure.native_wind_geometry import (
    LOCAL_METHOD, METHOD, SOURCE_LOCAL_DEFINITION, SOURCE_LOCAL_FRAME,
    SOURCE_LOCAL_MAX_RADIUS_M, enclose_source_box, enclose_source_local_segment,
)
from prototype.forecast import utc_time

SOURCE_FRAME = 'met-source-sphere-angular-linear-v1'
MAX_CELLS = 512


@dataclass(frozen=True)
class SourceSphereSegment:
    start_latitude: Decimal
    start_longitude: Decimal
    end_latitude: Decimal
    end_longitude: Decimal
    start_time: datetime
    end_time: datetime
    coordinate_frame: str


def closed_cell_indices(axis, low, high):
    """Every CLOSED adjacent-node interval touching the closed query interval."""
    if low > high or len(axis) < 2 or any(a >= b for a,b in zip(axis,axis[1:])):
        raise ValueError('Ordered interval and strictly increasing source axis required')
    return tuple(i for i in range(len(axis)-1) if axis[i] <= high and axis[i+1] >= low)


def _decimal(value):
    with localcontext() as ctx:
        ctx.prec = 80
        return format(Decimal(value.numerator)/Decimal(value.denominator), 'f')


def _fingerprint(value):
    return sha256(json.dumps(value,default=str,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _coordinate(value):
    if isinstance(value,bool) or not isinstance(value,(int,Decimal,Fraction)):
        raise ValueError('Exact decimal/rational source-sphere coordinates required')
    return Fraction(value)


def inspect_native_segment(wind, segment, *, max_cells=MAX_CELLS):
    """Inventory all adjacent source boxes intersecting an enclosing space/time box.

    The entire angular-linear segment lies in its geographic endpoint rectangle;
    nonlinear projection of the WHOLE rectangle is interval-enclosed. This does
    not assert equivalence to the motor's locally affine trajectory, the source's
    original binary axes, or the provider's unknown interpolation stencil.
    """
    if segment.coordinate_frame != SOURCE_FRAME:
        raise ValueError('Source-sphere path required; local/WGS84 route binding is unverified')
    if type(max_cells) is not int or not 1 <= max_cells <= MAX_CELLS:
        raise ValueError('Invalid source-cell budget')
    start_time, end_time = (utc_time(t,'Native segment time') for t in
                            (segment.start_time,segment.end_time))
    if start_time >= end_time:
        raise ValueError('Positive segment duration required')
    latitudes = sorted((_coordinate(segment.start_latitude),_coordinate(segment.end_latitude)))
    longitudes = sorted((_coordinate(segment.start_longitude),_coordinate(segment.end_longitude)))
    x,y = enclose_source_box(latitudes,longitudes,wind.projection)
    record=dict(
        {name:str(_coordinate(getattr(segment,name))) for name in
         ('start_latitude','start_longitude','end_latitude','end_longitude')},
        start_time=start_time.isoformat(),end_time=end_time.isoformat(),coordinate_frame=SOURCE_FRAME)
    return _inspect_enclosure(wind,record,start_time,end_time,x,y,max_cells)


def _inspect_enclosure(wind,segment_record,start_time,end_time,x,y,max_cells, *,
                       method=METHOD,local_geometry=None):
    nx,ny,nt = len(wind.x_m),len(wind.y_m),len(wind.times)
    if nx*ny*nt > 4096 or min(nx,ny,nt) < 2:
        raise ValueError('Unsupported raw source dimensions')
    for data in (wind.speed_m_s,wind.direction_from_degrees):
        if len(data)!=nt or any(len(plane)!=ny or any(len(row)!=nx for row in plane) for plane in data):
            raise ValueError('Raw source shape differs from native axes')
    if len(wind.land_fraction)!=ny or any(len(row)!=nx for row in wind.land_fraction):
        raise ValueError('Land fraction shape differs from native axes')
    east = closed_cell_indices(wind.x_m,x.low,x.high)
    north = closed_cell_indices(wind.y_m,y.low,y.high)
    times = closed_cell_indices(wind.times,start_time,end_time)
    spatial_inside = (wind.x_m[0] <= x.low <= x.high <= wind.x_m[-1]
                      and wind.y_m[0] <= y.low <= y.high <= wind.y_m[-1])
    time_inside = wind.times[0] <= start_time < end_time <= wind.times[-1]
    count = len(east)*len(north)*len(times)
    reasons=[]
    if not spatial_inside:
        reasons.append('projected_box_outside_serialized_native_grid')
    if not time_inside:
        reasons.append('segment_outside_nominal_time_support')
    if count > max_cells:
        reasons.append('source_cell_budget_exceeded')
    cells, nodes = [], []
    # No partial success, clipped geometry, or truncated lists on any failure.
    if not reasons:
        cells = [(k,j,i) for k in times for j in north for i in east]
        node_indices = sorted({(k+dt,j+dy,i+dx) for k,j,i in cells
                               for dt in (0,1) for dy in (0,1) for dx in (0,1)})
        for k,j,i in node_indices:
            speed,direction = wind.speed_m_s[k][j][i],wind.direction_from_degrees[k][j][i]
            valid_speed = isinstance(speed,Decimal) and speed.is_finite() and speed >= 0
            valid_direction = (isinstance(direction,Decimal) and direction.is_finite()
                               and 0 <= direction <= 360)
            complete = valid_speed and valid_direction
            if not complete:
                reasons.append('missing_or_nonfinite_raw_node')
            nodes.append({'index':[k,j,i], 'x_m':str(wind.x_m[i]),'y_m':str(wind.y_m[j]),
                          'valid_at':wind.times[k].isoformat(),
                          'speed_m_s':str(speed) if valid_speed else None,
                          'direction_from_degrees':str(direction) if valid_direction else None,
                          'land_fraction':str(wind.land_fraction[j][i])})
    report = {
        'schema':1, 'method':method, 'scope':'source_sphere_serialized_grid_inventory_only',
        'segment':segment_record,
        'segment_coordinate_encoding':('exact rational metres' if local_geometry else 'exact rational degrees'),
        'source_projection':wind.projection,
        'source_hashes':dict(wind.source_hashes), 'source_input_sha256':_fingerprint(asdict(wind)),
        'projected_enclosure_m':{'x':[_decimal(x.low),_decimal(x.high)],
                                 'y':[_decimal(y.low),_decimal(y.high)]},
        'numeric_method':'exact rational interval operations; outward quantum 1e-30; bounded series tails',
        'arithmetic_error_included_in_enclosure':True,
        'physical_source_support_qualified':False,
        'source_coordinate_serialization_error_m':None, 'source_to_wgs84_datum_error_m':None,
        'local_route_geometry_binding_verified':False,
        'serialized_spatial_box_inside':spatial_inside, 'nominal_time_box_inside':time_inside,
        'arrival_before_last_sample':end_time < wind.times[-1],
        'intersecting_box_count':count, 'max_cells':max_cells,
        'adjacent_node_boxes':[list(c) for c in cells], 'raw_nodes':nodes,
        'raw_inventory_complete':not reasons, 'inventory_failures':sorted(set(reasons)),
        'provider_wind_validity_mask':None, 'land_fraction_is_validity_mask':False,
        'provider_interpolation_stencil_verified':False, 'mean_window_placement':None,
        'wind_vector_frame_qualified':False, 'wind_safety_envelope':None,
        'routing_status':'data_unavailable', 'fastest_candidate':None,'comfortable_candidate':None,
        'planning_blockers':list(wind.planning_blockers) + [
            'wind_source_serialization_error_unverified','wind_route_datum_binding_unverified',
            'wind_validity_mask_unverified','wind_interpolation_rule_unverified',
            'wind_mean_window_unverified','wind_safety_envelope_unverified'],
    }
    if local_geometry is not None:
        report['source_local_geometry']=local_geometry
    report['report_sha256']=_fingerprint(report)
    return report


@dataclass(frozen=True)
class SourceLocalSegment:
    start_east_m: Decimal
    start_north_m: Decimal
    end_east_m: Decimal
    end_north_m: Decimal
    start_time: datetime
    end_time: datetime
    coordinate_frame: str


def inspect_source_local_segment(wind,segment, *, max_cells=MAX_CELLS):
    """Bind a locally affine SOURCE-SPHERE path; never accept a WGS84 frame flag."""
    if segment.coordinate_frame != SOURCE_LOCAL_FRAME:
        raise ValueError('Explicit source-sphere AEQD frame required; WGS84 binding remains unverified')
    if type(max_cells) is not int or not 1 <= max_cells <= MAX_CELLS:
        raise ValueError('Invalid source-cell budget')
    start_time,end_time=(utc_time(t,'Source-local segment time') for t in
                         (segment.start_time,segment.end_time))
    if start_time >= end_time:
        raise ValueError('Positive segment duration required')
    coordinates={name:_coordinate(getattr(segment,name)) for name in
                 ('start_east_m','start_north_m','end_east_m','end_north_m')}
    x,y,lat,lon,radius,radius_squared=enclose_source_local_segment(
        (coordinates['start_east_m'],coordinates['start_north_m']),
        (coordinates['end_east_m'],coordinates['end_north_m']),wind.projection)
    record=dict({name:str(value) for name,value in coordinates.items()},
                start_time=start_time.isoformat(),end_time=end_time.isoformat(),
                coordinate_frame=SOURCE_LOCAL_FRAME)
    geometry={
        'local_definition':SOURCE_LOCAL_DEFINITION,
        'path_model':'affine in source-sphere AEQD east/north metres and time',
        'local_to_source_sphere_enclosure_verified':True,
        'wgs84_route_binding_verified':False,
        'projection_enclosure_method':METHOD,
        'radius_limit_m':SOURCE_LOCAL_MAX_RADIUS_M,
        'maximum_endpoint_radius_squared_m2':str(radius_squared),
        'origin_disk_radius_m':[_decimal(radius.low),_decimal(radius.high)],
        'latitude_degrees':[_decimal(lat.low),_decimal(lat.high)],
        'longitude_degrees':[_decimal(lon.low),_decimal(lon.high)],
        'scope':'mathematical source-sphere frame only; no datum/serialization error assumed',
    }
    return _inspect_enclosure(wind,record,start_time,end_time,x,y,max_cells,
                              method=LOCAL_METHOD,local_geometry=geometry)
