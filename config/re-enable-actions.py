#!/bin/env python3
from shared.call import call
from shared.packages import list_packages
from shared.path import change_dir
from shared.path import path_factory
import argparse
import itertools
import pathlib


base_url = 'https://github.com/zopefoundation'
base_path = pathlib.Path(__file__).parent
types = ['buildout-recipe', 'c-code', 'pure-python', 'zope-product']


parser = argparse.ArgumentParser(
    description='Re-enable GitHub Actions for all repos in a packages.txt'
                ' files.')
parser.add_argument(
    'clones',
    type=path_factory('clones', is_dir=True),
    help='path to the directory where the clones of the repositories are'
         ' stored')
parser.add_argument(
    '--force-run',
    help='Run workflow even it is already enabled.',
    action='store_true')

args = parser.parse_args()
clones_path = args.clones
repos = itertools.chain(
    *[list_packages(base_path / type / 'packages.txt')
      for type in types])

for repo in repos:
    print(repo)
    target_path = clones_path / repo
    if not target_path.exists():
        print('    ➡️  Cloning repos ...')
        with change_dir(clones_path):
            call('git', 'clone', f'{base_url}/{repo}.git')
    with change_dir(target_path):
        wfs = call(
            'gh', 'workflow', 'list', '--all', capture_output=True).stdout
        test_line = [x for x in wfs.splitlines() if x.startswith('test')][0]
        if 'disabled_inactivity' not in test_line:
            print('    ☑️  already enabled')
            if args.force_run:
                call('gh', 'workflow', 'run', 'tests.yml')
                print("Started workflow.")
            continue
        test_id = test_line.split()[-1]
        call('gh', 'workflow', 'enable', test_id)
        call('gh', 'workflow', 'run', 'tests.yml')
        print('    ✅ enabled')
