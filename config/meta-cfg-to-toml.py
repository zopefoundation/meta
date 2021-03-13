#!/usr/bin/env python3
from configparser import ConfigParser
from shared.call import call
from shared.path import change_dir
from shared.toml_encoder import TomlArraySeparatorEncoderWithNewline
import argparse
import collections
import pathlib
import sys
import toml


parser = argparse.ArgumentParser(
    description='Convert the .meta.cfg in a package to a .meta.toml.')
parser.add_argument(
    'path', type=pathlib.Path, help='path to the repository to be changed')
parser.add_argument(
    '--no-push',
    dest='no_push',
    action='store_true',
    help='Prevent direct push.')


args = parser.parse_args()
path = args.path
meta_cfg_path = path / '.meta.cfg'

if not (path / '.git').exists():
    raise ValueError('`path` does not point to a git clone of a repository!')

if not meta_cfg_path.exists():
    raise ValueError('`path` does have a `.meta.cfg`!')


src = ConfigParser()
src.read(meta_cfg_path)
src = src['meta']

dest = collections.defaultdict(dict)
dest['meta']['template'] = src['template']
dest['meta']['commit-id'] = src['commit-id']

dest['python']['with-pypy'] = src.getboolean('with-pypy', False)
dest['python']['with-legacy-python'] = src.getboolean(
    'with-legacy-python', True)
dest['python']['with-docs'] = src.getboolean('with-docs', False)
dest['python']['with-sphinx-doctests'] = src.getboolean(
    'with-sphinx-doctests', False)

dest['coverage']['fail-under'] = int(src.setdefault('fail-under', 0))

flake8_config = src.get('additional-flake8-config', '').strip()
if flake8_config:
    dest['flake8']['additional-config'] = flake8_config.splitlines()

manifest_rules = src.get('additional-manifest-rules', '').strip()
if manifest_rules:
    dest['manifest']['additional-rules'] = manifest_rules.splitlines()

check_manifest = src.get('additional-check-manifest-ignores', '').strip()
if check_manifest:
    dest['check-manifest']['additional-ignores'] = check_manifest.splitlines()


branch_name = 'covert.meta.cfg-to-.meta.toml'
with change_dir(path) as cwd:
    with open('.meta.toml', 'w') as meta_f:
        meta_f.write(
            '# Generated from:\n'
            '# https://github.com/zopefoundation/meta/tree/master/config/'
            f'{src["template"]}\n')
        toml.dump(
            dest, meta_f,
            TomlArraySeparatorEncoderWithNewline(
                separator=',\n   ', indent_first_line=True))

    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'checkout', branch_name)
        updating = True
    else:
        call('git', 'checkout', '-b', branch_name)
        updating = False
    call('git', 'rm', '.meta.cfg')
    call('git', 'add', '.meta.toml')
    call('git', 'commit', '-m', 'Switching from .meta.cfg to .meta.toml.')
    config_package_args = [
        sys.executable,
        'config-package.py',
        path,
        f'--branch={branch_name}',
    ]
    if args.no_push:
        config_package_args.append('--no-push')
    call(*config_package_args, cwd=cwd)
    print()
    print('Created resp. updated branch', end='')
    if args.no_push:
        print(', but did not push upstream.')
    else:
        call('git', 'push', '--set-upstream', 'origin', branch_name)
        print('and pushed upstream.')
