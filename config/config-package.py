#!/usr/bin/env python3
from configparser import ConfigParser
import argparse
import os
import pathlib
import shutil
import subprocess
import sys


META_HINT = """\
# Generated from:
# https://github.com/zopefoundation/meta/tree/master/config/{config_type}
"""


def call(*args, capture_output=False):
    """Call `args` as a subprocess.

    If it fails exit the process.
    """
    result = subprocess.run(args, capture_output=capture_output, text=True)
    if result.returncode != 0:
        print('ABORTING: Please fix the errors shown above.')
        print('Proceed anyway (y/N)?', end=' ')
        if input().lower() != 'y':
            sys.exit(result.returncode)
    return result


def copy_with_meta(source, destination, config_type, **kw):
    """Copy the source file to destination and a hint of origin."""
    with open(source) as f_:
        f_data = f_.read()

    with open(destination, 'w') as f_:
        f_.write(META_HINT.format(config_type=config_type))
        if kw:
            f_data = f_data.format(**kw)
        f_.write(f_data)


parser = argparse.ArgumentParser(
    description='Use configuration for a package.')
parser.add_argument(
    'path', type=str, help='path to the repository to be configured')
parser.add_argument(
    '--no-push',
    dest='no_push',
    action='store_true',
    help='Prevent direct push.')
parser.add_argument('type', choices=['pure-python',
                                     'pure-python-with-multiprocess',
                                     'pure-python-without-pypy'],
                    help='type of the config to be used, see README.rst')


args = parser.parse_args()
path = pathlib.Path(args.path)
config_type = args.type
default_path = pathlib.Path(__file__).parent / 'default'
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


# Read and update meta configuration
meta_cfg = ConfigParser()
meta_cfg_path = path / '.meta.cfg'
if meta_cfg_path.exists():
    meta_cfg.read(meta_cfg_path)
else:
    meta_cfg['meta'] = {}
meta_opts = meta_cfg['meta']
meta_opts['template'] = config_type
meta_opts['commit-id'] = call(
    'git', 'log', '-n1', '--format=format:%H', capture_output=True).stdout

# Copy template files
copy_with_meta(
    default_path / 'setup.cfg', path / 'setup.cfg', config_type)
copy_with_meta(
    default_path / 'MANIFEST.in', path / 'MANIFEST.in', config_type)
copy_with_meta(
    default_path / 'editorconfig', path / '.editorconfig', config_type)
copy_with_meta(
    default_path / 'gitignore', path / '.gitignore', config_type)
shutil.copy(config_type_path / 'tox.ini', path)
shutil.copy(config_type_path / 'travis.yml', path / '.travis.yml')

add_coveragerc = False
rm_coveragerc = False
if (config_type_path / 'coveragerc').exists():
    copy_with_meta(
        config_type_path / 'coveragerc', path / '.coveragerc', config_type,
        package_name=path.name)
    add_coveragerc = True
elif (path / '.coveragerc').exists():
    rm_coveragerc = True


# Modify templates with meta options.
tox_ini_path = path / 'tox.ini'
with open(tox_ini_path) as f_:
    tox_ini = f_.read()

with open(tox_ini_path, 'w') as f_:
    # initialize configuration if not already present
    fail_under = meta_opts.setdefault('fail-under', '0')
    f_.write(tox_ini.format(
        coverage_report_options=f'--fail-under={fail_under}'))


cwd = os.getcwd()
branch_name = f'config-with-{config_type}'
try:
    os.chdir(path)
    if pathlib.Path('bootstrap.py').exists():
        call('git', 'rm', 'bootstrap.py')
    call(pathlib.Path(cwd) / 'bin' / 'tox', '-p', 'auto')

    # Modify files with user interaction only after all tests are green.
    with open('.meta.cfg', 'w') as meta_f:
        meta_f.write(
            '# Generated from:\n'
            '# https://github.com/zopefoundation/meta/tree/master/config/'
            f'{config_type}\n')
        meta_cfg.write(meta_f)

    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'checkout', branch_name)
        updating = True
    else:
        call('git', 'checkout', '-b', branch_name)
        updating = False
    call('git', 'add',
         'setup.cfg', 'tox.ini', '.gitignore', '.travis.yml', 'MANIFEST.in',
         '.editorconfig', '.meta.cfg')
    if rm_coveragerc:
        call('git', 'rm', '.coveragerc')
    if add_coveragerc:
        call('git', 'add', '.coveragerc')
    call('git', 'commit', '-m', f'Configuring for {config_type}')
    if not args.no_push:
        call('git', 'push', '--set-upstream', 'origin', branch_name)
    print()
    print('If everything went fine up to here:')
    if updating:
        print('Updated the previously created PR.')
    else:
        print('Create a PR, using the URL shown above.')
finally:
    os.chdir(cwd)
