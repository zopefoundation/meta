#!/usr/bin/env python3
from functools import cached_property
from shared.call import abort
from shared.call import call
from shared.git import get_branch_name
from shared.git import get_commit_id
from shared.git import git_branch
from shared.path import change_dir
from shared.toml_encoder import TomlArraySeparatorEncoderWithNewline
import argparse
import collections
import jinja2
import pathlib
import shutil
import toml


META_HINT = """\
# Generated from:
# https://github.com/zopefoundation/meta/tree/master/config/{config_type}"""
META_HINT_MARKDOWN = """\
<!--
Generated from:
https://github.com/zopefoundation/meta/tree/master/config/{config_type}
--> """
FUTURE_PYTHON_VERSION = "3.12.0-beta.4"
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
        '--no-flake8',
        dest='use_flake8',
        action='store_false',
        default=None,
        help='Do not include flake8 and isort in the linting configuration.')
    parser.add_argument(
        '--with-appveyor',
        dest='with_appveyor',
        action='store_true',
        default=None,
        help='Activate running tests on AppVeyor, too, '
        'if not already configured in .meta.toml.')
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
        default=None,
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
            'groktoolkit',
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
    """Prepend `text` which a space if not empty.

    This prevents trailing whitespace for empty values.
    """
    if text:
        text = f' {text}'
    return text


