"""Explicit development-only assumptions around otherwise unchanged real inputs."""
from dataclasses import asdict, replace
from datetime import datetime
import json
from pathlib import Path
from functools import lru_cache

from infrastructure.development_forecast import DevelopmentForecast,ProjectedDevelopmentForecast
from prototype.forecast_metadata import ProductMetadata, Coverage
from prototype.forecast import utc_time
from scripts.regional_forecast import load_regional_inputs,load_expanded_native_inputs
from application.planning import canonical, digest

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=frozenset(('model_issue_time_unverified','cross_product_model_run_compatibility_unverified',
    'current_native_wet_mask_unverified','wind_native_geometry_unqualified','wind_vector_frame_unqualified',
    'wind_validity_mask_unverified','wind_mean_window_unverified','marine_time_support_unverified'))


@lru_cache(maxsize=2)
def _inputs(root, source_bundle=None, radius_m=None):
    if source_bundle is None:return load_regional_inputs(root)
    if source_bundle!='vinga-expanded-20261017':raise ValueError('Okänd fryst utvecklingsbunt')
    return load_expanded_native_inputs(root/source_bundle,radius_m=radius_m)


def load_development_weather(config_path=None, fixtures=None):
    config=json.loads((config_path or ROOT/'settings/development-weather-assumptions.json').read_text())
    if config.get('mode') != 'development_assumptions' or set(config['assumptions']) != REQUIRED:
        raise ValueError('Alla specifika utvecklingsantaganden måste vara explicit konfigurerade')
    if any(not isinstance(v,str) or not v.strip() for v in config['assumptions'].values()):
        raise ValueError('Antaganden kräver en förklaring')
    root=fixtures or ROOT/'fixtures'
    inputs=_inputs(root,config['source_bundle'],config['support_radius_m']) if config.get('source_bundle') is not None else _inputs(root)
    if not set(inputs.wind.planning_blockers) <= REQUIRED:
        raise ValueError('Nytt vindproblem kräver ett specifikt antagande')
    assumptions=tuple(sorted(config['assumptions'].items()))
    issued=utc_time(datetime.fromisoformat(config['assumed_issued_at'].replace('Z','+00:00')),'Antagen utfärdandetid')
    products=[]
    source_metadata=[]
    for product in inputs.marine.products:
        source_metadata.append(asdict(product.metadata))
        if not set(product.metadata.planning_blockers) <= REQUIRED:
            raise ValueError('Nytt källproblem kräver ett specifikt antagande; inga generella undantag')
        products.append(replace(product,metadata=replace(product.metadata,issued_at=issued,planning_blockers=(),assumed_fields=('issued_at',*sorted(REQUIRED)))))
    marine=replace(inputs.marine,products=tuple(products))
    radius=config['support_radius_m']
    wm=ProductMetadata('wind','MET-native-frozen',inputs.wind.model_reference_time.strftime('%Y%m%d'),'MET Nordic frysta verkliga vindnoder',issued,
        inputs.wind.times[0],inputs.wind.times[-1],Coverage(-radius,-radius,radius,radius,57.633,11.605),
        ('m/s','m/s'),'ground-to-true-east-north',source_sha256=dict(inputs.wind.source_hashes)['native-wind-land.txt'],assumed_fields=('issued_at',*sorted(REQUIRED)))
    frame=config.get('motion_frame')
    if frame not in (None,'wgs84-aeqd-proj-differential-v1'):
        raise ValueError('Unknown motion frame')
    forecast=ProjectedDevelopmentForecast if frame is not None else DevelopmentForecast
    dataset=forecast('seaparser-real-meteo-marine','development-'+digest(config)[:16],
        inputs.wind,marine,wm,assumptions,radius)
    evidence={'mode':'development_assumptions','source_qualification':'unverified',
        'verified':{'wind_model_reference_time':inputs.wind.model_reference_time.isoformat(),
                    'wind_source_hashes':dict(inputs.wind.source_hashes),
                    'marine_source_hashes':dict(inputs.marine_source_hashes),
                    'marine_metadata':source_metadata},
        'assumptions':dict(assumptions),'assumed_issued_at':issued.isoformat(),
        'configuration_sha256':digest(config),
        'historical_snapshot':True,'actual_source_issued_at':{'wind':None,'current':None,'waves':None}}
    if frame is not None:evidence['motion_frame']=frame
    return dataset,config,json.loads(canonical(evidence))
