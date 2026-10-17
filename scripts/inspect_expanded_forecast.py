"""Reproducible offline inspection of the larger frozen source bundle.

Uses existing MET materialization/interpolation and native marine surveys;
never constructs another routing adapter or clears planning/source gates.
"""
import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from scripts.copernicus_budget import digest
from scripts.manifest_json import manifest_json
from scripts.audit_met_metadata import read_wind_sample
from scripts.regional_forecast import native_wind_from_snapshot
from scripts.survey_marine_support import survey
from infrastructure.met_wind_segments import NativeMetWind

ROOT=Path(__file__).resolve().parents[1]


def inspect(root):
    root=Path(root).resolve()
    with (root/'manifest.json').open('rb') as stream:data=stream.read(512001)
    if len(data)>512000:raise ValueError('Frozen manifest budget exceeded')
    manifest=manifest_json(data)
    files=manifest['files']
    if manifest.get('schema')!=1 or not 1<=len(files)<=32 or len({e['path'] for e in files})!=len(files):
        raise ValueError('Bounded unique frozen-bundle manifest required')
    hashes={}
    for entry in files:
        path=root/entry['path']
        if (not path.resolve().is_relative_to(root) or path.is_symlink() or entry['bytes']>10_000_000
                or path.stat().st_size!=entry['bytes'] or digest(path)!=entry['sha256']):
            raise ValueError('Frozen expanded source hash/size/path mismatch')
        hashes[entry['path']]=entry['sha256']
    waves=survey(root/'waves.nc','waves',root/'wave-mask.nc')
    current=survey(root/'current.nc','current')
    for name,report in (('waves',waves),('current',current)):
        if report['source_sha256']!=hashes[name+'.nc']:raise ValueError('Captured marine source differs from bundle')
    if waves['wave_mask_sha256']!=hashes['wave-mask.nc']:raise ValueError('Captured mask differs from bundle')
    reference=datetime.fromisoformat(manifest['expected_wind_reference'].replace('Z','+00:00'))
    if reference.tzinfo is None:raise ValueError('Explicit aware model reference required')
    snapshot=read_wind_sample(root/'met-nordic-wind-sample',root/'met-nordic-metadata',
                              expected_reference=Decimal(int(reference.timestamp())))
    wind=native_wind_from_snapshot(snapshot)
    for name,sha in wind.source_hashes:
        directory='met-nordic-wind-sample' if name=='native-wind-land.txt' else 'met-nordic-metadata'
        if hashes[directory+'/'+name]!=sha:raise ValueError('Captured wind source differs from bundle')
    native=NativeMetWind(wind);point_count=0
    for marine in (waves,current):
        for lat in marine['latitude']:
            for lon in marine['longitude']:
                for when in wind.times[:-1]:
                    native.at(lon,lat,when);point_count+=1
    labels=[(wind.times[0].isoformat(),wind.times[-1].isoformat()),
            (waves['time_start'],waves['time_end']),(current['time_start'],current['time_end'])]
    windows=[tuple(datetime.fromisoformat(t.replace('Z','+00:00')) for t in pair) for pair in labels]
    start=max(w[0] for w in windows);end=min(w[1] for w in windows)
    if start>=end:raise ValueError('No common coordinate time window')
    config_path=ROOT/'settings/development-weather-assumptions.json'
    config=json.loads(config_path.read_text())
    return dict(schema=1,scope='expanded_frozen_source_inventory_not_routing_qualification',
        source_qualification='unverified',result_qualification='diagnostic_only',routing_enabled=False,
        source_hashes=hashes,source_issued_at=manifest['source_issued_at'],
        common_coordinate_window=dict(first_label=start.isoformat(),last_label=end.isoformat(),
            temporal_support_qualified=False),
        acquisition=dict(new_marine_estimated_transfer_bytes=manifest['estimated_new_marine_transfer_bytes'],
            new_met_response_bytes=manifest['new_met_response_bytes'],new_wave_transfer_bytes=0,
            total_frozen_bytes=sum(e['bytes'] for e in files)),
        wind=dict(native_node_count=len(wind.x_m)*len(wind.y_m),time_count=len(wind.times),
            model_reference_time=wind.model_reference_time.isoformat(),issued_at=None,
            marine_native_point_checks=point_count,point_checks_scope='Points only; not whole segments or an area proof',
            planning_blockers=list(wind.planning_blockers),land_fraction_is_validity_mask=False),
        waves=waves,current=current,full_space_time_support_verified=False,
        blockers=['larger_area_local_rectilinear_geometry_unverified','larger_area_land_underlay_missing',
            'current_own_validity_mask_unverified','wind_own_validity_mask_unverified',
            'original_wave_time_semantics_unqualified','model_issue_time_unverified',
            'cross_product_model_run_compatibility_unverified'],
        unchanged_runtime=dict(development_support_radius_m=config['support_radius_m'],configuration_sha256=digest(config_path),source_configuration='settings/development-weather-assumptions.json',
            default_snapshot=config['departure'][:10],source_qualification='unverified',result_qualification='conditional_on_assumptions'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,default=ROOT/'fixtures/vinga-expanded-20261017')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=inspect(a.fixtures)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('EXPANDED_FORECAST_INSPECTED',report['common_coordinate_window'],'routing_enabled',False)
