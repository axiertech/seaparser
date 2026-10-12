"""Versioned estimated fixture for offline acceptance scenarios, no real provider."""
from datetime import datetime, timedelta, timezone

from .forecast_adapter import SyntheticFixtureAdapter

PLAN = datetime(2026, 1, 1, tzinfo=timezone.utc)
START = PLAN + timedelta(hours=2)


def synthetic_snapshot(scenario='baseline'):
    if scenario not in ('baseline', 'weather-limit', 'unverified', 'missing-waves'):
        raise ValueError('Okänt syntetiskt scenario')
    version = '1' if scenario == 'baseline' else '1-'+scenario
    east = [-50, 0, 20, 80, 100, 150]
    north = [-50, 0, 20, 50]
    times = [START, START+timedelta(seconds=300), START+timedelta(seconds=600),
             START+timedelta(seconds=1800)]
    products = []
    for name in ('wind', 'current', 'waves'):
        def node(index, y):
            if name == 'wind':
                return [4, 0]
            if name == 'current':
                return [0 if index < 2 else .2, 90]
            if scenario == 'weather-limit':
                return [1.2, 5, 0]
            if scenario == 'unverified':
                return [.4 if y <= 0 else 1.1, 5, 0]
            if scenario == 'missing-waves':
                return None
            return [1 if y <= 0 else 1/3, 5, 0]
        products.append({
            'product': name, 'dataset_id': 'estimated-demo-'+name, 'version': version,
            'source': 'SeaParser handvalda uppskattade syntetiska testdata',
            'issued_at': PLAN-timedelta(seconds=100), 'valid_from': START, 'valid_until': times[-1],
            'coverage': {'min_east_m': -50, 'min_north_m': -50, 'max_east_m': 150,
                         'max_north_m': 50, 'origin_latitude': 58, 'origin_longitude': 11},
            'east_m': east, 'north_m': north, 'times': times,
            'units': ['m', 's', 'deg'] if name == 'waves' else ['m/s', 'deg'],
            'reference_frame': 'ground-from-true-north-tm02' if name == 'waves' else (
                'ground-from-true-north' if name == 'wind' else 'ground-to-true-north'),
            'values': [[[node(k, y) for x in east] for y in north] for k in range(len(times))]})
    return SyntheticFixtureAdapter().normalize({
        'dataset_id': 'seaparser-estimated-planning-demo', 'version': version, 'products': products})
