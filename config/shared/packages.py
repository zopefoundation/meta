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
import itertools
import pathlib


TYPES = ['buildout-recipe', 'c-code', 'pure-python', 'zope-product', 'toolkit']
ORG = 'zopefoundation'
BASE_PATH = pathlib.Path(__file__).parent.parent
OLDEST_PYTHON_VERSION = '3.8'
NEWEST_PYTHON_VERSION = '3.12'
SUPPORTED_PYTHON_VERSIONS = [
    f'3.{i}' for i in range(int(OLDEST_PYTHON_VERSION.replace('3.', '')),
                            int(NEWEST_PYTHON_VERSION.replace('3.', '')) + 1)
]
FUTURE_PYTHON_VERSION = '3.13'
PYPY_VERSION = '3.10'
SETUPTOOLS_VERSION_SPEC = '<74'
MANYLINUX_PYTHON_VERSION = '3.11'
MANYLINUX_AARCH64 = 'manylinux2014_aarch64'
MANYLINUX_I686 = 'manylinux2014_i686'
MANYLINUX_X86_64 = 'manylinux2014_x86_64'
PYPROJECT_TOML_DEFAULTS = {
    'build-system': {
        'requires': [f'setuptools{SETUPTOOLS_VERSION_SPEC}'],
        'build-backend': 'setuptools.build_meta',
    },
}


def list_packages(path: pathlib.Path) -> list:
    """List the packages in ``path``.

    ``path`` must point to a packages.txt file.
    """
    return [
        p for p in path.read_text().split('\n') if p and not p.startswith('#')
    ]


ALL_REPOS = itertools.chain(
    *[list_packages(BASE_PATH / type / 'packages.txt') for type in TYPES])
