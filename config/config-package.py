#!/usr/bin/env python3
from configparser import ConfigParser
import argparse
import jinja2
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


def copy_with_meta(template_name, destination, config_type, **kw):
    """Copy the source file to destination and a hint of origin.

    If kwargs are given they are used as template arguments.
    """
    with open(destination, 'w') as f_:
        f_.write(META_HINT.format(config_type=config_type))
        template = jinja_env.get_template(template_name)
        f_.write(template.render(**kw))


parser = argparse.ArgumentParser(
    description='Use configuration for a package.')
parser.add_argument(
    'path', type=str, help='path to the repository to be configured')
parser.add_argument(
    '--no-push',
    dest='no_push',
    action='store_true',
    help='Prevent direct push.')
parser.add_argument(
    '--with-pypy',
    dest='with_pypy',
    action='store_true',
    default=False,
    help='Activate PyPy support if not already configured in .meta.cfg.')
parser.add_argument(
    'type',
     choices=[
        'buildout-recipe',
        'pure-python',
    ],
    help='type of the config to be used, see README.rst')


args = parser.parse_args()
path = pathlib.Path(args.path)
config_type = args.type
default_path = pathlib.Path(__file__).parent / 'default'
config_type_path = pathlib.Path(__file__).parent / config_type
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader([config_type_path, default_path]),
    variable_start_string='%(',
    variable_end_string=')s',
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

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
with_pypy = meta_opts.getboolean('with-pypy', False) or args.with_pypy
meta_opts['with-pypy'] = str(with_pypy)

# Copy template files
copy_with_meta('setup.cfg', path / 'setup.cfg', config_type)
copy_with_meta('editorconfig', path / '.editorconfig', config_type)
copy_with_meta('gitignore', path / '.gitignore', config_type)
workflows = path / '.github' / 'workflows'
workflows.mkdir(parents=True, exist_ok=True)

add_coveragerc = False
rm_coveragerc = False
if (config_type_path / 'coveragerc.j2').exists():
    copy_with_meta(
        'coveragerc.j2', path / '.coveragerc', config_type,
        package_name=path.name)
    add_coveragerc = True
elif (path / '.coveragerc').exists():
    rm_coveragerc = True


fail_under = meta_opts.setdefault('fail-under', '0')
copy_with_meta(
    'tox.ini.j2', path / 'tox.ini', config_type,
    fail_under=fail_under, with_pypy=with_pypy)
copy_with_meta(
    'tests.yml.j2', workflows / 'tests.yml', config_type,
    with_pypy=with_pypy)


# Modify MANIFEST.in with meta options
additional_manifest_rules = meta_opts.get(
    'additional-manifest-rules', '').strip()
copy_with_meta(
    'MANIFEST.in.j2', path / 'MANIFEST.in', config_type,
    additional_rules=additional_manifest_rules)

cwd = os.getcwd()
branch_name = f'config-with-{config_type}'
try:
    os.chdir(path)
    if pathlib.Path('bootstrap.py').exists():
        call('git', 'rm', 'bootstrap.py')
    if pathlib.Path('.travis.yml').exists():
        call('git', 'rm', '.travis.yml')
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
         'setup.cfg', 'tox.ini', '.gitignore', '.github/workflows/tests.yml',
         'MANIFEST.in', '.editorconfig', '.meta.cfg')
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
