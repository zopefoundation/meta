#!/usr/bin/env python3
import argparse
import pathlib
import shutil

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
config_type_path = pathlib.Path(config_type)

if not (path / '.git').exists():
    raise ValueError('The `path` has to point to a git clone of a repository')

with open(config_type_path / 'packages.txt') as f:
    known_packages = f.readlines()

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
