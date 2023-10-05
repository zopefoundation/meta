#!/usr/bin/env python3
from shared.call import abort
from shared.call import call
from shared.packages import ALL_REPOS
from shared.packages import MANYLINUX_PYTHON_VERSION
from shared.packages import NEWEST_PYTHON_VERSION
from shared.packages import OLDEST_PYTHON_VERSION
from shared.packages import ORG
import argparse
import json
import os
import requests
import tempfile
import tomllib


BASE_URL = f'https://raw.githubusercontent.com/{ORG}'
OLDEST_PYTHON = f'py{OLDEST_PYTHON_VERSION.replace(".", "")}'
NEWEST_PYTHON = f'py{NEWEST_PYTHON_VERSION.replace(".", "")}'
DEFAULT_BRANCH = 'master'


parser = argparse.ArgumentParser(
    description='Set the branch protection rules for all known packages.\n'
                'Prerequsites: `gh auth login`.')
parser.add_argument(
    '--I-am-authenticated',
    help='If you are authenticated via `gh auth login`, use this required'
         ' parameter.',
    action='store_true',
    required=True)

args = parser.parse_args()


def call_gh(
        method, path, *args, capture_output=False, allowed_return_codes=(0, )):
    """Call the gh api command."""
    return call(
        'gh', 'api',
        '--method', method,
        '-H', 'Accept: application/vnd.github+json',
        '-H', 'X-GitHub-Api-Version: 2022-11-28',
        f'/repos/{ORG}/{repo}/branches/{DEFAULT_BRANCH}/{path}',
        *args, capture_output=capture_output,
        allowed_return_codes=allowed_return_codes)


for repo in ALL_REPOS:
    print(repo, end="")
    result = call_gh(
        'GET', 'protection/required_pull_request_reviews',
        capture_output=True, allowed_return_codes=(0, 1))
    required_pull_request_reviews = None
    if result.returncode == 1:
        if json.loads(result.stdout)['message'] != "Branch not protected":
            # If there is no branch protection we create it later on using the
            # PUT call, but if there is another error we show it:
            print(result.stdout)
            abort(result.returncode)
    else:
        required_approving_review_count = json.loads(
            result.stdout)['required_approving_review_count']
        required_pull_request_reviews = {
            'required_approving_review_count': required_approving_review_count
        }
        print(f' required reviews={required_approving_review_count}', end='')

    response = requests.get(
        f'{BASE_URL}/{repo}/{DEFAULT_BRANCH}/.meta.toml', timeout=30)
    meta_toml = tomllib.loads(response.text)
    if meta_toml['python']['with-windows']:
        required = []
        print('TBI')
        import sys
        sys.exit()
    elif meta_toml['meta']['template'] == 'c-code':
        required = [
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, manylinux2014_aarch64)',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, manylinux2014_i686)',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, manylinux2014_x86_64)',
            f'lint ({MANYLINUX_PYTHON_VERSION}, ubuntu-20.04)',
            f'test ({OLDEST_PYTHON_VERSION}, macos-11)',
            f'test ({NEWEST_PYTHON_VERSION}, macos-11)',
            f'test ({OLDEST_PYTHON_VERSION}, ubuntu-20.04)',
            f'test ({NEWEST_PYTHON_VERSION}, ubuntu-20.04)',
        ]
        if meta_toml['python'].get('with-docs', False):
            required.append(f'docs ({MANYLINUX_PYTHON_VERSION}, ubuntu-20.04)')
        if meta_toml['python']['with-pypy']:
            required.append('test (pypy-3.9, ubuntu-20.04)')
    elif meta_toml['meta']['template'] in ('c-code', 'toolkit'):
        print('TBI')
        import sys
        sys.exit()
    else:  # default for most packages
        required = ['coverage', 'lint', OLDEST_PYTHON, NEWEST_PYTHON]
        if meta_toml['python'].get('with-docs', False):
            required.append('docs')
        if meta_toml['python']['with-pypy']:
            required.append('pypy3')

    data = {
        'allow_deletions': False,
        'allow_force_pushes': False,
        'allow_fork_syncing': True,
        'lock_branch': False,
        'enforce_admins': None,
        'restrictions': None,
        'required_conversation_resolution': True,
        'required_linear_history': False,
        'required_pull_request_reviews': required_pull_request_reviews,
        'required_status_checks': {'contexts': required, 'strict': False}
    }
    fd, filename = tempfile.mkstemp('config.json', 'meta', text=True)
    try:
        file = os.fdopen(fd, 'w')
        json.dump(data, file)
        file.close()
        call_gh(
            'PUT', 'protection', '--input', filename, capture_output=True)
    finally:
        os.unlink(filename)
    print(' ✅')
