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

import tomlkit

from .shared.call import call
from .shared.call import wait_for_accept
from .shared.git import get_branch_name
from .shared.git import git_branch
from .shared.packages import FUTURE_PYTHON_VERSION
from .shared.packages import NEWEST_PYTHON_VERSION
from .shared.packages import OLDEST_PYTHON_VERSION
from .shared.packages import supported_python_versions
from .shared.path import change_dir
from .shared.script_args import get_shared_parser


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
    args = parser.parse_args()
    path = args.path.absolute()

    if not (path / '.git').exists():
        raise ValueError(
            '`path` does not point to a git clone of a repository!')
    if not (path / '.meta.toml').exists():
        raise ValueError('The repository `path` points to has no .meta.toml!')

    with change_dir(path) as cwd_str:
        cwd = pathlib.Path(cwd_str)
        bin_dir = cwd / 'bin'
        with open('.meta.toml', 'rb') as meta_f:
            meta_toml = collections.defaultdict(dict, **tomlkit.load(meta_f))
        config_type = meta_toml['meta']['template']
        oldest_python_version = meta_toml['python'].get('oldest-python',
                                                        OLDEST_PYTHON_VERSION)
        branch_name = get_branch_name(args.branch_name, config_type)
        updating = git_branch(branch_name)
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

        if no_longer_supported or not_yet_supported:
            call(bin_dir / 'bumpversion', '--feature', *non_interactive_params)
        else:
            print('No changes required.')
            sys.exit(0)

        if no_longer_supported:
            version_spec = ', '.join(sorted(no_longer_supported))
            call(bin_dir / 'addchangelogentry',
                 f'Drop support for Python {version_spec}.',
                 *non_interactive_params)
            python_versions_args.append(
                '--drop=' + ','.join(no_longer_supported))

        if not_yet_supported:
            version_spec = ', '.join(sorted(not_yet_supported))
            call(
                bin_dir / 'addchangelogentry',
                f'Add support for Python {version_spec}.',
                *non_interactive_params)
            python_versions_args.append(
                '--add=' +
                ','.join(supported_python_versions(oldest_python_version))
            )
        if args.with_future_python:
            call(
                bin_dir / 'addchangelogentry',
                f'Add preliminary support for Python {FUTURE_PYTHON_VERSION}.',
                *non_interactive_params)

        if no_longer_supported or not_yet_supported:
            call(bin_dir / 'check-python-versions', '--only=setup.py',
                 *python_versions_args)
            print('Look through .meta.toml to see if it needs changes.')
            call(os.environ['EDITOR'], '.meta.toml')

            config_package_args = [
                bin_dir / 'config-package',
                path,
                f'--branch={branch_name}',
                '--no-push',
            ]
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
            call('find', src, '-name', '*.py', '-exec', bin_dir / 'pyupgrade',
                 '--py3-plus', py_ver_plus, '{}', ';')
            call(bin_dir / 'pyupgrade',
                 '--py3-plus',
                 py_ver_plus,
                 'setup.py',
                 allowed_return_codes=(0, 1))

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
                f'{"|".join(no_longer_supported)}|sys.version|PY3|Py3|Python 3'
                '|__unicode__|ImportError',
                src,
                *excludes,
                allowed_return_codes=(
                    0,
                    1))
            wait_for_accept()

            if args.run_tests:
                tox_path = shutil.which('tox') or (cwd / 'bin' / 'tox')
                call(tox_path, '-p', 'auto')

            if args.commit:
                print('Adding, committing and pushing all changes ...')
                call('git', 'add', '.')
                call('git', 'commit', '-m', 'Update Python version support.')
                call('git', 'push', '--set-upstream', 'origin', branch_name)
                if updating:
                    print('Updated the previously created PR.')
                else:
                    print(
                        'Are you logged in via `gh auth login` to'
                        ' create a PR? (y/N)?', end=' ')
                    if input().lower() == 'y':
                        call('gh', 'pr', 'create', '--fill', '--title',
                             'Update Python version support.')
                    else:
                        print('If everything went fine up to here:')
                        print('Create a PR, using the URL shown above.')
            else:
                print('Applied all changes. Please check and commit manually.')
