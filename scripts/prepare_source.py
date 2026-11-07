"""Apply the pinned ULTRA patch and write an unsigned build configuration."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def prepare(source: Path, root: Path) -> None:
    lock = json.loads((root / 'source.lock.json').read_text(encoding='utf-8'))
    revision = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=source, text=True
    ).strip()
    if revision != lock['commit']:
        raise ValueError('Source revision does not match source.lock.json')
    patch = root / 'patches' / 'ultra.patch'
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    if digest != lock['patch_sha256']:
        raise ValueError('ULTRA patch digest does not match source.lock.json')
    api_id = os.environ.get('TELEGRAM_API_ID', '').strip()
    api_hash = os.environ.get('TELEGRAM_API_HASH', '').strip()
    if bool(api_id) != bool(api_hash):
        raise ValueError('Both TELEGRAM_API_ID and TELEGRAM_API_HASH are required')
    smoke = not api_id
    if smoke:
        raise ValueError('Telegram API secrets are missing; refusing to package a login-disabled IPA')
    elif not re.fullmatch(r'[1-9][0-9]{0,9}', api_id) or not re.fullmatch(r'[0-9a-fA-F]{32}', api_hash):
        raise ValueError('Invalid Telegram API credential format')

    rules_source = source / 'build-system' / 'bazel-rules' / 'rules_apple'
    rules_revision = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=rules_source, text=True
    ).strip()
    if rules_revision != lock['rules_apple_commit']:
        raise ValueError('rules_apple revision does not match source.lock.json')
    rules_patch = root / 'patches' / 'rules-apple-unsigned.patch'
    if hashlib.sha256(rules_patch.read_bytes()).hexdigest() != lock['rules_apple_patch_sha256']:
        raise ValueError('rules_apple patch digest does not match source.lock.json')
    for target, change in [(source, patch), (rules_source, rules_patch)]:
        subprocess.run(['git', 'apply', '--check', str(change)], cwd=target, check=True)
    for target, change in [(source, patch), (rules_source, rules_patch)]:
        subprocess.run(['git', 'apply', str(change)], cwd=target, check=True)
    configuration = {
        'bundle_id': lock['bundle_id'],
        'api_id': api_id,
        'api_hash': api_hash,
        'team_id': 'ULTRA00001',
        'app_center_id': '0',
        'is_internal_build': 'false',
        'is_appstore_build': 'false',
        'appstore_id': '0',
        'app_specific_url_scheme': 'telegaultra',
        'premium_iap_product_id': '',
        'enable_siri': False,
        'enable_icloud': False,
    }
    output = source / 'build-input' / 'ultra-configuration.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(configuration, indent=2), encoding='utf-8')
    metadata = {
        'upstream_commit': revision,
        'patch_sha256': digest,
        'bundle_id': lock['bundle_id'],
        'smoke_build': smoke,
        'signing': 'unsigned; must be signed before installation',
    }
    artifacts = root / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    (artifacts / 'build-info.json').write_text(
        json.dumps(metadata, indent=2), encoding='utf-8'
    )
    print('Diagnostic build: login disabled until own Telegram API credentials are configured.'
          if smoke else 'Own Telegram API credentials configured; values are not logged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    arguments = parser.parse_args()
    prepare(arguments.source.resolve(), Path(__file__).resolve().parents[1])
