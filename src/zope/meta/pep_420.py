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
import pathlib
import shutil

from .shared.call import call
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
        branch_name = 'pep-420-native-namespace'
        updating = git_branch(branch_name)

        non_interactive_params = []
        if not args.interactive and args.commit:
            non_interactive_params = ['--no-input']
        else:
            args.commit = False

        call(bin_dir / 'bumpversion', '--breaking', *non_interactive_params)
        call(bin_dir / 'addchangelogentry',
             'Drop support for ``pkg_resources`` namespace and replace it with'
             ' PEP 420 native namespace.'
             ' Caution: This change requires to switch all packages in the '
             ' namespace of the package to versions using a PEP 420 namespace.'
             )

        setup_py = []
        for line in (path / 'setup.py').read_text().splitlines():
            if 'from setuptools import find_packages' in line:
                continue
            elif 'namespace_packages' in line:
                continue
            elif 'packages=' in line:
                continue
            elif 'package_dir=' in line:
                continue
            elif 'zope.testrunner' in line:
                setup_py.append(
                    line.replace('zope.testrunner', 'zope.testrunner >= 6.4'))
            else:
                setup_py.append(line)
            for dir in (path / 'src').iterdir():
                if dir.is_dir() and (dir / '__init__.py').exists():
                    (dir / '__init__.py').unlink()
                if dir.name == 'zope':
                    for subdir in dir.iterdir():
                        if (subdir.is_dir() and subdir.name == 'app' and
                                (subdir / '__init__.py').exists()):
                            (subdir / '__init__.py').unlink()
        (path / 'setup.py').write_text('\n'.join(setup_py) + '\n')

        if args.commit:
            print('Adding all changes ...')
            call('git', 'add', '.')

        tox_path = shutil.which('tox') or (cwd / 'bin' / 'tox')
        call(tox_path, '-p', 'auto')

        if args.commit:
            print('Committing and pushing all changes ...')
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
