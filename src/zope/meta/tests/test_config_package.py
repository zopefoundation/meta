##############################################################################
#
# Copyright (c) 2024 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import pathlib
import unittest

from zope.meta.config_package import FUTURE_PYTHON_SHORTVERSION
from zope.meta.config_package import NEWEST_PYTHON_SHORTVERSION_T
from zope.meta.config_package import combined_coverage_envs
from zope.meta.config_package import make_jinja_env
from zope.meta.config_package import prepend_coverage_file
from zope.meta.config_package import prepend_space
from zope.meta.config_package import skip_env_regex


TEMPLATES = pathlib.Path(__file__).parent.parent


def render(template_name, **context):
    """Render one of the shipped templates the way `config-package` does."""
    env = make_jinja_env([TEMPLATES / context['config_type'],
                          TEMPLATES / 'default'])
    return env.get_template(template_name).render(**context)


#: A `pure-python` package with docs, Sphinx doctests and a future Python,
#: i. e. the values `PackageConfiguration.tox()` passes to `tox.ini.j2`.
TOX_CONTEXT = {
    'additional_envlist': [],
    'build_requirements': ['setuptools >= 78.1.1,< 82'],
    'config_type': 'pure-python',
    'coverage_additional': [],
    'coverage_basepython': 'python3',
    'coverage_command': [],
    'coverage_setenv': [],
    'docs_deps': [],
    'flake8_additional_sources': '',
    'future_python_shortversion': '315',
    'isort_additional_sources': '',
    'lint_diff_on_failure': True,
    'newest_python_shortversion_t': '314t',
    'setuptools_version_spec': '>= 78.1.1,< 82',
    'supported_python_versions': ['310', '311'],
    'testenv_additional': [],
    'testenv_additional_extras': [],
    'testenv_commands': [],
    'testenv_commands_pre': [],
    'testenv_deps': [],
    'testenv_setenv': [],
    'testenv_skip_test_extra': False,
    'with_docs': True,
    'with_free_threaded_python': False,
    'with_future_python': True,
    'with_pypy': False,
    'with_sphinx_doctests': True,
}

#: The same package as `TOX_CONTEXT`, for `tests.yml.j2`.
TESTS_YML_CONTEXT = {
    'config_type': 'pure-python',
    'coverage_combine': False,
    'future_python_shortversion': '315',
    'future_python_version': '3.15',
    'gha_additional_config': [],
    'gha_additional_exclude': [],
    'gha_additional_install': [],
    'gha_services': [],
    'gha_skip_env_regex': '(docs|lint|release-check)',
    'gha_steps_before_checkout': [],
    'gha_test_commands': [],
    'gha_test_environment': [],
    'newest_python_shortversion': '314',
    'newest_python_shortversion_t': '314t',
    'newest_python_version': '3.14',
    'package_name': 'testpackage',
    'pypy_version': '3.11',
    'setuptools_version_spec': '>= 78.1.1,< 82',
    'supported_python_versions': [('3.10', '310'), ('3.11', '311')],
    'use_trusted_publishing': False,
    'with_docs': True,
    'with_free_threaded_python': False,
    'with_future_python': True,
    'with_macos': False,
    'with_pypy': False,
    'with_sphinx_doctests': True,
    'with_windows': False,
}

#: The values `PackageConfiguration.pre_commit_config_yaml()` passes to
#: `pre-commit-config.yaml.j2`.
PRE_COMMIT_CONTEXT = {
    'config_type': 'pure-python',
    'oldest_python_version': '310',
    'pre_commit_additional_config': [],
    'pyupgrade_exclude': '',
    'teyit_exclude': '',
}

DEFAULT_TEST_COMMAND = (
    '      run: uvx --with tox-uv tox -e ${{ matrix.config[1] }}\n')
COMBINE_TEST_COMMAND = """\
        uvx --with tox-uv tox ${{ matrix.config[1] == 'coverage' \
&& '--skip-env "(docs|lint|release-check)"' \
|| format('-e {0}', matrix.config[1]) }}
"""


class ConfigPackageTests(unittest.TestCase):

    def test_config_package__prepend_space__1(self):
        """It prepends a space to a non-empty text."""

        self.assertIsNone(prepend_space(None))
        self.assertEqual('', prepend_space(''))
        self.assertEqual(' foobar', prepend_space('foobar'))


