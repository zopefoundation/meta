#!/usr/bin/env python3
from configparser import ConfigParser
from shared.call import call
from shared.path import change_dir
from shared.toml_encoder import TomlArraySeparatorEncoderWithNewline
import argparse
import collections
import os
import pathlib
import sys
import toml


def path_factory(parameter_name, *, has_extension=None, is_dir=False):
    """Return factory creating pathlib.Path object if requirements are matched.

    The factory raises an exception otherwise.
    """
    def factory(str):
        path = pathlib.Path(str)
        if not path.exists():
            raise argparse.ArgumentTypeError(f'{str!r} does not exist!')
        if has_extension is not None and path.suffix != has_extension:
            raise argparse.ArgumentTypeError(
                f'The required extension is {has_extension!r}'
                f' not {path.suffix!r}.')
        if is_dir and not path.is_dir():
            raise argparse.ArgumentTypeError('has to point to a directory!')
        return path
    return factory


parser = argparse.ArgumentParser(
    description='Call a script on all repositories listed in a packages.txt.',
    epilog='Additional optional arguments are passed directly to the script.')
parser.add_argument(
    'script', type=path_factory('script', has_extension='.py'),
    help='path to the Python script to be called')
parser.add_argument(
    'packages_txt', type=path_factory('packages.txt', has_extension='.txt'),
    help='path to the packages.txt; script is called on each repository listed'
         ' inside', metavar='packages.txt')
parser.add_argument(
    'clones', type=path_factory('clones', is_dir=True),
    help='path to the directory where the clones of the repositories are'
         ' stored')

# idea from https://stackoverflow.com/a/37367814/8531312
args, sub_args = parser.parse_known_args()

packages = [
    p
    for p in args.packages_txt.read_text().split('\n')
    if p and not p.startswith('#')
]

for package in packages:
    print(f'*** Running {args.script.name} on {package} ***')
    if (args.clones / package).exists():
        with change_dir(args.clones / package):
            print('Updating existing checkout …')
            call('git', 'restore', '.')
            call('git', 'checkout', 'master')
            call('git', 'pull')
    else:
        with change_dir(args.clones):
            print('Cloning repository …')
            call('git', 'clone',
                 f'https://github.com/zopefoundation/{package}')

    call_args = [
        sys.executable,
        args.script,
        args.clones / package
    ]
    call_args.extend(sub_args)
    call(*call_args)
