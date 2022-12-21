#!/usr/bin/env', 'python3
from shared.call import call
from shared.call import wait_for_accept
from shared.git import get_branch_name
from shared.git import git_branch
from shared.path import change_dir
import argparse
import collections
import os
import pathlib
import shutil
import sys
import toml


parser = argparse.ArgumentParser(
    description='Drop support of Python 2.7 up to 3.6 from a package.')
parser.add_argument(
    'path', type=pathlib.Path, help='path to the repository to be configured')
parser.add_argument(
    '--branch',
    dest='branch_name',
    default=None,
    help='Define a git branch name to be used for the changes. If not given'
         ' it is constructed automatically and includes the configuration'
         ' type')
parser.add_argument(
    '--interactive',
    dest='interactive',
    action='store_true',
    default=False,
    help='Run interactively: Scripts will prompt for input and changes will '
         'not be committed and pushed automatically.')


args = parser.parse_args()
path = args.path.absolute()

if not (path / '.git').exists():
    raise ValueError('`path` does not point to a git clone of a repository!')
if not (path / '.meta.toml').exists():
    raise ValueError('The repository `path` points to has no .meta.toml!')

with change_dir(path) as cwd_str:
    cwd = pathlib.Path(cwd_str)
    bin_dir = cwd / 'bin'
    meta_cfg = collections.defaultdict(dict, **toml.load('.meta.toml'))
    config_type = meta_cfg['meta']['template']
    branch_name = get_branch_name(args.branch_name, config_type)
    updating = git_branch(branch_name)

    if not args.interactive:
        call(bin_dir / 'bumpversion', '--breaking', '--no-input')
        call(bin_dir / 'addchangelogentry',
            'Drop support for Python 2.7, 3.5, 3.6.', '--no-input')
    else:
        call(bin_dir / 'bumpversion', '--breaking')
        call(bin_dir / 'addchangelogentry',
            'Drop support for Python 2.7, 3.5, 3.6.')
    call(bin_dir / 'check-python-versions',
         '--drop=2.7,3.5,3.6', '--only=setup.py')
    print('Remove legacy Python specific settings from .meta.toml')
    call(os.environ['EDITOR'], '.meta.toml')

    config_package_args = [
        sys.executable,
        'config-package.py',
        path,
        f'--branch={branch_name}',
        '--no-push',
    ]
    if args.interactive:
        config_package_args.append('--no-commit')
    call(*config_package_args, cwd=cwd_str)
    print('Remove `six` from the list of dependencies and other Py 2 things.')
    call(os.environ['EDITOR'], 'setup.py')
    src = path.resolve() / 'src'
    call('find', src, '-name', '*.py', '-exec',
         bin_dir / 'pyupgrade', '--py3-plus', '--py37-plus', '{}', ';')
    call(bin_dir / 'pyupgrade', '--py3-plus', '--py37-plus', 'setup.py')

    excludes = ('--exclude-dir', '__pycache__', '--exclude-dir', '*.egg-info',
                '--exclude', '*.pyc', '--exclude', '*.so')
    print(
        'Replace all remaining `six` mentions or continue if none are listed.')
    call('grep', '-rn', 'six', src, *excludes, allowed_return_codes=(0, 1))
    wait_for_accept()
    print('Replace any remaining code that may support legacy Python 2:')
    call('egrep', '-rn',
         '2.7|3.5|3.6|sys.version|PY2|PY3|Py2|Py3|Python 2|Python 3'
         '|__unicode__|ImportError', src, *excludes,
         allowed_return_codes=(0, 1))
    wait_for_accept()
    tox_path = shutil.which('tox') or (cwd / 'bin' / 'tox')
    call(tox_path, '-p', 'auto')
    if not args.interactive:
        print('Adding, committing and pushing all changes ...')
        call('git', 'add', '.')
        call('git', 'commit', '-m', 'Drop support for Python 2.7 up to 3.6.')
        call('git', 'push', '--set-upstream', 'origin', branch_name)
        if updating:
            print('Updated the previously created PR.')
        else:
            print('If everything went fine up to here:')
            print('Create a PR, using the URL shown above.')
    else:
        print('Applied all changes. Please check and commit manually.')
