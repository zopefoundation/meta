#!/usr/bin/env python3
from shared.call import abort
from shared.call import call
from shared.packages import ALL_REPOS
from shared.packages import MANYLINUX_AARCH64
from shared.packages import MANYLINUX_I686
from shared.packages import MANYLINUX_PYTHON_VERSION
from shared.packages import MANYLINUX_X86_64
from shared.packages import NEWEST_PYTHON_VERSION
from shared.packages import OLDEST_PYTHON_VERSION
from shared.packages import ORG
from shared.packages import PYPY_VERSION
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
parser.add_argument(
    '-r', '--repos',
    help='Run the script only for the given repos instead of all.',
    metavar='NAME', nargs='*', default=[])

args = parser.parse_args()
repos = args.repos if args.repos else ALL_REPOS


def call_gh(
        method, path, repo, *args, capture_output=False,
        allowed_return_codes=(0, )):
    """Call the gh api command."""
    return call(
        'gh', 'api',
        '--method', method,
        '-H', 'Accept: application/vnd.github+json',
        '-H', 'X-GitHub-Api-Version: 2022-11-28',
        f'/repos/{ORG}/{repo}/branches/{DEFAULT_BRANCH}/{path}',
        *args, capture_output=capture_output,
        allowed_return_codes=allowed_return_codes)


for repo in repos:
    print(repo, end="")
    result = call_gh(
        'GET', 'protection/required_pull_request_reviews', repo,
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
    template = meta_toml['meta']['template']
    with_docs = meta_toml['python'].get('with-docs', False)
    with_pypy = meta_toml['python']['with-pypy']
    with_windows = meta_toml['python']['with-windows']
    if template == 'c-code':
        required = [
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_AARCH64})',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_I686})',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_X86_64})',
            f'lint ({MANYLINUX_PYTHON_VERSION}, ubuntu-latest)',
            f'test ({OLDEST_PYTHON_VERSION}, macos-latest)',
            f'test ({NEWEST_PYTHON_VERSION}, macos-latest)',
            f'test ({OLDEST_PYTHON_VERSION}, ubuntu-latest)',
            f'test ({NEWEST_PYTHON_VERSION}, ubuntu-latest)',
        ]
        if with_docs:
            required.append(
                f'docs ({MANYLINUX_PYTHON_VERSION}, ubuntu-latest)')
        if with_pypy:
            required.append(f'test (pypy-{PYPY_VERSION}, ubuntu-latest)')
        if with_windows:
            required.extend([
                f'test ({OLDEST_PYTHON_VERSION}, windows-latest)',
                f'test ({NEWEST_PYTHON_VERSION}, windows-latest)',
            ])
    elif with_windows:
        required = []
        print('TBI')
        import sys
        sys.exit()
    else:  # default for most packages
        required = ['coverage', 'lint', OLDEST_PYTHON, NEWEST_PYTHON]
        if with_docs:
            required.append('docs')
        if with_pypy:
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
            'PUT', 'protection', repo, '--input', filename,
            capture_output=True)
    finally:
        os.unlink(filename)
    print(' ✅')
