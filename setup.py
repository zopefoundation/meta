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
"""Setup for zope.meta package
"""

import os

from setuptools import find_packages
from setuptools import setup


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as stream:
        return stream.read()


setup(
    name='zope.meta',
    version='1.0',
    author='Zope Foundation and Contributors',
    author_email='zope-dev@zope.dev',
    description='Helper functions for package management',
    long_description=(
        read('README.rst')
        + '\n\n' +
        read('CHANGES.rst')
    ),
    long_description_content_type='text/x-rst',
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
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
    license='ZPL 2.1',
    url='https://github.com/zopefoundation/meta',
    project_urls={
        'Documentation': 'https://zopemeta.readthedocs.io',
        'Issue Tracker': 'https://github.com/zopefoundation/meta/issues',
        'Sources': 'https://github.com/zopefoundation/meta',
    },
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['zope'],
    install_requires=[
        'setuptools',
        'check-python-versions',
        'Jinja2',
        'packaging',
        'pyupgrade',
        'requests',
        'tomlkit',
        'tox',
        'zest.releaser',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'test': ['zope.testrunner'],
        'docs': ['Sphinx', 'furo'],
    },
    entry_points={
        'console_scripts': [
            'config-package=zope.meta.config_package:main',
            'multi-call=zope.meta.multi_call:main',
            're-enable-actions=zope.meta.re_enable_actions:main',
            (
                'set-branch-protection-rules='
                'zope.meta.set_branch_protection_rules:main'
            ),
            'update-python-support=zope.meta.update_python_support:main',
        ],
    },
)
