#!/usr/bin/env python3
from shared.call import abort
from shared.call import call
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
FUTURE_PYTHON_VERSION = "3.11.0-beta.3"


def copy_with_meta(
        template_name, destination, config_type, meta_hint=META_HINT, **kw):
    """Copy the source file to destination and a hint of origin.

    If kwargs are given they are used as template arguments.
    """
    with open(destination, 'w') as f_:
        template = jinja_env.get_template(template_name)
        rendered = template.render(config_type=config_type, **kw)
        meta_hint = meta_hint.format(config_type=config_type)
        if rendered.startswith('#!'):
            she_bang, _, body = rendered.partition('\n')
            content = '\n'.join([she_bang, meta_hint, body])
        else:
            content = '\n'.join([meta_hint, rendered])
        f_.write(content)


parser = argparse.ArgumentParser(
    description='Use configuration for a package.')
parser.add_argument(
    'path', type=pathlib.Path, help='path to the repository to be configured')
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
    help='Activate running tests on AppVeyor, too, if not already configured'
         ' in .meta.toml.')
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
    '--without-legacy-python',
    dest='with_legacy_python',
    action='store_false',
    default=None,
    help='Disable support for Python versions which reached their end-of-life.'
    ' (aka 2.7 and 3.5) if not already configured in .meta.toml.'
    ' Also disables support for PyPy2.')
parser.add_argument(
    '--with-docs',
    # people (me) use --with-sphinx and accidentally get --with-sphinx-doctests
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
    help='Activate running doctests with sphinx if not already configured in'
         ' .meta.toml.')
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
    help='type of the configuration to be used, see README.rst. Only required'
         ' when running on a repository for the first time.')
parser.add_argument(
    '--branch',
    dest='branch_name',
    default=None,
    help='Define a git branch name to be used for the changes. If not given'
         ' it is constructed automatically and includes the configuration'
         ' type')

args = parser.parse_args()
path = args.path.absolute()
default_path = pathlib.Path(__file__).parent / 'default'

if not (path / '.git').exists():
    raise ValueError('`path` does not point to a git clone of a repository!')


# Read and update meta configuration
meta_toml_path = path / '.meta.toml'
if meta_toml_path.exists():
    meta_cfg = toml.load(meta_toml_path)
    meta_cfg = collections.defaultdict(dict, **meta_cfg)
else:
    meta_cfg = collections.defaultdict(dict)
    if args.with_docs is None:
        args.with_docs = (path / "docs" / "conf.py").exists()
        print(f"Autodetecting --with-docs: {args.with_docs}")
    if args.with_appveyor is None:
        args.with_appveyor = (path / "appveyor.yml").exists()
        print(f"Autodetecting --with-appveyor: {args.with_appveyor}")

config_type = meta_cfg['meta'].get('template') or args.type

if config_type is None:
    raise ValueError(
        'Configuration type not set. Please use `--type` to select it.')
meta_cfg['meta']['template'] = config_type

config_type_path = pathlib.Path(__file__).parent / config_type
with open(config_type_path / 'packages.txt') as f:
    known_packages = f.read().splitlines()

if path.name in known_packages:
    print(f'{path.name} is already configured for this config type, updating.')
else:
    print(f'{path.name} is not yet configured for this config type, adding.')
    with open(config_type_path / 'packages.txt', 'a') as f:
        f.write(f'{path.name}\n')

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader([config_type_path, default_path]),
    variable_start_string='%(',
    variable_end_string=')s',
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

meta_cfg['meta']['commit-id'] = call(
    'git', 'log', '-n1', '--format=format:%H', capture_output=True).stdout
with_appveyor = meta_cfg['python'].get(
    'with-appveyor', False) or args.with_appveyor
meta_cfg['python']['with-appveyor'] = with_appveyor
with_windows = meta_cfg['python'].get(
    'with-windows', False) or args.with_windows
meta_cfg['python']['with-windows'] = with_windows
with_pypy = meta_cfg['python'].get('with-pypy', False) or args.with_pypy
meta_cfg['python']['with-pypy'] = with_pypy
with_future_python = (meta_cfg['python'].get('with-future-python', False)
                      or args.with_future_python)
