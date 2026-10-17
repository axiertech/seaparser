"""Stage/verify one standalone review; explicitly publish only a new URL.

Reuses Vinga's atomic copy and hash guards. No service or system changes.
"""
import argparse
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

from deployment.vinga_upgrade import atomic_public_copy, tree_hashes
from deployment.prepare_vinga import digest, PUBLIC, ROOT
from presentation.frozen_forecast_html import render_frozen_forecast
from presentation.real_route_html import render as render_real_routes

NAME = 'vinga-prognosprov.html'
URL = 'https://seaparser.com/' + NAME
ARTIFACT = ROOT / 'artifacts/vinga-frozen-review/index.html'


def select_review(kind):
    """Only fixed reviewed standalone destinations; never accept arbitrary paths."""
    global NAME, URL, ARTIFACT, REVIEW_KIND
    if kind not in ('forecast', 'routes', 'routes-motion'):
        raise ValueError('Unknown standalone review')
    REVIEW_KIND=kind
    NAME={'forecast':'vinga-prognosprov.html','routes':'vinga-ruttjamforelse.html',
          'routes-motion':'vinga-ruttjamforelse-ramar.html'}[kind]
    URL='https://seaparser.com/'+NAME
    ARTIFACT=(ROOT/'artifacts'/({'forecast':'vinga-frozen-review','routes':'real-route-review',
                    'routes-motion':'motion-route-review'}[kind]))/'index.html'


REVIEW_KIND='forecast'


def validate_page(data):
    if REVIEW_KIND in ('routes','routes-motion'):
        result=json.loads(ARTIFACT.with_name('result.json').read_text())
        if (result.get('result_qualification')!='conditional_on_assumptions'
                or result.get('data_quality',{}).get('weather')!='real_frozen_with_assumptions'
                or not result.get('weather_provenance',{}).get('historical_snapshot')
                or not result['weather_provenance'].get('assumptions')
                or not result.get('alternatives')):
            raise ValueError('Historical real-route assumptions and alternatives required')
        if REVIEW_KIND=='routes-motion' and result['weather_provenance'].get('motion_frame')!='wgs84-aeqd-proj-differential-v1':
            raise ValueError('Motion review requires explicit physical/projected kinematics')
        if render_real_routes(result).encode()!=data:
            raise ValueError('Unexpected standalone route HTML/assets')
        return

    page = data.decode('utf-8')
    match = re.search(r'<script id="review-data" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError('Missing review data')
    review = json.loads(match[1])
    # Exact reviewed template/assets, including CSP hashes and non-routing notice.
    if render_frozen_forecast(review).encode() != data:
        raise ValueError('Unexpected standalone HTML/assets')
    if {p['id'] for p in review['products']} != {'wind', 'waves', 'current'}:
        raise ValueError('All three reviewed products required')
    if not all(p['times'] for p in review['products']):
        raise ValueError('Validity times required')


def prepare(stage):
    if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Clean reviewed checkout required')
    data = ARTIFACT.read_bytes()
    if REVIEW_KIND=='forecast':
        receipt = json.loads(ARTIFACT.with_suffix('.receipt.json').read_text())
        if sha256(data).hexdigest() != receipt['sha256']:
            raise ValueError('Artifact receipt hash mismatch')
    validate_page(data)
    if (PUBLIC / NAME).exists() or (PUBLIC / NAME).is_symlink():
        raise ValueError('Separate URL already exists; refuse overwrite')
    before = tree_hashes(PUBLIC)
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    ready = stage / 'public-ready'
    ready.mkdir()
    (ready / NAME).write_bytes(data)
    manifest = {'schema': 1, 'checkout': str(ROOT), 'commit': subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'public_root': str(PUBLIC), 'url': URL, 'public_before': before,
        'public_files': {NAME: sha256(data).hexdigest()}, 'published': False,
        'notice': 'Historical real-source routes with explicit assumptions' if REVIEW_KIND in ('routes','routes-motion') else 'Historical raw forecast samples; routing remains unqualified'}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def verify(stage):
    if stage.is_symlink() or (stage / 'public-ready').is_symlink():
        raise ValueError('Symlink in staging path')
    manifest = json.loads((stage / 'manifest.json').read_text())
    if (manifest['schema'] != 1 or manifest['checkout'] != str(ROOT)
            or manifest['public_root'] != str(PUBLIC) or manifest['url'] != URL
            or set(manifest['public_files']) != {NAME}):
        raise ValueError('Unexpected publication identity/allowlist')
    if tree_hashes(stage / 'public-ready') != manifest['public_files']:
        raise ValueError('Staged public files differ from exact allowlist/hash')
    validate_page((stage / 'public-ready' / NAME).read_bytes())
    if subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() != manifest['commit']:
        raise ValueError('Checkout changed after preparation')
    if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Checkout has unreviewed changes')
    if tree_hashes(PUBLIC) != manifest['public_before']:
        raise ValueError('Existing public content changed; prepare a new snapshot')
    if (PUBLIC / NAME).exists() or (PUBLIC / NAME).is_symlink():
        raise ValueError('Separate URL already exists; refuse overwrite')
    return manifest


def publish(stage):
    with (stage / 'publish.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = verify(stage)
        os.umask(0o022)
        atomic_public_copy(stage / 'public-ready' / NAME, PUBLIC / NAME,
                           {'uid': 1000, 'gid': 1000, 'mode': 0o644})
        if tree_hashes(PUBLIC) != manifest['public_before'] | manifest['public_files']:
            raise ValueError('Public content verification failed; inspect before further changes')
        result = {'url': URL, 'commit': manifest['commit'], 'sha256': digest(PUBLIC / NAME),
                  'existing_public_content_unchanged': True, 'published': True,
                  'https_verified': False}
        (stage / 'publication-result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'publish'))
    parser.add_argument('stage', type=Path)
    parser.add_argument('--review', choices=('forecast','routes','routes-motion'), default='forecast')
    args = parser.parse_args()
    select_review(args.review)
    try:
        result = {'prepare': prepare, 'verify': verify, 'publish': publish}[args.action](args.stage.absolute())
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
