#!/usr/bin/env python3
import argparse
import os
import pathlib
import shutil
import subprocess
import sys


def call(*args):
    """Call `args` as a subprocess.

    If it fails exit the process.
    """
    result = subprocess.run(args)
    if result.returncode != 0:
        print('ABORTING: Please fix the errors shown above.')
        sys.exit(result.returncode)


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


travis_yml = f'''\
version: ~> 1.0
language: python
import: zopefoundation/meta:config/{config_type}/travis.yml
'''

shutil.copy(config_type_path / 'setup.cfg', path)
shutil.copy(config_type_path / 'tox.ini', path)
shutil.copy(config_type_path / 'gitignore', path / '.gitignore')
with open(path / '.travis.yml', 'w') as f:
    f.write(travis_yml)

cwd = os.getcwd()
branch_name = f'config-with-{config_type}'
try:
    os.chdir(path)
    call('tox')
    call('git', 'co', '-b', branch_name)
    call('git', 'add', 'setup.cfg', 'tox.ini', '.gitignore', '.travis.yml')
    call('git', 'ci', '-m', f'Configuring for {config_type}')
    print()
    print('If everything went fine up to here call:')
    print(f' git push --set-upstream origin {branch_name}')
    print('Then create a PR, using the URL shown by the `git push` call.')
finally:
    os.chdir(cwd)
