##############################################################################
#
# Copyright (c) 2025 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import tempfile
import textwrap
import unittest

from zope.meta.shared.path import change_dir
from zope.meta.update_python_support import get_declared_python_versions
from zope.meta.update_python_support import get_tox_ini_python_versions


class TestUpdatePythonSupport(unittest.TestCase):

    def test_update_python_support__get_tox_ini_python_versions__1(self):
        """It filters out c-code pure versions and custom versions."""

        with tempfile.NamedTemporaryFile(mode='w') as tox_ini:
            tox_ini.write(textwrap.dedent("""
                [tox]
                minversion = 4.0
                envlist =
                    lint
                    py39,py39-pure
                    py310,py310-pure
                    py311,py311-pure
                    pypy3
                    docs
                    coverage
                    py39-watch, py311-watch
                """))
            tox_ini.flush()
            versions = get_tox_ini_python_versions(tox_ini.name)
            self.assertEqual({'3.9', '3.10', '3.11'}, versions)

    def test_update_python_support__get_tox_ini_python_versions__2(self):
        """It filters out free-threaded Python versions."""

        with tempfile.NamedTemporaryFile(mode='w') as tox_ini:
            tox_ini.write(textwrap.dedent("""
                [tox]
                minversion = 4.0
                envlist =
                    lint
                    py313,py313-pure
                    py314,py314-pure
                    py314t,py314t-pure
                    pypy3
                    docs
                    coverage
                """))
            tox_ini.flush()
            versions = get_tox_ini_python_versions(tox_ini.name)
            self.assertEqual({'3.13', '3.14'}, versions)

    def test_update_python_support__get_tox_ini_python_versions__3(self):
        """It ignores factor envs using curly braces."""

        with tempfile.NamedTemporaryFile(mode='w') as tox_ini:
            tox_ini.write(textwrap.dedent("""
                [tox]
                minversion = 4.0
                envlist =
                    lint
                    py313
                    py314
                    pypy3
                    py{313}-sqlalchemy{12,13}
                    py{313,314,py3}-subunit
                """))
            tox_ini.flush()
            versions = get_tox_ini_python_versions(tox_ini.name)
            self.assertEqual({'3.13', '3.14'}, versions)

    def test_update_python_support__get_declared_python_versions__1(self):
        """It returns the versions declared in `pyproject.toml`."""

        with tempfile.TemporaryDirectory() as tmpdir, change_dir(tmpdir):
            with open('pyproject.toml', 'w') as pyproject_toml:
                pyproject_toml.write(textwrap.dedent("""
                    [project]
                    classifiers = [
                        "Programming Language :: Python :: 3.13",
                        "Programming Language :: Python :: 3.14",
                    ]
                    """))
            versions = get_declared_python_versions()
        self.assertEqual({'3.13', '3.14'}, versions)

    def test_update_python_support__get_declared_python_versions__2(self):
        """It returns an empty set if there is no package metadata."""

        with tempfile.TemporaryDirectory() as tmpdir, change_dir(tmpdir):
            versions = get_declared_python_versions()
        self.assertEqual(set(), versions)
