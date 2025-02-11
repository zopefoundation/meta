#!/usr/bin/env python3
##############################################################################
#
# Copyright (c) 2025 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import argparse
import collections
import pathlib
import shutil

import tomlkit

from .shared.call import call
from .shared.git import get_branch_name
from .shared.git import git_branch
from .shared.path import change_dir


def main():
    parser = argparse.ArgumentParser(
        description='Update a repository to PEP 420 native namespace.'
    )
    parser.add_argument('path',
                        type=pathlib.Path,
                        help='path to the repository to be updated')
    parser.add_argument(
        '--branch',
        dest='branch_name',
        default=None,
        help='Define a git branch name to be used for the changes. If not'
        ' given it is constructed automatically and includes the configuration'
        ' type')
    parser.add_argument(
        '--no-commit',
        dest='commit',
        action='store_false',
        default=True,
        help='Don\'t "git commit" changes made by this script.')
    parser.add_argument(
        '--interactive',
        dest='interactive',
        action='store_true',
        default=False,
        help='Run interactively: Scripts will prompt for input. Implies '
        '--no-commit, changes will not be committed and pushed automatically.')

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
        branch_name = get_branch_name(args.branch_name, config_type)
        updating = git_branch(branch_name)

        non_interactive_params = []
        if not args.interactive and args.commit:
            non_interactive_params = ['--no-input']
        else:
            args.commit = False

        call(bin_dir / 'bumpversion', '--breaking', *non_interactive_params)
        call(bin_dir / 'addchangelogentry',
             'Drop support for pkg_resources namespace and replace it with'
             ' PEP 420 native namespace.')

        setup_py = []
        for line in (path / 'setup.py').read_text().splitlines():
            if 'find_packages' in line:
                continue
            elif 'zope.testrunner' in line:
                setup_py.append(
                    line.replace('zope.testrunner', 'zope.testrunner >= 6.4'))
            elif 'namespace_packages' in line:
                leading_spaces = len(line) - len(line.lstrip())
                packages = []
                for dir in (path / 'src').iterdir():
                    if dir.is_dir() and (dir / '__init__.py').exists():
                        (dir / '__init__.py').unlink()
                        for sub_dir in dir.iterdir():
                            if (sub_dir / '__init__.py').exists():
                                packages.append(
                                    f'{dir.name}.{sub_dir.name}')

                setup_py.append(
                    f'{" " * leading_spaces}packages={packages!r},')
            else:
                setup_py.append(line)
        (path / 'setup.py').write_text('\n'.join(setup_py) + '\n')

        tox_path = shutil.which('tox') or (cwd / 'bin' / 'tox')
        call(tox_path, '-p', 'auto')

        if args.commit:
            print('Adding, committing and pushing all changes ...')
            call('git', 'add', '.')
            call('git', 'commit', '-m', 'Switch to PEP 420 native namespace.')
            call('git', 'push', '--set-upstream', 'origin', branch_name)
            if updating:
                print('Updated the previously created PR.')
            else:
                print(
                    'Are you logged in via `gh auth login` to'
                    ' create a PR? (y/N)?', end=' ')
                if input().lower() == 'y':
                    call('gh', 'pr', 'create', '--fill', '--title',
                         'Switch to PEP 420 native namespace.')
                else:
                    print('If everything went fine up to here:')
                    print('Create a PR, using the URL shown above.')
        else:
            print('Applied all changes. Please check and commit manually.')
