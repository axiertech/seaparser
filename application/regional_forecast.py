"""Accept all three real products together, before the routing boundary."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from infrastructure.native_wind import NativeWindSample
from infrastructure.native_marine import NativeMarineDataset
from prototype.forecast import utc_time
from prototype.forecast_data import ForecastDataset


@dataclass(frozen=True)
class RegionalForecastInputs:
    wind: NativeWindSample
    marine: ForecastDataset | NativeMarineDataset
    # Source-read CF model reference, not catalogue version or issuance.
    marine_model_references: tuple[tuple[str, str | None], ...]
    marine_source_hashes: tuple[tuple[str, str], ...]


def inspect_regional_inputs(inputs, departure):
    departure = utc_time(departure, 'Regional departure')
    products = {product.metadata.product: product for product in inputs.marine.products}
    if set(products) != {'waves', 'current'}:
        raise ValueError('Both real marine products required')
    start = max(inputs.wind.times[0], *(product.metadata.valid_from for product in products.values()))
    end = min(inputs.wind.times[-1], *(product.metadata.valid_until for product in products.values()))
    blockers = list(inputs.wind.planning_blockers)
    blockers.append('current_native_wet_mask_unverified')
    for product in products.values():
        blockers.extend(product.metadata.planning_blockers)
    if not start <= departure < end:
        blockers.append('departure_outside_common_validity')
    # Equality of validity is useful for binding inputs, never proof of runs.
    identity = json.dumps(asdict(inputs), default=str, sort_keys=True, separators=(',', ':'))
    refs = dict(inputs.marine_model_references)
    return {
        'status': 'data_unavailable', 'fastest_candidate': None, 'comfortable_candidate': None,
        'input_sha256': sha256(identity.encode()).hexdigest(),
        'common_validity': {'from': start.isoformat() if start < end else None,
                            'until_exclusive': end.isoformat() if start < end else None,
                            'departure_supported': start <= departure < end},
        'wind': {'representation': 'native_source_grid_not_routing_grid',
                 'shape': [len(inputs.wind.times), len(inputs.wind.y_m), len(inputs.wind.x_m)],
                 'model_reference_time': inputs.wind.model_reference_time.isoformat(),
                 'issued_at': None, 'land_fraction_is_validity_mask': False,
                 'source_hashes': dict(inputs.wind.source_hashes)},
        'marine': {name: {'dataset_id': product.metadata.dataset_id,
                         'catalogue_version': product.metadata.version,
                         'source_sha256': product.metadata.source_sha256,
                         'model_reference_time': refs.get(name), 'issued_at': None,
                         'run_identity': None}
                   for name, product in products.items()},
        'marine_source_hashes': dict(inputs.marine_source_hashes),
        'cross_product_run_compatibility': 'unverified',
        'blockers': list(dict.fromkeys(blockers)),
        'navigational_safety': 'not_assessed', 'depth_status': 'unknown',
    }
