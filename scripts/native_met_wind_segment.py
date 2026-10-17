"""Reproduce actual frozen MET wind support/bounds on one Vinga route segment."""
from dataclasses import asdict
from datetime import datetime
import argparse
import json
from pathlib import Path

from infrastructure.met_wind_segments import NativeMetWind, VingaRouteSegment
from prototype.model import Vector
from scripts.regional_forecast import load_native_wind


def reproduce(fixtures):
    root = Path(fixtures)
    case = json.loads((root / 'vinga-met-wind-segment.json').read_text())
    sample = load_native_wind(root)
    source_manifest = json.loads((root / 'met-nordic-wind-sample' / 'manifest.json').read_text())
    segment = VingaRouteSegment(
        Vector(*case['start_local_east_north_m']),
        Vector(*case['end_local_east_north_m']),
        datetime.fromisoformat(case['start_time'].replace('Z', '+00:00')),
        datetime.fromisoformat(case['end_time'].replace('Z', '+00:00')))
    wind = NativeMetWind(sample)
    from infrastructure.land import to_geo
    observations = []
    for fraction in (0.0, 0.5, 1.0):
        point = Vector(segment.start.east + (segment.end.east-segment.start.east)*fraction,
                       segment.start.north + (segment.end.north-segment.start.north)*fraction)
        lon, lat = to_geo(point)
        time = segment.start_time + (segment.end_time-segment.start_time)*fraction
        vector = wind.at(lon, lat, time)
        route_vector = wind.at_vinga_local(point, time)
        observations.append({'fraction': fraction, 'longitude': lon, 'latitude': lat,
                             'time': time.isoformat(), 'wind_east_m_s': vector.east,
                             'wind_north_m_s': vector.north, 'wind_speed_m_s': vector.speed,
                             'route_east_m_s': route_vector.east,
                             'route_north_m_s': route_vector.north})
    return {
        'schema': 1, 'status': 'diagnostic_only',
        'dataset': 'MET Nordic native frozen wind; no live fetch',
        'source_hashes': dict(sample.source_hashes),
        'retrieved_at': source_manifest['observed_at'],
        'source_url': source_manifest['url'].split('?')[0],
        'model_reference_time': sample.model_reference_time.isoformat(), 'issued_at': None,
        'validity': [sample.times[0].isoformat(), sample.times[-1].isoformat()],
        'segment': {'start_east_north_m': asdict(segment)['start'],
                    'end_east_north_m': asdict(segment)['end'],
                    'start_time': segment.start_time.isoformat(),
                    'end_time': segment.end_time.isoformat()},
        'interpolation': 'bilinear native LCC E/N components, then linear time components',
        'wind_observations': observations,
        'hard_wind_checks': {
            str(limit): wind.bound_segment(segment, max_wind_m_s=limit)
            for limit in case['test_wind_limits_m_s']},
        'provider_wind_mask': 'unknown', 'wind_average_window_placement': 'unverified',
        'coordinate_mapping': {
            'operation': 'preserve geographic lon/lat values into the MET CF geographic CRS, '
                         'then apply its declared spherical LCC; no datum shift is implied',
            'alignment_check_nodes': 56,
            'observed_max_alignment_error_m': 0.24907657108681355,
            'applied_support_margin_m': 1.0,
            'global_datum_accuracy': 'not established'},
        'marine_run_compatibility': 'unverified', 'depth': 'unknown',
        'land_completeness': 'unknown', 'navigational_safety': 'not_assessed',
        'synthetic_components': {'current': 'not used', 'waves': 'not used',
                                 'boat_polar': 'not used'},
        'limitations': ['one diagnostic segment, not full route comparison',
                         'a within-interpolation-model bound is not source-quality qualification',
                         'overall planning remains blocked by missing mask, averaging placement, '
                         'issued_at and marine run compatibility'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'fixtures')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = reproduce(args.fixtures)
    rendered = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