class PackageConfiguration:
    add_coveragerc = False
    rm_coveragerc = False
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
            meta_cfg = toml.load(meta_toml_path)
            meta_cfg = collections.defaultdict(dict, **meta_cfg)
        else:
            meta_cfg = collections.defaultdict(dict)
            if self.args.with_docs is None:
                self.args.with_docs = (self.path / "docs" / "conf.py").exists()
                print(f"Autodetecting --with-docs: {self.args.with_docs}")
            if self.args.with_appveyor is None:
                value = (self.path / "appveyor.yml").exists()
                self.args.with_appveyor = value
                print(f"Autodetecting --with-appveyor: {value}")
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
    def with_appveyor(self):
        return self._set_python_config_value('appveyor')

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
        return self._set_python_config_value('future-python')

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
    def fail_under(self):
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
        extra_flake8_config = self.cfg_option(
            'flake8', 'additional-config')
        extra_check_manifest_ignores = self.cfg_option(
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

        zest_releaser_options = self.meta_cfg['zest-releaser'].get(
            'options', [])
        if self.config_type == 'c-code':
            zest_releaser_options.append('create-wheel = no')

        self.copy_with_meta(
            'setup.cfg.j2',
            self.path / 'setup.cfg',
            self.config_type,
            additional_flake8_config=extra_flake8_config,
            additional_check_manifest_ignores=extra_check_manifest_ignores,
            check_manifest_ignore_bad_ideas=check_manifest_ignore_bad_ideas,
            isort_known_third_party=isort_known_third_party,
            isort_known_zope=isort_known_zope,
            isort_known_first_party=isort_known_first_party,
            isort_known_local_folder=isort_known_local_folder,
            with_docs=self.with_docs,
            with_sphinx_doctests=self.with_sphinx_doctests,
            zest_releaser_options=zest_releaser_options,
        )

    def gitignore(self):
        git_ignore = self.meta_cfg['git'].get('ignore', [])

        self.copy_with_meta(
            'gitignore.j2', self.path / '.gitignore',
            self.config_type,
            ignore=git_ignore,
        )

    def coveragerc(self):
        coverage_run_additional_config = self.meta_cfg['coverage-run'].get(
            'additional-config', [])
        if (self.config_type_path / 'coveragerc.j2').exists():
            self.copy_with_meta(
                'coveragerc.j2',
                self.path / '.coveragerc',
                self.config_type,
                coverage_run_source=self.coverage_run_source,
                run_additional_config=coverage_run_additional_config,
            )
            self.add_coveragerc = True
        elif (self.path / '.coveragerc').exists():
            self.rm_coveragerc = True

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
            self.copy_with_meta(
                'manylinux-install.sh.j2', self.path / '.manylinux-install.sh',
                self.config_type,
                package_name=self.path.name,
                setup=manylinux_install_setup,
                aarch64_tests=manylinux_aarch64_tests,
                with_future_python=self.with_future_python,
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
        if self.args.use_flake8 is None:
            use_flake8 = self.tox_option('use-flake8', default=True)
        else:
            use_flake8 = self.args.use_flake8
        self.meta_cfg['tox']['use-flake8'] = use_flake8
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
            fail_under=self.fail_under,
            flake8_additional_sources=flake8_additional_sources,
            isort_additional_sources=isort_additional_sources,
            testenv_additional=testenv_additional,
            testenv_additional_extras=testenv_additional_extras,
            testenv_commands=testenv_commands,
            testenv_commands_pre=testenv_commands_pre,
            testenv_deps=testenv_deps,
            testenv_setenv=testenv_setenv,
            use_flake8=use_flake8,
            with_docs=self.with_docs,
            with_future_python=self.with_future_python,
            with_pypy=self.with_pypy,
            with_sphinx_doctests=self.with_sphinx_doctests,
            with_config_type=self.config_type,
        )

    def tests_yml(self):
        workflows = self.path / '.github' / 'workflows'
        workflows.mkdir(parents=True, exist_ok=True)

        services = self.gh_option('services')
        additional_config = self.gh_option('additional-config')
        additional_exclude = self.gh_option('additional-exclude')
        steps_before_checkout = self.gh_option('steps-before-checkout')
        additional_install = self.gh_option('additional-install')
        additional_build_dependencies = self.gh_option(
            'additional-build-dependencies')
        test_environment = self.gh_option('test-environment')
        test_commands = self.gh_option('test-commands')
        self.copy_with_meta(
            'tests.yml.j2',
            workflows / 'tests.yml',
            self.config_type,
            gha_additional_config=additional_config,
            gha_additional_exclude=additional_exclude,
            gha_additional_install=additional_install,
            gha_additional_build_dependencies=additional_build_dependencies,
            gha_test_environment=test_environment,
            gha_test_commands=test_commands,
            package_name=self.path.name,
            services=services,
            steps_before_checkout=steps_before_checkout,
            with_docs=self.with_docs,
            with_sphinx_doctests=self.with_sphinx_doctests,
            with_future_python=self.with_future_python,
            future_python_version=FUTURE_PYTHON_VERSION,
            with_pypy=self.with_pypy,
            with_macos=self.with_macos,
            with_windows=self.with_windows,
        )

    def manifest_in(self):
        """Modify MANIFEST.in with meta options."""
        additional_manifest_rules = self.meta_cfg['manifest'].get(
            'additional-rules', [])
        if self.config_type == 'c-code' \
                and 'include *.sh' not in additional_manifest_rules:
            additional_manifest_rules.insert(0, 'include *.sh')
        self.copy_with_meta(
            'MANIFEST.in.j2', self.path / 'MANIFEST.in', self.config_type,
            additional_rules=additional_manifest_rules,
            with_docs=self.with_docs, with_appveyor=self.with_appveyor)

    def appveyor(self):
        appveyor_global_env_vars = self.meta_cfg['appveyor'].get(
            'global-env-vars', [])
        appveyor_additional_matrix = self.meta_cfg['appveyor'].get(
            'additional-matrix', [])
        appveyor_install_steps = self.meta_cfg['appveyor'].get(
            'install-steps', ['- pip install -U -e .[test]'])
        appveyor_build_script = self.meta_cfg['appveyor'].get(
            'build-script', [])
        if self.config_type == 'c-code' and not appveyor_build_script:
            appveyor_build_script = [
                '- python -W ignore setup.py -q bdist_wheel']
        appveyor_test_steps = self.meta_cfg['appveyor'].get(
            'test-steps', ['- zope-testrunner --test-path=src'])
        appveyor_additional_lines = self.meta_cfg['appveyor'].get(
            'additional-lines', [])
        appveyor_replacement = self.meta_cfg['appveyor'].get('replacement', [])
        self.copy_with_meta(
            'appveyor.yml.j2',
            self.path / 'appveyor.yml',
            self.config_type,
            with_future_python=self.with_future_python,
            global_env_vars=appveyor_global_env_vars,
            additional_matrix=appveyor_additional_matrix,
            install_steps=appveyor_install_steps,
            test_steps=appveyor_test_steps,
            build_script=appveyor_build_script,
            additional_lines=appveyor_additional_lines,
            replacement=appveyor_replacement,
        )

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

        self.setup_cfg()
        self.gitignore()
        self.copy_with_meta(
            'editorconfig', self.path / '.editorconfig', self.config_type)
        self.copy_with_meta(
            'CONTRIBUTING.md', self.path / 'CONTRIBUTING.md', self.config_type,
            meta_hint=META_HINT_MARKDOWN)

        with change_dir(self.path):
            # We have to add it here otherwise the linter complains
            # that it is not added.
            call('git', 'add', 'CONTRIBUTING.md')

        self.coveragerc()
        self.manylinux_sh()
        self.tox()
        self.tests_yml()
        self.manifest_in()

        if self.with_appveyor:
            self.appveyor()

        with change_dir(self.path) as cwd:
            if pathlib.Path('bootstrap.py').exists():
                call('git', 'rm', 'bootstrap.py')
            if pathlib.Path('.travis.yml').exists():
                call('git', 'rm', '.travis.yml')
            if self.rm_coveragerc:
                call('git', 'rm', '.coveragerc')
            if self.add_coveragerc:
                call('git', 'add', '.coveragerc')
            if self.with_appveyor:
                call('git', 'add', 'appveyor.yml')
            if self.add_manylinux:
                call('git', 'add', '.manylinux.sh', '.manylinux-install.sh')
            # Remove empty sections:
            meta_cfg = {k: v for k, v in self.meta_cfg.items() if v}
            with open('.meta.toml', 'w') as meta_f:
                meta_f.write(META_HINT.format(config_type=self.config_type))
                meta_f.write('\n')
                toml.dump(
                    meta_cfg, meta_f,
                    TomlArraySeparatorEncoderWithNewline(
                        separator=',\n   ', indent_first_line=True))

            tox_path = shutil.which('tox') or (
                pathlib.Path(cwd) / 'bin' / 'tox')
            call(tox_path, '-p', 'auto')

            updating = git_branch(self.branch_name)

            if not self.fail_under:
                print(
                    'In .meta.toml in section [coverage] the option '
                    '"fail-under" is  0. Please enter a valid minimum '
                    'coverage and rerun.')
                abort(1)
            if self.args.commit:
                call(
                    'git', 'add',
                    'setup.cfg', 'tox.ini', '.gitignore',
                    '.github/workflows/tests.yml', 'MANIFEST.in',
                    '.editorconfig',
                    '.meta.toml')
                if self.args.commit_msg:
                    commit_msg = self.args.commit_msg
                else:
                    commit_msg = f'Configuring for {self.config_type}'
                call('git', 'commit', '-m', commit_msg)
                if self.args.push:
                    call('git', 'push', '--set-upstream',
                         'origin', self.branch_name)
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


main()
