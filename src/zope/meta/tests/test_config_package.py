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


TEMPLATES = pathlib.Path(__file__).parent.parent


def render(template_name, **context):
    """Render one of the shipped templates the way `config-package` does."""
    from zope.meta.config_package import make_jinja_env

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

DEFAULT_TEST_COMMAND = (
    '      run: uvx --with tox-uv tox -e ${{ matrix.config[1] }}\n')
COMBINE_TEST_COMMAND = """\
        uvx --with tox-uv tox ${{ matrix.config[1] == 'coverage' \
&& '--skip-env "(docs|lint|release-check)"' \
|| format('-e {0}', matrix.config[1]) }}
"""


class ConfigPackageTests(unittest.TestCase):

    def test_prepend_space(self):
        from zope.meta.config_package import prepend_space

        self.assertIsNone(prepend_space(None))
        self.assertEqual('', prepend_space(''))
        self.assertEqual(' foobar', prepend_space('foobar'))


class CombinedCoverageTests(unittest.TestCase):
    """Tests for the ``[coverage] combine`` option."""

    def test_combined_coverage_envs(self):
        from zope.meta.config_package import combined_coverage_envs

        self.assertEqual(['py310', 'py311'],
                         combined_coverage_envs(['310', '311']))

    def test_combined_coverage_envs__all_variants(self):
        from zope.meta.config_package import FUTURE_PYTHON_SHORTVERSION
        from zope.meta.config_package import NEWEST_PYTHON_SHORTVERSION_T
        from zope.meta.config_package import combined_coverage_envs

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

    def test_prepend_coverage_file(self):
        from zope.meta.config_package import prepend_coverage_file

        self.assertEqual(['COVERAGE_FILE=.coverage'],
                         prepend_coverage_file([], '.coverage'))
        self.assertEqual(['COVERAGE_FILE=.coverage', 'FOO=bar'],
                         prepend_coverage_file(['FOO=bar'], '.coverage'))

    def test_prepend_coverage_file__keeps_configured_value(self):
        from zope.meta.config_package import prepend_coverage_file

        self.assertEqual(
            ['COVERAGE_FILE=elsewhere'],
            prepend_coverage_file(['COVERAGE_FILE=elsewhere'], '.coverage'))

    def test_skip_env_regex(self):
        from zope.meta.config_package import skip_env_regex

        self.assertEqual('(docs|lint|release-check)', skip_env_regex())
        self.assertEqual('(lint|release-check)', skip_env_regex(False))

    def test_tox_ini__coverage_env_combines(self):
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

    def test_tox_ini__coverage_env_measures_by_default(self):
        tox_ini = render('tox.ini.j2', **TOX_CONTEXT)
        coverage_env = tox_ini.split('[testenv:coverage]')[1]

        self.assertIn(
            '    coverage run -m zope.testrunner --test-path=src'
            ' {posargs:-vc}\n',
            coverage_env)
        self.assertNotIn('coverage combine', coverage_env)
        self.assertNotIn('depends', coverage_env)

    def test_tests_yml__coverage_job_runs_the_test_envs(self):
        tests_yml = render('tests.yml.j2',
                           **dict(TESTS_YML_CONTEXT, coverage_combine=True))

        self.assertIn(COMBINE_TEST_COMMAND, tests_yml)
        self.assertNotIn(DEFAULT_TEST_COMMAND, tests_yml)

    def test_tests_yml__test_command_unchanged_by_default(self):
        tests_yml = render('tests.yml.j2', **TESTS_YML_CONTEXT)

        self.assertIn(DEFAULT_TEST_COMMAND, tests_yml)
        self.assertNotIn('--skip-env', tests_yml)

    def test_tests_yml__explicit_test_commands_win(self):
        tests_yml = render('tests.yml.j2', **dict(
            TESTS_YML_CONTEXT,
            coverage_combine=True,
            gha_test_commands=['make test'],
        ))

        self.assertIn('      run: |\n        make test\n', tests_yml)
        self.assertNotIn('--skip-env', tests_yml)
