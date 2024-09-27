#!/usr/bin/env python3
##############################################################################
#
# Copyright (c) 2019 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import argparse
import collections
import pathlib
import shutil
from functools import cached_property

import jinja2
import tomlkit

from .set_branch_protection_rules import set_branch_protection
from .shared.call import abort
from .shared.call import call
from .shared.git import get_branch_name
from .shared.git import get_commit_id
from .shared.git import git_branch
from .shared.packages import FUTURE_PYTHON_VERSION
from .shared.packages import MANYLINUX_AARCH64
from .shared.packages import MANYLINUX_I686
from .shared.packages import MANYLINUX_PYTHON_VERSION
from .shared.packages import MANYLINUX_X86_64
from .shared.packages import NEWEST_PYTHON_VERSION
from .shared.packages import OLDEST_PYTHON_VERSION
from .shared.packages import PYPY_VERSION
from .shared.packages import SETUPTOOLS_VERSION_SPEC
from .shared.packages import get_pyproject_toml_defaults
from .shared.packages import parse_additional_config
from .shared.packages import supported_python_versions
from .shared.path import change_dir


FUTURE_PYTHON_SHORTVERSION = FUTURE_PYTHON_VERSION.replace('.', '')
NEWEST_PYTHON_SHORTVERSION = NEWEST_PYTHON_VERSION.replace('.', '')
META_HINT = """\
# Generated from:
# https://github.com/zopefoundation/meta/tree/master/config/{config_type}"""
META_HINT_MARKDOWN = """\
<!--
Generated from:
https://github.com/zopefoundation/meta/tree/master/config/{config_type}
--> """
DEFAULT = object()


def handle_command_line_arguments():
    """Parse command line options"""
    parser = argparse.ArgumentParser(
        description='Use configuration for a package.')
    parser.add_argument(
        'path', type=pathlib.Path,
        help='path to the repository to be configured')
    parser.add_argument(
        '--commit-msg',
        dest='commit_msg',
        metavar='MSG',
        help='Use MSG as commit message instead of an artificial one.')
    parser.add_argument(
        '--no-commit',
        dest='commit',
        action='store_false',
        default=True,
        help='Prevent automatic committing of changes. Implies --no-push.')
    parser.add_argument(
        '--no-push',
        dest='push',
        action='store_false',
        default=True,
        help='Prevent direct push.')
    parser.add_argument(
        '--with-macos',
        dest='with_macos',
        action='store_true',
        default=False,
        help='Activate running tests on macOS on GitHub Actions, too, if not'
        ' already configured in .meta.toml.')
    parser.add_argument(
        '--with-windows',
        dest='with_windows',
        action='store_true',
        default=False,
        help='Activate running tests on Windows on GitHub Actions, too, if not'
        ' already configured in .meta.toml.')
    parser.add_argument(
        '--with-pypy',
        dest='with_pypy',
        action='store_true',
        default=False,
        help='Activate PyPy support if not already configured in .meta.toml.')
    parser.add_argument(
        '--with-future-python',
        dest='with_future_python',
        action='store_true',
        default=False,
        help='Activate support for a future non-final Python version if not'
        ' already configured in .meta.toml.')
    parser.add_argument(
        '--with-docs',
        # people (me) use --with-sphinx and accidentally
        # get --with-sphinx-doctests
        # so let's make --with-sphinx an alias for --with-docs
        '--with-sphinx',
        dest='with_docs',
        action='store_true',
        default=False,
        help='Activate building docs if not already configured in .meta.toml.')
    parser.add_argument(
        '--with-sphinx-doctests',
        dest='with_sphinx_doctests',
        action='store_true',
        default=False,
        help='Activate running doctests with sphinx '
        'if not already configured in  .meta.toml.')
    parser.add_argument(
        '-t', '--type',
        choices=[
            'buildout-recipe',
            'c-code',
            'pure-python',
            'zope-product',
            'toolkit',
        ],
        default=None,
        dest='type',
        help='type of the configuration to be used, see README.rst. '
        'Only required when running on a repository for the first time.')
    parser.add_argument(
        '--branch',
        dest='branch_name',
        default=None,
        help='Define a git branch name to be used for the changes. '
        'If not given it is constructed automatically and includes '
        'the configuration type')

    args = parser.parse_args()
    return args


