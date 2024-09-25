##############################################################################
#
# Copyright (c) 2024 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Setup for zope.metalib package
"""

import os

from setuptools import find_packages
from setuptools import setup


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as stream:
        return stream.read()


setup(
    name='zope.metalib',
    version='1.0.dev0',
    author='Zope Foundation and Contributors',
    author_email='zope-dev@zope.org',
    description='Helper functions for package management',
    long_description=(
        read('README.rst')
        + '\n\n' +
        read('CHANGES.rst')
    ),
    keywords="zope packaging",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
    license='ZPL 2.1',
    url='https://github.com/zopefoundation/zope.metalib',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['zope'],
    install_requires=[
        'setuptools',
        'Jinja2',
        'packaging',
        'pyupgrade',
        'requests',
        'tomlkit',
        'zest.releaser',
        ],
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'test': ['zope.testrunner'],
        'docs': ['Sphinx', 'sphinx_rtd_theme'],
    },
)