meta_cfg['python']['with-future-python'] = with_future_python
if args.with_legacy_python is None:
    with_legacy_python = meta_cfg['python'].get('with-legacy-python', True)
else:
    with_legacy_python = args.with_legacy_python
meta_cfg['python']['with-legacy-python'] = with_legacy_python
with_docs = meta_cfg['python'].get('with-docs', False) or args.with_docs
meta_cfg['python']['with-docs'] = with_docs
with_sphinx_doctests = meta_cfg['python'].get(
    'with-sphinx-doctests', False) or args.with_sphinx_doctests
meta_cfg['python']['with-sphinx-doctests'] = with_sphinx_doctests


if with_sphinx_doctests and not with_docs:
    print("The package is configured without sphinx docs, but with sphinx"
          " doctests.  Is this a mistake?")

# Copy template files
additional_flake8_config = meta_cfg['flake8'].get('additional-config', [])
additional_check_manifest_ignores = meta_cfg['check-manifest'].get(
    'additional-ignores', [])
check_manifest_ignore_bad_ideas = meta_cfg['check-manifest'].get(
    'ignore-bad-ideas', [])
isort_known_third_party = meta_cfg['isort'].get(
    'known_third_party', 'six, docutils, pkg_resources')
isort_known_zope = meta_cfg['isort'].get('known_zope', '')
isort_known_first_party = meta_cfg['isort'].get('known_first_party', '')
isort_known_local_folder = meta_cfg['isort'].get('known_local_folder', '')
for var in (
    'isort_known_third_party',
    'isort_known_zope',
    'isort_known_first_party',
):
    if locals()[var]:
        # Avoid whitespace at end of line if empty:
        locals()[var] = ' ' + locals()[var]

copy_with_meta(
    'setup.cfg.j2', path / 'setup.cfg', config_type,
    additional_flake8_config=additional_flake8_config,
    additional_check_manifest_ignores=additional_check_manifest_ignores,
    check_manifest_ignore_bad_ideas=check_manifest_ignore_bad_ideas,
    isort_known_third_party=isort_known_third_party,
    isort_known_zope=isort_known_zope,
    isort_known_first_party=isort_known_first_party,
    isort_known_local_folder=isort_known_local_folder,
    with_docs=with_docs, with_sphinx_doctests=with_sphinx_doctests,
    with_legacy_python=with_legacy_python,
)
copy_with_meta('editorconfig', path / '.editorconfig', config_type)
copy_with_meta('gitignore', path / '.gitignore', config_type)
copy_with_meta(
    'CONTRIBUTING.md', path / 'CONTRIBUTING.md', config_type,
    meta_hint=META_HINT_MARKDOWN)
with change_dir(path):
    # We have to add it here otherwise the linter complains that it is not
    # added.
    call('git', 'add', 'CONTRIBUTING.md')
workflows = path / '.github' / 'workflows'
workflows.mkdir(parents=True, exist_ok=True)

coverage_run_additional_config = meta_cfg['coverage-run'].get(
    'additional-config', [])
coverage_run_source = meta_cfg['coverage-run'].get('source', path.name)
add_coveragerc = False
rm_coveragerc = False
if (config_type_path / 'coveragerc.j2').exists():
    copy_with_meta(
        'coveragerc.j2', path / '.coveragerc', config_type,
        coverage_run_source=coverage_run_source,
        run_additional_config=coverage_run_additional_config,
        with_legacy_python=with_legacy_python,
    )
    add_coveragerc = True
elif (path / '.coveragerc').exists():
    rm_coveragerc = True

manylinux_install_setup = meta_cfg['c-code'].get(
    'manylinux-install-setup', [])
manylinux_aarch64_tests = meta_cfg['c-code'].get(
    'manylinux-aarch64-tests', [
        'cd /io/',
        '${PYBIN}/pip install tox',
        'TOXENV=$(tox_env_map "${PYBIN}")',
        '${PYBIN}/tox -e ${TOXENV}',
        'cd ..',
    ])
