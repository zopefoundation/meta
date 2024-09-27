#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import tempfile
from typing import Optional

import requests
import tomlkit

from .shared.call import abort
from .shared.call import call
from .shared.packages import ALL_REPOS
from .shared.packages import MANYLINUX_AARCH64
from .shared.packages import MANYLINUX_I686
from .shared.packages import MANYLINUX_PYTHON_VERSION
from .shared.packages import MANYLINUX_X86_64
from .shared.packages import NEWEST_PYTHON_VERSION
from .shared.packages import OLDEST_PYTHON_VERSION
from .shared.packages import ORG
from .shared.packages import PYPY_VERSION


BASE_URL = f'https://raw.githubusercontent.com/{ORG}'
OLDEST_PYTHON = f'py{OLDEST_PYTHON_VERSION.replace(".", "")}'
NEWEST_PYTHON = f'py{NEWEST_PYTHON_VERSION.replace(".", "")}'
DEFAULT_BRANCH = 'master'


def _call_gh(
        method, path, repo, *args, capture_output=True,
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


def set_branch_protection(
        repo: str, meta_path: Optional[pathlib.Path] = None) -> bool:
    result = _call_gh(
        'GET', 'protection/required_pull_request_reviews', repo,
        allowed_return_codes=(0, 1))
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

    if meta_path is None:
        response = requests.get(
            f'{BASE_URL}/{repo}/{DEFAULT_BRANCH}/.meta.toml', timeout=30)
        meta_toml = tomlkit.loads(response.text)
    else:
        with open(meta_path) as f:
            meta_toml = tomlkit.load(f)
    template = meta_toml['meta']['template']
    with_docs = meta_toml['python'].get('with-docs', False)
    with_pypy = meta_toml['python']['with-pypy']
    with_windows = meta_toml['python']['with-windows']
    with_macos = meta_toml['python']['with-macos']
    required = ['linting']
    if template == 'c-code':
        required.extend([
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_AARCH64})',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_I686})',
            f'manylinux ({MANYLINUX_PYTHON_VERSION}, {MANYLINUX_X86_64})',
            f'test ({OLDEST_PYTHON_VERSION}, macos-latest)',
            f'test ({NEWEST_PYTHON_VERSION}, macos-latest)',
            f'test ({OLDEST_PYTHON_VERSION}, ubuntu-latest)',
            f'test ({NEWEST_PYTHON_VERSION}, ubuntu-latest)',
            'coveralls_finish',
        ])
        if with_docs:
            required.append(
                f'docs ({MANYLINUX_PYTHON_VERSION}, ubuntu-latest)')
        if with_pypy:
            required.append(f'test (pypy-{PYPY_VERSION}, ubuntu-latest)')
            required.append(f'test (pypy-{PYPY_VERSION}, windows-latest)')
        if with_windows:
            required.extend([
                f'test ({OLDEST_PYTHON_VERSION}, windows-latest)',
                f'test ({NEWEST_PYTHON_VERSION}, windows-latest)',
            ])
    elif with_windows or with_macos:
        required.extend([
            'ubuntu-coverage',
            f'ubuntu-{OLDEST_PYTHON}',
            f'ubuntu-{NEWEST_PYTHON}',
        ])
        if with_windows:
            required.extend([
                f'windows-{OLDEST_PYTHON}',
                f'windows-{NEWEST_PYTHON}',
            ])
        if with_macos:
            required.extend([
                f'macos-{OLDEST_PYTHON}',
                f'macos-{NEWEST_PYTHON}',
            ])
        if with_pypy:
            required.extend([
                'ubuntu-pypy3',
                'windows-pypy3',
            ])
        if with_docs:
            required.append('ubuntu-docs')
    else:  # default for most packages
        required.extend([OLDEST_PYTHON, NEWEST_PYTHON])
        if template != 'toolkit':
            required.append('coverage')
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
        _call_gh('PUT', 'protection', repo, '--input', filename)
    finally:
        os.unlink(filename)
    return True


def main():
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
    parser.add_argument(
        '-m', '--meta',
        help='Use this .meta.toml instead the one on `master` of the repos.',
        metavar='PATH', default=None, type=pathlib.Path)

    args = parser.parse_args()
    repos = args.repos if args.repos else ALL_REPOS
    meta_path = args.meta

    if meta_path and len(repos) > 1:
        print('--meta can only be used together with a single repos.')
        abort(-1)

    for repo in repos:
        print(repo, end="")
        set_branch_protection(repo, meta_path)
        print(' ✅')
