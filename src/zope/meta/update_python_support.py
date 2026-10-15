#!/usr/bin/env python3
##############################################################################
#
# Copyright (c) 2022 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import collections
import configparser
import os
import pathlib
import shutil
import sys
import sysconfig

import tomlkit
from zest.releaser import choose

from .set_branch_protection_rules import get_package_name
from .set_branch_protection_rules import set_branch_protection
from .shared.call import call
from .shared.call import wait_for_accept
from .shared.git import branch_exists
from .shared.git import create_pull_request
from .shared.git import get_branch_name
from .shared.git import git_branch
from .shared.packages import FUTURE_PYTHON_VERSION
from .shared.packages import NEWEST_PYTHON_VERSION
from .shared.packages import OLDEST_PYTHON_VERSION
from .shared.packages import supported_python_versions
from .shared.path import change_dir
from .shared.script_args import get_shared_parser


PR_TITLE = 'Update Python version support.'


def get_pending_update(branch_name) -> str | None:
    """Return why an update by a previous run is still pending, else None."""
    if call('git', 'ls-remote', '--exit-code', '--heads', 'origin',
            branch_name, capture_output=True,
            allowed_return_codes=(0, 2)).returncode == 0:
        return f'Branch {branch_name} already exists.'
    pr_urls = call(
        'gh', 'pr', 'list', '--state', 'open',
        '--search', f'"{PR_TITLE}" in:title', '--json', 'url',
        '--jq', '.[].url', capture_output=True).stdout.split()
    if pr_urls:
        return f'Pull request {pr_urls[0]} is still open.'
    return None


def get_tox_ini_python_versions(path) -> set:
    config = configparser.ConfigParser()
    config.read(path)
    envs = config['tox']['envlist'].split()
    raw_versions = {
        env.replace('py3', '3.') for env in envs
        if env.startswith('py') and env != 'pypy3'
    }
    # c-code template uses `py313,py313-pure`, get rid of the pure version:
    versions = {v.partition(',')[0] for v in raw_versions}
    # some packages use `py38-watch` or similar, get rid of the suffix:
    versions = {v.partition('-')[0] for v in versions}
    # free-threaded envs like py314t should map to 3.14:
    return {v.rstrip('t') for v in versions}