if (config_type_path / 'manylinux.sh').exists():
    copy_with_meta('manylinux.sh', path / '.manylinux.sh', config_type)
    (path / '.manylinux.sh').chmod(0o755)
    copy_with_meta(
        'manylinux-install.sh.j2', path / '.manylinux-install.sh', config_type,
        package_name=path.name,
        setup=manylinux_install_setup,
        aarch64_tests=manylinux_aarch64_tests,
        with_legacy_python=with_legacy_python,
        with_future_python=with_future_python,
    )
    (path / '.manylinux-install.sh').chmod(0o755)
    add_manylinux = True
else:
    add_manylinux = False


additional_envlist = meta_cfg['tox'].get('additional-envlist', [])
testenv_additional = meta_cfg['tox'].get('testenv-additional', [])
testenv_additional_extras = meta_cfg['tox'].get(
    'testenv-additional-extras', [])
testenv_commands_pre = meta_cfg['tox'].get('testenv-commands-pre', [])
testenv_commands = meta_cfg['tox'].get('testenv-commands', [])
testenv_setenv = meta_cfg['tox'].get('testenv-setenv', [])
coverage_basepython = meta_cfg['tox'].get('coverage-basepython', 'python3')
coverage_command = meta_cfg['tox'].get('coverage-command', [])
if isinstance(coverage_command, str):
    coverage_command = [coverage_command]
coverage_additional = meta_cfg['tox'].get('coverage-additional', [])
testenv_deps = meta_cfg['tox'].get('testenv-deps', [])
coverage_setenv = meta_cfg['tox'].get('coverage-setenv', [])
fail_under = meta_cfg['coverage'].setdefault('fail-under', 0)
coverage_run_additional_config = meta_cfg['coverage-run'].get(
    'additional-config', [])
flake8_additional_sources = meta_cfg['flake8'].get('additional-sources', '')
if flake8_additional_sources:
    # Avoid whitespace at end of line if no additional sources are provided:
    flake8_additional_sources = ' ' + flake8_additional_sources
if args.use_flake8 is None:
    use_flake8 = meta_cfg['tox'].get('use-flake8', True)
else:
    use_flake8 = args.use_flake8
meta_cfg['tox']['use-flake8'] = use_flake8
copy_with_meta(
    'tox.ini.j2', path / 'tox.ini', config_type,
    additional_envlist=additional_envlist,
    coverage_additional=coverage_additional,
    coverage_basepython=coverage_basepython,
    coverage_command=coverage_command,
    coverage_run_source=coverage_run_source,
    coverage_run_additional_config=coverage_run_additional_config,
    coverage_setenv=coverage_setenv,
    fail_under=fail_under,
    flake8_additional_sources=flake8_additional_sources,
    testenv_additional=testenv_additional,
    testenv_additional_extras=testenv_additional_extras,
    testenv_commands=testenv_commands,
    testenv_commands_pre=testenv_commands_pre,
    testenv_deps=testenv_deps,
    testenv_setenv=testenv_setenv,
    use_flake8=use_flake8,
    with_docs=with_docs,
    with_legacy_python=with_legacy_python,
    with_future_python=with_future_python,
    with_pypy=with_pypy,
    with_sphinx_doctests=with_sphinx_doctests,
)

gha_services = meta_cfg['github-actions'].get('services', [])
gha_additional_config = meta_cfg['github-actions'].get(
    'additional-config', [])
gha_additional_exclude = meta_cfg['github-actions'].get(
    'additional-exclude', [])
gha_steps_before_checkout = meta_cfg['github-actions'].get(
    'steps-before-checkout', [])
gha_additional_install = meta_cfg['github-actions'].get(
    'additional-install', [])
gha_test_commands = meta_cfg['github-actions'].get(
    'test-commands', [])
copy_with_meta(
    'tests.yml.j2', workflows / 'tests.yml', config_type,
    gha_additional_config=gha_additional_config,
    gha_additional_exclude=gha_additional_exclude,
    gha_additional_install=gha_additional_install,
    gha_test_commands=gha_test_commands,
    package_name=path.name,
    services=gha_services,
    steps_before_checkout=gha_steps_before_checkout,
    with_docs=with_docs,
    with_sphinx_doctests=with_sphinx_doctests,
    with_legacy_python=with_legacy_python,
    with_future_python=with_future_python,
    future_python_version=FUTURE_PYTHON_VERSION,
    with_pypy=with_pypy,
    with_windows=with_windows,
)