def prepend_space(text):
    """Prepend `text` with a space if not empty.

    This prevents trailing whitespace for empty values.
    """
    if text:
        text = f' {text}'
    return text


class PackageConfiguration:
    add_manylinux = False

    def __init__(self, args):
        self.args = args
        self.path = args.path.absolute()
        self.meta_cfg = {}

        if not (self.path / '.git').exists():
            raise ValueError(
                f'{self.path!r} does not point '
                'to a git clone of a repository!')

        self.meta_cfg = self._read_meta_configuration()
        self.meta_cfg['meta']['template'] = self.config_type
        self.meta_cfg['meta']['commit-id'] = get_commit_id()

    def _read_meta_configuration(self):
        """Read and update meta configuration"""
        meta_toml_path = self.path / '.meta.toml'
        if meta_toml_path.exists():
            with open(meta_toml_path, 'rb') as meta_f:
                meta_cfg = tomlkit.load(meta_f)
            meta_cfg = collections.defaultdict(dict, **meta_cfg)
        else:
            meta_cfg = collections.defaultdict(dict)
            if self.args.with_docs is None:
                self.args.with_docs = (self.path / "docs" / "conf.py").exists()
                print(f"Autodetecting --with-docs: {self.args.with_docs}")
        return meta_cfg

    @cached_property
    def config_type(self):
        value = self.meta_cfg['meta'].get('template') or self.args.type
        if value is None:
            raise ValueError(
                'Configuration type not set. '
                'Please use `--type` to select it.')
        return value

    @cached_property
    def config_type_path(self):
        return pathlib.Path(__file__).parent / self.config_type

    @cached_property
    def default_path(self):
        return pathlib.Path(__file__).parent / 'default'

    @cached_property
    def jinja_env(self):
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                [self.config_type_path, self.default_path]),
            variable_start_string='%(',
            variable_end_string=')s',
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @cached_property
    def with_macos(self):
        return self._set_python_config_value('macos')

    @cached_property
    def with_windows(self):
        return self._set_python_config_value('windows')

    @cached_property
    def with_pypy(self):
        return self._set_python_config_value('pypy')

    @cached_property
    def with_future_python(self):
        value = self._set_python_config_value('future-python')

        if not FUTURE_PYTHON_VERSION:
            return 'false'

        return value

    @cached_property
    def with_docs(self):
        return self._set_python_config_value('docs')

    @cached_property
    def with_sphinx_doctests(self):
        return self._set_python_config_value('sphinx-doctests')

    @cached_property
    def coverage_run_source(self):
        return self.meta_cfg['coverage-run'].get('source', self.path.name)

    @cached_property
    def coverage_fail_under(self):
        return self.meta_cfg['coverage'].setdefault('fail-under', 0)

    @cached_property
    def branch_name(self):
        return get_branch_name(self.args.branch_name, self.config_type)

    def _add_project_to_config_type_list(self):
        """Add the current project to packages.txt if it is not there"""
        with open(self.config_type_path / 'packages.txt') as f:
            known_packages = f.read().splitlines()

        if self.path.name in known_packages:
            print(f'{self.path.name} is already configured '
                  'for this config type, updating.')
        else:
            print(f'{self.path.name} is not yet configured '
                  'for this config type, adding.')
            with open(self.config_type_path / 'packages.txt', 'a') as f:
                f.write(f'{self.path.name}\n')

    def _set_python_config_value(self, name, default=False):
        """Get value from either python section in config file or cmd line arg.

        Return the value and store it in `meta_cfg`.
        """
        key = f'with-{name}'
        existing_value = self.meta_cfg['python'].get(key, default)
        arg_value = getattr(self.args, key.replace('-', '_'))
        new_value = existing_value or arg_value
        self.meta_cfg['python'][key] = new_value
        return new_value

    def _clean_up_old_settings(self):
        try:
            del self.meta_cfg['python']['with-legacy-python']
        except KeyError:
            pass

    def setup_cfg(self):
        """Copy setup.cfg file to the package being configured."""
        flake8_additional_config = self.cfg_option(
            'flake8', 'additional-config')
        check_manifest_additional_ign = self.cfg_option(
            'check-manifest', 'additional-ignores')
        check_manifest_ignore_bad_ideas = self.cfg_option(
            'check-manifest', 'ignore-bad-ideas')
        isort_known_third_party = prepend_space(
            self.cfg_option('isort', 'known_third_party',
                            default='docutils, pkg_resources, pytz'))
        isort_known_zope = prepend_space(
            self.cfg_option('isort', 'known_zope', default=''))
        isort_known_first_party = prepend_space(
            self.cfg_option('isort', 'known_first_party', default=''))
        isort_known_local_folder = prepend_space(
            self.meta_cfg['isort'].get('known_local_folder', ''))
        isort_additional_config = self.cfg_option(
            'isort', 'additional-config')

        zest_releaser_options = self.meta_cfg['zest-releaser'].get(
            'options', [])
        if self.config_type == 'c-code':
            zest_releaser_options.append('create-wheel = no')

        self.copy_with_meta(
            'setup.cfg.j2',
            self.path / 'setup.cfg',
            self.config_type,
            flake8_additional_config=flake8_additional_config,
            check_manifest_additional_ignores=check_manifest_additional_ign,
            check_manifest_ignore_bad_ideas=check_manifest_ignore_bad_ideas,
            isort_known_third_party=isort_known_third_party,
            isort_known_zope=isort_known_zope,
            isort_known_first_party=isort_known_first_party,
            isort_known_local_folder=isort_known_local_folder,
            isort_additional_config=isort_additional_config,
            with_docs=self.with_docs,
            with_sphinx_doctests=self.with_sphinx_doctests,
            zest_releaser_options=zest_releaser_options,
        )

    def gitignore(self):
        git_ignore = self.meta_cfg['git'].get('ignore', [])

        self.copy_with_meta(
            'gitignore.j2', self.path / '.gitignore',
            self.config_type,
            git_ignore=git_ignore,
        )

    def pre_commit_config_yaml(self):
        teyit_exclude = self.meta_cfg["pre-commit"].get("teyit-exclude", "")

        self.copy_with_meta(
            "pre-commit-config.yaml.j2",
            self.path / ".pre-commit-config.yaml",
            self.config_type,
            oldest_python_version=OLDEST_PYTHON_VERSION.replace(".", ""),
            teyit_exclude=teyit_exclude,
        )

    def readthedocs(self):
        rtd_build_extra = self.cfg_option(
            'readthedocs', 'build-extra', default=[])
        self.copy_with_meta(
            'readthedocs.yaml.j2',
            self.path / '.readthedocs.yaml',
            self.config_type,
            rtd_build_extra=rtd_build_extra,
        )

    def manylinux_sh(self):
        """Add the scripts to produce binary wheels"""
        manylinux_install_setup = self.meta_cfg['c-code'].get(
            'manylinux-install-setup', [])
        manylinux_aarch64_tests = self.meta_cfg['c-code'].get(
            'manylinux-aarch64-tests', [
                'cd /io/',
                '${PYBIN}/pip install tox',
                'TOXENV=$(tox_env_map "${PYBIN}")',
                '${PYBIN}/tox -e ${TOXENV}',
                'cd ..',
            ])

        if (self.config_type_path / 'manylinux.sh').exists():
            self.copy_with_meta(
                'manylinux.sh', self.path / '.manylinux.sh', self.config_type)
            (self.path / '.manylinux.sh').chmod(0o755)
            stop_at = None
            if not self.with_future_python:
                stop_at = NEWEST_PYTHON_SHORTVERSION
            self.copy_with_meta(
                'manylinux-install.sh.j2', self.path / '.manylinux-install.sh',
                self.config_type,
                package_name=self.path.name,
                manylinux_install_setup=manylinux_install_setup,
                manylinux_aarch64_tests=manylinux_aarch64_tests,
                with_future_python=self.with_future_python,
                future_python_shortversion=FUTURE_PYTHON_SHORTVERSION,
                supported_python_versions=supported_python_versions(
                    short_version=True),
                stop_at=stop_at,
            )
            (self.path / '.manylinux-install.sh').chmod(0o755)
            self.add_manylinux = True

    def cfg_option(self, section, name, default=DEFAULT):
        """Read a value from `self.meta_cfg`, default to `[]` if not existing.
        """
        if default == DEFAULT:
            default = []
        return self.meta_cfg[section].get(name, default)

    def tox_option(self, name, default=DEFAULT):
        """Read a value from the tox options.

        Default not existing ones to `[]`.
        """
        return self.cfg_option('tox', name, default)

    def gh_option(self, name, default=DEFAULT):
        """Read a value from the GitHub actions options.

        Default not existing ones to `[]`.
        """
        return self.cfg_option('github-actions', name, default)

    def tox(self):
        additional_envlist = self.tox_option('additional-envlist')
        testenv_additional = self.tox_option('testenv-additional')
        testenv_additional_extras = self.tox_option(
            'testenv-additional-extras')
        testenv_commands_pre = self.tox_option('testenv-commands-pre')
        testenv_commands = self.tox_option('testenv-commands')
        testenv_setenv = self.tox_option('testenv-setenv')
        coverage_basepython = self.tox_option(
            'coverage-basepython', default='python3')
        coverage_command = self.tox_option('coverage-command')
        if isinstance(coverage_command, str):
            coverage_command = [coverage_command]
        coverage_additional = self.tox_option('coverage-additional')
        testenv_deps = self.tox_option('testenv-deps')
        coverage_setenv = self.tox_option('coverage-setenv')
        coverage_run_additional_config = self.meta_cfg['coverage-run'].get(
            'additional-config', [])
        flake8_additional_sources = self.meta_cfg['flake8'].get(
            'additional-sources', '')
        if flake8_additional_sources:
            # Avoid whitespace at end of line
            # if no additional sources are provided:
            flake8_additional_sources = f' {flake8_additional_sources}'
        isort_additional_sources = self.meta_cfg['isort'].get(
            'additional-sources', '')
        if isort_additional_sources:
            # Avoid whitespace at end of line
            # if no additional sources are provided:
            isort_additional_sources = f' {isort_additional_sources}'
        docs_deps = self.tox_option("docs-deps", default=[])
        self.copy_with_meta(
            'tox.ini.j2',
            self.path / 'tox.ini',
            self.config_type,
            additional_envlist=additional_envlist,
            coverage_additional=coverage_additional,
            coverage_basepython=coverage_basepython,
            coverage_command=coverage_command,
            coverage_run_source=self.coverage_run_source,
            coverage_run_additional_config=coverage_run_additional_config,
            coverage_setenv=coverage_setenv,
            coverage_fail_under=self.coverage_fail_under,
            flake8_additional_sources=flake8_additional_sources,
            isort_additional_sources=isort_additional_sources,
            testenv_additional=testenv_additional,
            testenv_additional_extras=testenv_additional_extras,
            testenv_commands=testenv_commands,
            testenv_commands_pre=testenv_commands_pre,
            testenv_deps=testenv_deps,
            testenv_setenv=testenv_setenv,
            with_docs=self.with_docs,
            with_future_python=self.with_future_python,
            with_pypy=self.with_pypy,
            with_sphinx_doctests=self.with_sphinx_doctests,
            docs_deps=docs_deps,
            setuptools_version_spec=SETUPTOOLS_VERSION_SPEC,
            future_python_shortversion=FUTURE_PYTHON_SHORTVERSION,
            supported_python_versions=supported_python_versions(
                short_version=True),
        )

    def tests_yml(self):
        workflows = self.path / '.github' / 'workflows'
        workflows.mkdir(parents=True, exist_ok=True)

        gha_services = self.gh_option('services')
        gha_additional_config = self.gh_option('additional-config')
        gha_additional_exclude = self.gh_option('additional-exclude')
        gha_steps_before_checkout = self.gh_option('steps-before-checkout')
        gha_additional_install = self.gh_option('additional-install')
        gha_additional_build_deps = self.gh_option(
            'additional-build-dependencies')
        gha_test_environment = self.gh_option('test-environment')
        gha_test_commands = self.gh_option('test-commands')
        require_cffi = self.meta_cfg.get(
            'c-code', {}).get('require-cffi', False)
        py_version_matrix = [
            x for x in zip(supported_python_versions(short_version=False),
                           supported_python_versions(short_version=True))]
        self.copy_with_meta(
            'tests.yml.j2',
            workflows / 'tests.yml',
            self.config_type,
            package_name=self.path.name,
            gha_additional_config=gha_additional_config,
            gha_additional_exclude=gha_additional_exclude,
            gha_additional_install=gha_additional_install,
            gha_additional_build_deps=gha_additional_build_deps,
            gha_test_environment=gha_test_environment,
            gha_test_commands=gha_test_commands,
            gha_services=gha_services,
            gha_steps_before_checkout=gha_steps_before_checkout,
            with_docs=self.with_docs,
            with_sphinx_doctests=self.with_sphinx_doctests,
            with_future_python=self.with_future_python,
            future_python_version=FUTURE_PYTHON_VERSION,
            require_cffi=require_cffi,
            with_pypy=self.with_pypy,
            with_macos=self.with_macos,
            with_windows=self.with_windows,
            manylinux_python_version=MANYLINUX_PYTHON_VERSION,
            manylinux_aarch64=MANYLINUX_AARCH64,
            manylinux_i686=MANYLINUX_I686,
            manylinux_x86_64=MANYLINUX_X86_64,
            pypy_version=PYPY_VERSION,
            setuptools_version_spec=SETUPTOOLS_VERSION_SPEC,
            future_python_shortversion=FUTURE_PYTHON_SHORTVERSION,
            supported_python_versions=py_version_matrix,
        )

    def pre_commit_yml(self):
        workflows = self.path / ".github" / "workflows"
        workflows.mkdir(parents=True, exist_ok=True)

        self.copy_with_meta(
            "pre-commit.yml.j2",
            workflows / "pre-commit.yml",
            self.config_type,
            package_name=self.path.name,
        )

    def manifest_in(self):
        """Modify MANIFEST.in with meta options."""
        manifest_additional_rules = self.meta_cfg['manifest'].get(
            'additional-rules', [])
        if (self.with_docs and 'include *.yaml'
                not in manifest_additional_rules):
            manifest_additional_rules.insert(0, 'include *.yaml')
        if self.config_type == 'c-code' \
                and 'include *.sh' not in manifest_additional_rules:
            manifest_additional_rules.insert(0, 'include *.sh')
        if self.config_type != 'toolkit':
            self.copy_with_meta(
                'MANIFEST.in.j2', self.path / 'MANIFEST.in', self.config_type,
                manifest_additional_rules=manifest_additional_rules,
                with_docs=self.with_docs)

    def pyproject_toml(self):
        """Modify pyproject.toml with meta options."""
        toml_path = self.path / 'pyproject.toml'

        if toml_path.exists():
            with open(toml_path, 'rb') as fp:
                toml_doc = tomlkit.load(fp)
        else:
            toml_doc = tomlkit.document()
            preamble = f'\n{META_HINT.format(config_type=self.config_type)}'
            toml_doc.add(tomlkit.comment(preamble))
        toml_data = collections.defaultdict(dict, **toml_doc)

        # Capture some pre-transformation data
        old_requires = toml_data['build-system'].get('requires', [])

        # Apply template-dependent defaults
        toml_data.update(get_pyproject_toml_defaults(self.config_type))

        # Create or update section "build-system"
        if old_requires:
            setuptools_requirement = [
                x for x in old_requires if x.startswith('setuptools')]
            for setuptools_req in setuptools_requirement:
                old_requires.remove(setuptools_req)
            toml_data['build-system']['requires'].extend(old_requires)

        # Update coverage-related data
        coverage = toml_data['tool']['coverage']
        coverage['run']['source'] = self.coverage_run_source.split()
        coverage['report']['fail_under'] = self.coverage_fail_under
        add_cfg = self.meta_cfg['coverage-run'].get('additional-config', [])
        for key, value in parse_additional_config(add_cfg).items():
            coverage['run'][key] = value

        # Remove empty sections
        toml_data = {k: v for k, v in toml_data.items() if v}

        # Update and write out the document
        toml_doc.update(toml_data)
        with open(toml_path, 'w') as fp:
            tomlkit.dump(toml_doc, fp, sort_keys=True)

    def copy_with_meta(
            self, template_name, destination, config_type,
            meta_hint=META_HINT, **kw):
        """Copy the source file to destination and a hint of origin.

        If kwargs are given they are used as template arguments.
        """
        template = self.jinja_env.get_template(template_name)
        rendered = template.render(config_type=config_type, **kw)
        meta_hint = meta_hint.format(config_type=config_type)
        if rendered.startswith('#!'):
            she_bang, _, body = rendered.partition('\n')
            content = '\n'.join([she_bang, meta_hint, body])
        else:
            content = '\n'.join([meta_hint, rendered])

        with open(destination, 'w') as f_:
            f_.write(content)

    def configure(self):
        self._add_project_to_config_type_list()
        self._clean_up_old_settings()

        if self.with_sphinx_doctests and not self.with_docs:
            print("The package is configured without sphinx docs, "
                  "but with sphinx doctests.  Is this a mistake?")

        if self.with_docs:
            self.readthedocs()

        self.pyproject_toml()
        self.setup_cfg()
        self.gitignore()
        self.pre_commit_config_yaml()
        self.copy_with_meta(
            'editorconfig.txt', self.path / '.editorconfig', self.config_type)
        self.copy_with_meta(
            'CONTRIBUTING.md', self.path / 'CONTRIBUTING.md', self.config_type,
            meta_hint=META_HINT_MARKDOWN)

        with change_dir(self.path):
            # We have to add it here otherwise the linter complains
            # that it is not added.
            early_add = [
                '.pre-commit-config.yaml',
                'CONTRIBUTING.md',
                'pyproject.toml',
            ]
            if self.args.commit:
                call('git', 'add', *early_add)

        self.manylinux_sh()
        self.tox()
        self.tests_yml()
        self.pre_commit_yml()
        self.manifest_in()

        with change_dir(self.path) as cwd:
            if pathlib.Path('bootstrap.py').exists():
                call('git', 'rm', 'bootstrap.py')
            if pathlib.Path('.travis.yml').exists():
                call('git', 'rm', '.travis.yml')
            if pathlib.Path('.coveragerc').exists():
                call('git', 'rm', '.coveragerc')
            if pathlib.Path('appveyor.yml').exists():
                call('git', 'rm', 'appveyor.yml')
            if self.with_docs and self.args.commit:
                call('git', 'add', '.readthedocs.yaml')
            if self.add_manylinux and self.args.commit:
                call('git', 'add', '.manylinux.sh', '.manylinux-install.sh')
            # Remove empty sections:
            meta_cfg = {k: v for k, v in self.meta_cfg.items() if v}
            with open('.meta.toml', 'w') as meta_f:
                meta_f.write(META_HINT.format(config_type=self.config_type))
                meta_f.write('\n')
                tomlkit.dump(meta_cfg, meta_f)

            tox_path = shutil.which('tox') or (
                pathlib.Path(cwd) / 'bin' / 'tox')
            call(tox_path, '-p', 'auto')

            updating = git_branch(self.branch_name)

            if not self.coverage_fail_under:
                print(
                    'In .meta.toml in section [coverage] the option '
                    '"fail-under" is  0. Please enter a valid minimum '
                    'coverage and rerun.')
                abort(1)
            to_add = [
                ".editorconfig",
                ".github/workflows/tests.yml",
                ".github/workflows/pre-commit.yml",
                ".gitignore",
                ".meta.toml",
                "setup.cfg",
                "tox.ini",
            ]
            if self.config_type != 'toolkit':
                to_add.append('MANIFEST.in')
            if self.args.commit:
                call('git', 'add', *to_add)
                if self.args.commit_msg:
                    commit_msg = self.args.commit_msg
                else:
                    commit_msg = f'Configuring for {self.config_type}'
                call('git', 'commit', '-m', commit_msg)
                if self.args.push:
                    call('git', 'push', '--set-upstream',
                         'origin', self.branch_name)
            print()
            print('If you are an admin and are logged in via `gh auth login`')
            print('update branch protection rules? (y/N)?', end=' ')
            if input().lower() == 'y':
                remote_url = call(
                    'git', 'config', '--get', 'remote.origin.url',
                    capture_output=True).stdout.strip()
                package_name = remote_url.rsplit('/')[-1].removesuffix('.git')
                success = set_branch_protection(
                    package_name, self.path / '.meta.toml')
                if success:
                    print('Successfully updated branch protection rules.')
                else:
                    abort(-1)
            print()
            print('If everything went fine up to here:')
            if updating:
                print('Updated the previously created PR.')
            else:
                print('Create a PR, using the URL shown above.')


def main():
    args = handle_command_line_arguments()

    package = PackageConfiguration(args)
    package.configure()
