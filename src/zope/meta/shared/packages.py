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
import configparser
import itertools
import pathlib

import tomlkit
from packaging.version import parse as parse_version
from tomlkit.toml_document import TOMLDocument


TYPES = ['buildout-recipe', 'c-code', 'pure-python', 'zope-product', 'toolkit']
ORG = 'zopefoundation'
BASE_PATH = pathlib.Path(__file__).parent.parent
OLDEST_PYTHON_VERSION = '3.9'
NEWEST_PYTHON_VERSION = '3.13'
FUTURE_PYTHON_VERSION = '3.14'
PYPY_VERSION = '3.10'
SETUPTOOLS_VERSION_SPEC = '<= 75.6.0'
MANYLINUX_PYTHON_VERSION = '3.11'
MANYLINUX_AARCH64 = 'manylinux2014_aarch64'
MANYLINUX_I686 = 'manylinux2014_i686'
MANYLINUX_X86_64 = 'manylinux2014_x86_64'


def get_pyproject_toml(path: pathlib.Path, comment='') -> TOMLDocument:
    """Parse ``pyproject.toml`` and return its values as ``TOMLDocument``.

    Args:
        path (str, pathlib.Path): Filesystem path to a pyproject.toml file.

    Kwargs:
        comment (str): Optional comment added to the top of the file.

    Returns:
        A TOMLDocument instance from the pyproject.toml file.
    """
    if path.exists():
        with open(path) as fp:
            toml_contents = fp.read()
    else:
        toml_contents = ''

    if comment and not\
       (toml_contents.startswith(comment) or
            toml_contents.startswith(f'# \n{comment}')):
        toml_contents = f'{comment}\n{toml_contents}'

    return tomlkit.loads(toml_contents)


def parse_additional_config(cfg):
    """Attempt to parse "additional-config" data

    "additional-config" sections usually contain ini-style key/value pairs
    packaged into a sequence of lines.

    Returns a mapping of keys and values found
    """
    data = {}

    if cfg:
        parser = configparser.ConfigParser()
        parser.read_string('[dummysection]\n' + '\n'.join(cfg))
        for key, value in parser.items('dummysection'):
            if '\n' in value:
                value = value.split()
            else:
                for func in (parser.getboolean,
                             parser.getint,
                             parser.getfloat):
                    try:
                        value = func('dummysection', key)
                        break
                    except Exception:
                        pass
            data[key] = value

    return data


def supported_python_versions(oldest_version=OLDEST_PYTHON_VERSION,
                              short_version=False):
    """Create a list containing all supported Python versions

    Uses the configured oldest and newest Python versions to compute a list
    containing all versions from oldest to newest that can be iterated over in
    the templates.

    Kwargs:
        oldest_version (str):
            The oldest supported Python version, e.g. '3.9'.

        short_version (bool):
            Return short versions like "313" instead of "3.13". Default False.
    """
    minor_versions = []
    oldest_python = parse_version(oldest_version)
    newest_python = parse_version(NEWEST_PYTHON_VERSION)
    for minor in range(oldest_python.minor, newest_python.minor + 1):
        minor_versions.append(minor)
    supported = [f'{oldest_python.major}.{minor}' for minor in minor_versions]

    if short_version:
        return [x.replace('.', '') for x in supported]

    return supported


def list_packages(path: pathlib.Path) -> list:
    """List the packages in ``path``.

    ``path`` must point to a packages.txt file.
    """
    return [
        p for p in path.read_text().split('\n') if p and not p.startswith('#')
    ]


ALL_REPOS = itertools.chain(
    *[list_packages(BASE_PATH / type / 'packages.txt') for type in TYPES])
