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


TYPES = ['buildout-recipe', 'c-code', 'pure-python', 'zope-product', 'toolkit']
ORG = 'zopefoundation'
BASE_PATH = pathlib.Path(__file__).parent.parent
OLDEST_PYTHON_VERSION = '3.8'
NEWEST_PYTHON_VERSION = '3.13'
SUPPORTED_PYTHON_VERSIONS = [
    f'3.{i}' for i in range(int(OLDEST_PYTHON_VERSION.replace('3.', '')),
                            int(NEWEST_PYTHON_VERSION.replace('3.', '')) + 1)
]
FUTURE_PYTHON_VERSION = '3.14'
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
    'tool': {
        'coverage': {
            'run': {
                'branch': True,
                'source': 'src',
            },
            'report': {
                'fail_under': 0,
                'precision': 2,
                'ignore_errors': True,
                'show_missing': True,
                'exclude_lines': ['pragma: no cover',
                                  'pragma: nocover',
                                  'except ImportError:',
                                  'raise NotImplementedError',
                                  "if __name__ == '__main__':",
                                  'self.fail',
                                  'raise AssertionError',
                                  'raise unittest.Skip',
                                  ],
            },
            'html': {
                'directory': 'parts/htmlcov',
            },
        },
    },

}
PYPROJECT_TOML_OVERRIDES = {
    'buildout-recipe': {
        'tool': {
            'coverage': {
                'run': {
                    'parallel': True,
                },
                'paths': {
                    'source': ['src/',
                               '.tox/*/lib/python*/site-packages/',
                               '.tox/pypy*/site-packages/',
                               ],
                },
            },
        },
    },
    'c-code': {
        'tool': {
            'coverage': {
                'run': {
                    'relative_files': True,
                },
                'paths': {
                    'source': ['src/',
                               '.tox/*/lib/python*/site-packages/',
                               '.tox/pypy*/site-packages/',
                               ],
                },
            },
        },
    },
}


def get_pyproject_toml_defaults(template_name):
    """ Get pyproject.toml default data for a given template name"""
    return merge_dicts(PYPROJECT_TOML_DEFAULTS,
                       PYPROJECT_TOML_OVERRIDES.get(template_name, {}))


def merge_dicts(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and \
           isinstance(dict1[key], dict) and \
           isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = merge_dicts(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1


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


def list_packages(path: pathlib.Path) -> list:
    """List the packages in ``path``.

    ``path`` must point to a packages.txt file.
    """
    return [
        p for p in path.read_text().split('\n') if p and not p.startswith('#')
    ]


ALL_REPOS = itertools.chain(
    *[list_packages(BASE_PATH / type / 'packages.txt') for type in TYPES])
