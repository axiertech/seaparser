"""Load frozen MET wind and Copernicus marine bytes into regional inputs offline."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

from application.regional_forecast import RegionalForecastInputs, inspect_regional_inputs
from infrastructure.copernicus_adapter import CopernicusMarineAdapter
from infrastructure.native_wind import NativeWindSample
from scripts.audit_met_metadata import PROJ4, audit_coordinate_extents, read_wind_sample
from scripts.freeze_copernicus_reference import freeze_with_audit


def load_native_wind(root):
    """Reuse the existing snapshot reader without loading unrelated marine data."""
    root = Path(root)
    metadata_dir, wind_dir = (root / name for name in
        ('met-nordic-metadata', 'met-nordic-wind-sample'))
    return native_wind_from_snapshot(read_wind_sample(wind_dir, metadata_dir))


def native_wind_from_snapshot(snapshot):
    """Materialize the exact already validated snapshot; never reopen source files."""
    metadata, digest, axes, epochs, values = snapshot
    rows,columns,count=len(axes['y']),len(axes['x']),len(epochs)
    def planes(flat):
        return tuple(tuple(tuple(flat[(k*rows+j)*columns:(k*rows+j+1)*columns])
                           for j in range(rows)) for k in range(count))
    def instant(epoch):
        return datetime.fromtimestamp(int(Decimal(epoch)), timezone.utc)
    hashes = dict(metadata['source_hashes'], **{'native-wind-land.txt': digest})
    return NativeWindSample(
        PROJ4, axes['x'], axes['y'], tuple(instant(epoch) for epoch in epochs),
        planes(values['wind_speed_10m']), planes(values['wind_direction_10m']),
        tuple(tuple(values['land_area_fraction'][j * columns:(j + 1) * columns]) for j in range(rows)),
        instant(metadata['model_reference']['epoch_seconds']), tuple(sorted(hashes.items())))


def load_regional_inputs(root):
    root = Path(root)
    metadata_dir, wind_dir, marine_dir = (root / name for name in
        ('met-nordic-metadata', 'met-nordic-wind-sample', 'vinga-copernicus'))
    # Preserve diagnostic snapshot ordering before the actual materialization.
    audit_coordinate_extents(metadata_dir, wind_dir, marine_dir)
    wind = load_native_wind(root)
    marine_payload, marine_audit = freeze_with_audit(marine_dir)
    marine = CopernicusMarineAdapter().normalize(marine_payload)
    return RegionalForecastInputs(wind, marine, tuple(
        (name, marine_audit[name]['forecast_reference_time']) for name in ('waves', 'current')),
        tuple(sorted(marine_audit['manifest_file_hashes'].items())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).resolve().parents[1] / 'fixtures')
    parser.add_argument('--departure', required=True, help='Aware UTC ISO departure')
    args = parser.parse_args()
    inputs = load_regional_inputs(args.fixtures)
    departure = datetime.fromisoformat(args.departure.replace('Z', '+00:00'))
    print(json.dumps(inspect_regional_inputs(inputs, departure), sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(f'REGIONAL_INPUTS_UNAVAILABLE {type(error).__name__}', file=sys.stderr)
        sys.exit(1)


def load_expanded_native_inputs(root, *, radius_m):
    """Same adapter and detached field reader for the explicit larger fixture."""
    from scripts.freeze_copernicus_reference import freeze_native_with_audit
    from scripts.audit_met_metadata import read_wind_sample
    root=Path(root)
    payload,report=freeze_native_with_audit(root,radius_m=radius_m)
    expected=Decimal(int(datetime.fromisoformat(report['wind']['model_reference_time']).timestamp()))
    wind=native_wind_from_snapshot(read_wind_sample(root/'met-nordic-wind-sample',root/'met-nordic-metadata',expected_reference=expected))
    marine=CopernicusMarineAdapter().normalize(payload,native_radius_m=radius_m)
    hashes=tuple((name,report['source_hashes'][name]) for name in ('waves.nc','current.nc','wave-mask.nc'))
    return RegionalForecastInputs(wind,marine,(('waves',None),('current',None)),hashes)
