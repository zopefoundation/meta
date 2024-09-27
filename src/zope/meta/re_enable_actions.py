#!/usr/bin/env python3
##############################################################################
#
# Copyright (c) 2021 Zope Foundation and Contributors.
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

from .shared.call import call
from .shared.packages import ALL_REPOS
from .shared.packages import ORG


base_url = f'https://github.com/{ORG}'
BASE_PATH = pathlib.Path(__file__).parent


def run_workflow(base_url, org, repo):
    """Manually start the tests.yml workflow of a repository."""
    result = call('gh', 'workflow', 'run', 'tests.yml', '-R', f'{org}/{repo}')
    if result.returncode != 0:
        print('To enable manually starting workflows clone the repository'
              ' and run meta/config/config-package.py on it.')
        print('Command to clone:')
        print(f'git clone {base_url}/{repo}.git')
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Re-enable GitHub Actions for all repos in a packages.txt'
                    ' files.')
    parser.add_argument(
        '--force-run',
        help='Run workflow even it is already enabled.',
        action='store_true')

    args = parser.parse_args()

    for repo in ALL_REPOS:
        print(repo)
        wfs = call(
            'gh', 'workflow', 'list', '--all', '-R', f'{ORG}/{repo}',
            capture_output=True).stdout
        test_line = [x for x in wfs.splitlines() if x.startswith('test')][0]
        if 'disabled_inactivity' not in test_line:
            print('    ☑️  already enabled')
            if args.force_run:
                run_workflow(base_url, ORG, repo)
            continue
        test_id = test_line.split()[-1]
        call('gh', 'workflow', 'enable', test_id, '-R', f'{ORG}/{repo}')
        if run_workflow(base_url, ORG, repo):
            print('    ✅ enabled')