def main():
    parser = get_shared_parser(
        'Update Python versions of a package to currently supported ones.',
        interactive=True)
    parser.add_argument(
        '--with-future-python',
        dest='with_future_python',
        action='store_true',
        default=False,
        help='Also enable testing the future Python version.')
    parser.add_argument(
        '--with-free-threaded-python',
        dest='with_free_threaded_python',
        action='store_true',
        default=False,
        help='Also enable testing with free-threaded Python (nogil).')
    parser.add_argument(
        '--auto-update',
        dest='auto_update',
        action='store_true',
        default=False,
        help='Run without any questions asked and without running the tests.'
        ' Only to be used by CI.')

    args = parser.parse_args()
    if args.auto_update:
        # Test failures surface in the created PR:
        args.run_tests = False
    path = args.path.absolute()
    # Scripts of zope.meta and its dependencies (e.g. zest.releaser) live
    # next to the Python executable of the environment zope.meta runs in:
    bin_dir = pathlib.Path(sysconfig.get_path('scripts'))

    if not (path / '.git').exists():
        raise ValueError(
            '`path` does not point to a git clone of a repository!')
    if not (path / '.meta.toml').exists():
        raise ValueError('The repository `path` points to has no .meta.toml!')

    with change_dir(path) as cwd_str:
        with open('.meta.toml', 'rb') as meta_f:
            meta_toml = collections.defaultdict(dict, **tomlkit.load(meta_f))
        config_type = meta_toml['meta']['template']
        oldest_python_version = meta_toml['python'].get('oldest-python',
                                                        OLDEST_PYTHON_VERSION)
        branch_name = get_branch_name(args.branch_name, config_type)
        if args.auto_update:
            pending_update = get_pending_update(branch_name)
            if pending_update:
                print(f'Skipping: {pending_update}')
                sys.exit(0)
        updating = branch_exists(branch_name)
        if updating:
            # Compare against the state of the previous run on this branch:
            git_branch(branch_name)
        to_be_supported = set(supported_python_versions(oldest_python_version))

        current_python_versions = get_tox_ini_python_versions('tox.ini')
        no_longer_supported = (
            current_python_versions -
            to_be_supported
        )
        not_yet_supported = (
            to_be_supported -
            current_python_versions
        )
        if (meta_toml['python'].get('with-future-python', True) and
                NEWEST_PYTHON_VERSION in to_be_supported):
            # If with-future-python is enabled, the newest python version is
            # already in `tox.ini` but not yet in `setup.py`:
            not_yet_supported.add(NEWEST_PYTHON_VERSION)

        non_interactive_params = []
        python_versions_args = []
        if not args.interactive and args.commit:
            non_interactive_params = ['--no-input']
        else:
            args.commit = False

        # zest.releaser fails on packages without change log, e.g. zopetoolkit:
        with_history = choose.version_control().history_file() is not None
        if no_longer_supported or not_yet_supported:
            if not updating:
                git_branch(branch_name)
            if with_history:
                call(bin_dir / 'bumpversion', '--feature',
                     *non_interactive_params)
        else:
            print('No changes required.')
            sys.exit(0)

        if no_longer_supported:
            version_spec = ', '.join(sorted(no_longer_supported))
            if with_history:
                call(bin_dir / 'addchangelogentry',
                     f'Drop support for Python {version_spec}.',
                     *non_interactive_params)
            python_versions_args.append(
                '--drop=' + ','.join(no_longer_supported))

        if not_yet_supported:
            version_spec = ', '.join(sorted(not_yet_supported))
            if with_history:
                call(
                    bin_dir / 'addchangelogentry',
                    f'Add support for Python {version_spec}.',
                    *non_interactive_params)
            python_versions_args.append(
                '--add=' +
                ','.join(supported_python_versions(oldest_python_version))
            )
        if args.with_future_python and with_history:
            call(
                bin_dir / 'addchangelogentry',
                f'Add preliminary support for Python {FUTURE_PYTHON_VERSION}.',
                *non_interactive_params)

        if no_longer_supported or not_yet_supported:
            if args.auto_update:
                # Classifiers and required version, per file:
                input_text = 'Y\n' * 4
            else:
                input_text = None
            # The metadata is in `pyproject.toml` if `setup-to-pyproject` ran:
            call(bin_dir / 'check-python-versions',
                 '--only=setup.py,pyproject.toml',
                 *python_versions_args, input=input_text)
            if not args.auto_update:
                print('Look through .meta.toml to see if it needs changes.')
                call(os.environ['EDITOR'], '.meta.toml')

            config_package_args = [
                bin_dir / 'config-package',
                path,
                f'--branch={branch_name}',
                '--no-push',
            ]
            if not args.auto_update:
                # `--auto-update` updates the branch protection rules itself
                # after pushing:
                config_package_args.append('--admin')
            if args.with_future_python:
                config_package_args.append('--with-future-python')
            if args.with_free_threaded_python:
                config_package_args.append('--with-free-threaded-python')
            if not args.commit:
                config_package_args.append('--no-commit')
            if not args.run_tests:
                config_package_args.append('--no-tests')
            if args.overrides_path:
                config_package_args.append(
                    f'--overrides={args.overrides_path}')
            call(*config_package_args, cwd=cwd_str)

            src = path.resolve() / 'src'
            py_ver_plus = f'--py{oldest_python_version.replace(".", "")}-plus'
            if src.exists():  # e.g. zopetoolkit has no code
                call('find', src, '-name', '*.py', '-exec',
                     bin_dir / 'pyupgrade', '--py3-plus', py_ver_plus, '{}',
                     ';')
            call(bin_dir / 'pyupgrade',
                 '--py3-plus',
                 py_ver_plus,
                 'setup.py',
                 allowed_return_codes=(0, 1))

            if not args.auto_update:
                excludes = (
                    '--exclude-dir',
                    '__pycache__',
                    '--exclude-dir',
                    '*.egg-info',
                    '--exclude',
                    '*.pyc',
                    '--exclude',
                    '*.so')
                print('Replace any remaining code that might'
                      ' support legacy Python:')
                call(
                    'egrep',
                    '-rn',
                    f'{"|".join(no_longer_supported)}|sys.version|PY3|Py3|'
                    'Python 3|__unicode__|ImportError',
                    src,
                    *excludes,
                    allowed_return_codes=(
                        0,
                        1))
                wait_for_accept()

            if args.auto_update:
                # Apply the fixes of the pre-commit hooks, remaining problems
                # surface in the created PR:
                call(bin_dir / 'pre-commit', 'run', '--all-files',
                     allowed_return_codes=(0, 1))

            if args.run_tests:
                tox_path = shutil.which('tox') or (bin_dir / 'tox')
                call(tox_path, '-p', 'auto')

            if args.commit:
                print('Adding, committing and pushing all changes ...')
                call('git', 'add', '.')
                call('git', 'commit', '-m', PR_TITLE)
                call('git', 'push', '--set-upstream', 'origin', branch_name)
                if updating:
                    print('Updated the previously created PR.')
                elif args.auto_update:
                    create_pull_request(
                        PR_TITLE,
                        body='Created by `update-python-support`.')
                else:
                    create_pull_request(PR_TITLE)
                if args.auto_update:
                    # Only after the push, so a failing run does not leave
                    # `master` requiring checks nobody provides.
                    # Requires a token with administration permission:
                    set_branch_protection(
                        get_package_name(), path / '.meta.toml')
            else:
                print('Applied all changes. Please check and commit manually.')
