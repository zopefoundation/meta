#!/usr/bin/env python3
import argparse
import os
import pathlib
import shutil
import subprocess
import sys


def call(*args, capture_output=False):
    """Call `args` as a subprocess.

    If it fails exit the process.
    """
    result = subprocess.run(args, capture_output=capture_output, text=True)
    if result.returncode != 0:
        print('ABORTING: Please fix the errors shown above.')
        sys.exit(result.returncode)
    return result


parser = argparse.ArgumentParser(
    description='Use configuration for a package.')
parser.add_argument(
    'path', type=str, help='path to the repository to be configured')
parser.add_argument('type', choices=['pure-python',
                                     'pure-python-without-pypy'],
                    help='type of the config to be used, see README.rst')


args = parser.parse_args()
path = pathlib.Path(args.path)
config_type = args.type
config_type_path = pathlib.Path(__file__).parent / config_type

if not (path / '.git').exists():
    raise ValueError('The `path` has to point to a git clone of a repository')

with open(config_type_path / 'packages.txt') as f:
    known_packages = f.read().splitlines()

if path.name in known_packages:
    print(f'{path.name} is already configured for this config type, updating.')
else:
    print(f'{path.name} is not yet configured for this config type, adding.')
    with open(config_type_path / 'packages.txt', 'a') as f:
        f.write(f'{path.name}\n')

shutil.copy(config_type_path / 'setup.cfg', path)
shutil.copy(config_type_path / 'tox.ini', path)
shutil.copy(config_type_path / 'MANIFEST.in', path)
shutil.copy(config_type_path / 'editorconfig', path / '.editorconfig')
shutil.copy(config_type_path / 'gitignore', path / '.gitignore')
shutil.copy(config_type_path / 'travis.yml', path / '.travis.yml')


cwd = os.getcwd()
branch_name = f'config-with-{config_type}'
try:
    os.chdir(path)
    if pathlib.Path('.coveragerc').exists():
        call('git', 'rm', '.coveragerc')
    if pathlib.Path('bootstrap.py').exists():
        call('git', 'rm', 'bootstrap.py')
    call(pathlib.Path(cwd) / 'bin' / 'tox', '-pall')
    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'co', branch_name)
        updating = True
    else:
        call('git', 'co', '-b', branch_name)
        updating = False
    call('git', 'add',
         'setup.cfg', 'tox.ini', '.gitignore', '.travis.yml', 'MANIFEST.in',
         '.editorconfig')
    call('git', 'ci', '-m', f'Configuring for {config_type}')
    call('git', 'push', '--set-upstream', 'origin', branch_name)
    print()
    print('If everything went fine up to here:')
    if updating:
        print('Updated the previously created PR.')
    else:
        print('Create a PR, using the URL shown above.')
finally:
    os.chdir(cwd)