# Modify MANIFEST.in with meta options
additional_manifest_rules = meta_cfg['manifest'].get('additional-rules', [])
if config_type == 'c-code' and 'include *.sh' not in additional_manifest_rules:
    additional_manifest_rules.insert(0, 'include *.sh')
copy_with_meta(
    'MANIFEST.in.j2', path / 'MANIFEST.in', config_type,
    additional_rules=additional_manifest_rules,
    with_docs=with_docs, with_appveyor=with_appveyor)


if with_appveyor:
    appveyor_global_env_vars = meta_cfg['appveyor'].get(
        'global-env-vars', [])
    appveyor_additional_matrix = meta_cfg['appveyor'].get(
        'additional-matrix', [])
    appveyor_install_steps = meta_cfg['appveyor'].get(
        'install-steps', ['- pip install -U -e .[test]'])
    appveyor_build_script = meta_cfg['appveyor'].get(
        'build-script', [])
    if config_type == 'c-code' and not appveyor_build_script:
        appveyor_build_script = ['- python -W ignore setup.py -q bdist_wheel']
    appveyor_test_steps = meta_cfg['appveyor'].get(
        'test-steps', ['- zope-testrunner --test-path=src'])
    appveyor_additional_lines = meta_cfg['appveyor'].get(
        'additional-lines', [])
    appveyor_replacement = meta_cfg['appveyor'].get('replacement', [])
    copy_with_meta(
        'appveyor.yml.j2', path / 'appveyor.yml', config_type,
        with_legacy_python=with_legacy_python,
        with_future_python=with_future_python,
        global_env_vars=appveyor_global_env_vars,
        additional_matrix=appveyor_additional_matrix,
        install_steps=appveyor_install_steps, test_steps=appveyor_test_steps,
        build_script=appveyor_build_script,
        additional_lines=appveyor_additional_lines,
        replacement=appveyor_replacement,
    )


branch_name = args.branch_name or f'config-with-{config_type}'
with change_dir(path) as cwd:
    if pathlib.Path('bootstrap.py').exists():
        call('git', 'rm', 'bootstrap.py')
    if pathlib.Path('.travis.yml').exists():
        call('git', 'rm', '.travis.yml')
    if rm_coveragerc:
        call('git', 'rm', '.coveragerc')
    if add_coveragerc:
        call('git', 'add', '.coveragerc')
    if with_appveyor:
        call('git', 'add', 'appveyor.yml')
    if add_manylinux:
        call('git', 'add', '.manylinux.sh', '.manylinux-install.sh')
    # Remove empty sections:
    meta_cfg = {k: v for k, v in meta_cfg.items() if v}
    with open('.meta.toml', 'w') as meta_f:
        meta_f.write(META_HINT.format(config_type=config_type))
        meta_f.write('\n')
        toml.dump(
            meta_cfg, meta_f,
            TomlArraySeparatorEncoderWithNewline(
                separator=',\n   ', indent_first_line=True))

    tox_path = shutil.which('tox') or (pathlib.Path(cwd) / 'bin' / 'tox')
    call(tox_path, '-p', 'auto')

    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'checkout', branch_name)
        updating = True
    else:
        call('git', 'checkout', '-b', branch_name)
        updating = False
    if not fail_under:
        print('In .meta.toml in section [coverage] the option "fail-under" is'
              ' 0. Please enter a valid minimum coverage and rerun.')
        abort(1)
    if args.commit:
        call('git', 'add',
             'setup.cfg', 'tox.ini', '.gitignore',
             '.github/workflows/tests.yml', 'MANIFEST.in', '.editorconfig',
             '.meta.toml')
        if args.commit_msg:
            commit_msg = args.commit_msg
        else:
            commit_msg = f'Configuring for {config_type}'
        call('git', 'commit', '-m', commit_msg)
        if args.push:
            call('git', 'push', '--set-upstream', 'origin', branch_name)
    print()
    print('If everything went fine up to here:')
    if updating:
        print('Updated the previously created PR.')
    else:
        print('Create a PR, using the URL shown above.')