class PreCommitAdditionalConfigTests(unittest.TestCase):
    """Tests for the ``[pre-commit] additional-config`` option."""

    def test_config_package__pre_commit_config_yaml__1(self):
        """It appends the configured repositories to the ``repos`` list."""

        config = render('pre-commit-config.yaml.j2', **dict(
            PRE_COMMIT_CONTEXT,
            pre_commit_additional_config=[
                '- repo: https://github.com/pre-commit/mirrors-mypy',
                '  rev: v2.1.0',
                '  hooks:',
                '    - id: mypy',
                '      pass_filenames: false',
            ],
        ))

        self.assertTrue(config.endswith(
            '  - repo: https://github.com/pre-commit/mirrors-mypy\n'
            '    rev: v2.1.0\n'
            '    hooks:\n'
            '      - id: mypy\n'
            '        pass_filenames: false\n'))

    def test_config_package__pre_commit_config_yaml__2(self):
        """It renders no additional lines by default."""

        config = render('pre-commit-config.yaml.j2', **PRE_COMMIT_CONTEXT)

        self.assertTrue(config.endswith(
            '        - flake8-debugger == 4.1.2\n'))


class CombinedCoverageTests(unittest.TestCase):
    """Tests for the ``[coverage] combine`` option."""

    def test_config_package__combined_coverage_envs__1(self):
        """It returns one environment per supported Python version."""

        self.assertEqual(['py310', 'py311'],
                         combined_coverage_envs(['310', '311']))

    def test_config_package__combined_coverage_envs__2(self):
        """It appends future, free-threaded, PyPy and additional envs."""

        self.assertEqual(
            ['py310',
             f'py{FUTURE_PYTHON_SHORTVERSION}',
             f'py{NEWEST_PYTHON_SHORTVERSION_T}',
             'pypy3',
             'py311-datetime'],
            combined_coverage_envs(
                ['310'],
                ['py311-datetime'],
                with_future_python=True,
                with_free_threaded_python=True,
                with_pypy=True))

    def test_config_package__prepend_coverage_file__1(self):
        """It prepends the ``COVERAGE_FILE`` entry."""

        self.assertEqual(['COVERAGE_FILE=.coverage'],
                         prepend_coverage_file([], '.coverage'))
        self.assertEqual(['COVERAGE_FILE=.coverage', 'FOO=bar'],
                         prepend_coverage_file(['FOO=bar'], '.coverage'))

    def test_config_package__prepend_coverage_file__2(self):
        """It keeps a ``COVERAGE_FILE`` the package configured itself."""

        self.assertEqual(
            ['COVERAGE_FILE=elsewhere'],
            prepend_coverage_file(['COVERAGE_FILE=elsewhere'], '.coverage'))

    def test_config_package__skip_env_regex__1(self):
        """It matches the environments contributing no coverage data."""

        self.assertEqual('(docs|lint|release-check)', skip_env_regex())
        self.assertEqual('(lint|release-check)', skip_env_regex(False))

    def test_config_package__tox_ini__1(self):
        """It renders a coverage environment combining the data files."""

        tox_ini = render('tox.ini.j2', **dict(
            TOX_CONTEXT,
            coverage_additional=['depends = py310,py311'],
            coverage_command=['coverage erase', 'coverage combine'],
            coverage_setenv=['COVERAGE_FILE=.coverage'],
            testenv_setenv=['COVERAGE_FILE=.coverage.{envname}'],
        ))
        testenv, coverage_env = tox_ini.split('[testenv:coverage]')

        self.assertIn('setenv =\n    COVERAGE_FILE=.coverage.{envname}\n',
                      testenv)
        self.assertIn('setenv =\n    COVERAGE_FILE=.coverage\n', coverage_env)
        self.assertIn('    coverage erase\n    coverage combine\n',
                      coverage_env)
        self.assertIn('\ndepends = py310,py311\n', coverage_env)

    def test_config_package__tox_ini__2(self):
        """It renders a coverage environment measuring by default."""

        tox_ini = render('tox.ini.j2', **TOX_CONTEXT)
        coverage_env = tox_ini.split('[testenv:coverage]')[1]

        self.assertIn(
            '    coverage run -m zope.testrunner --test-path=src'
            ' {posargs:-vc}\n',
            coverage_env)
        self.assertNotIn('coverage combine', coverage_env)
        self.assertNotIn('depends', coverage_env)

    def test_config_package__tests_yml__1(self):
        """It runs the test environments in the coverage job."""

        tests_yml = render('tests.yml.j2',
                           **dict(TESTS_YML_CONTEXT, coverage_combine=True))

        self.assertIn(COMBINE_TEST_COMMAND, tests_yml)
        self.assertNotIn(DEFAULT_TEST_COMMAND, tests_yml)

    def test_config_package__tests_yml__2(self):
        """It leaves the test command unchanged if combining is off."""

        tests_yml = render('tests.yml.j2', **TESTS_YML_CONTEXT)

        self.assertIn(DEFAULT_TEST_COMMAND, tests_yml)
        self.assertNotIn('--skip-env', tests_yml)

    def test_config_package__tests_yml__3(self):
        """It prefers the test commands configured by the package."""

        tests_yml = render('tests.yml.j2', **dict(
            TESTS_YML_CONTEXT,
            coverage_combine=True,
            gha_test_commands=['make test'],
        ))

        self.assertIn('      run: |\n        make test\n', tests_yml)
        self.assertNotIn('--skip-env', tests_yml)
