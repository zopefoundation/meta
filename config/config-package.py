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
# https://github.com/zopefoundation/meta/tree/master/config/{config_type}
"""


def copy_with_meta(template_name, destination, config_type, **kw):
    """Copy the source file to destination and a hint of origin.

    If kwargs are given they are used as template arguments.
    """
    with open(destination, 'w') as f_:
        f_.write(META_HINT.format(config_type=config_type))
        template = jinja_env.get_template(template_name)
        f_.write(template.render(config_type=config_type, **kw))


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
    help='Do not include flake8 and isort in the linting configuration.')
parser.add_argument(
    '--with-appveyor',
    dest='with_appveyor',
    action='store_true',
    default=False,
    help='Activate running tests on AppVeyor, too, if not already configured'
         ' in .meta.toml.')
parser.add_argument(
    '--with-pypy',
    dest='with_pypy',
    action='store_true',
    default=False,
    help='Activate PyPy support if not already configured in .meta.toml.')
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
    dest='with_docs',
    action='store_true',
    default=False,
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
path = args.path
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
with_pypy = meta_cfg['python'].get('with-pypy', False) or args.with_pypy
meta_cfg['python']['with-pypy'] = with_pypy
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
workflows = path / '.github' / 'workflows'
workflows.mkdir(parents=True, exist_ok=True)

coverage_run_additional_config = meta_cfg['coverage-run'].get(
    'additional-config', [])
add_coveragerc = False
rm_coveragerc = False
if (config_type_path / 'coveragerc.j2').exists():
    copy_with_meta(
        'coveragerc.j2', path / '.coveragerc', config_type,
        package_name=path.name,
        run_additional_config=coverage_run_additional_config,
    )
    add_coveragerc = True
elif (path / '.coveragerc').exists():
    rm_coveragerc = True


additional_envlist = meta_cfg['tox'].get('additional-envlist', [])
testenv_additional = meta_cfg['tox'].get('testenv-additional', [])
testenv_additional_extras = meta_cfg['tox'].get(
    'testenv-additional-extras', [])
testenv_commands_pre = meta_cfg['tox'].get('testenv-commands-pre', [])
testenv_commands = meta_cfg['tox'].get('testenv-commands', [])
testenv_setenv = meta_cfg['tox'].get('testenv-setenv', [])
coverage_command = meta_cfg['tox'].get('coverage-command', '')
coverage_additional = meta_cfg['tox'].get('coverage-additional', [])
testenv_deps = meta_cfg['tox'].get('testenv-deps', ['zope.testrunner'])
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
    coverage_command=coverage_command,
    coverage_run_additional_config=coverage_run_additional_config,
    coverage_setenv=coverage_setenv,
    fail_under=fail_under,
    flake8_additional_sources=flake8_additional_sources,
    package_name=path.name,
    testenv_additional=testenv_additional,
    testenv_additional_extras=testenv_additional_extras,
    testenv_commands=testenv_commands,
    testenv_commands_pre=testenv_commands_pre,
    testenv_deps=testenv_deps,
    testenv_setenv=testenv_setenv,
    use_flake8=use_flake8,
    with_docs=with_docs,
    with_legacy_python=with_legacy_python,
    with_pypy=with_pypy,
    with_sphinx_doctests=with_sphinx_doctests,
)

gha_services = meta_cfg['github-actions'].get('services', [])
gha_additional_config = meta_cfg['github-actions'].get(
    'additional-config', [])
gha_steps_before_checkout = meta_cfg['github-actions'].get(
    'steps-before-checkout', [])
gha_additional_install = meta_cfg['github-actions'].get(
    'additional-install', [])
gha_test_commands = meta_cfg['github-actions'].get(
    'test-commands', [])
copy_with_meta(
    'tests.yml.j2', workflows / 'tests.yml', config_type,
    package_name=path.name,
    with_pypy=with_pypy, with_legacy_python=with_legacy_python,
    with_docs=with_docs, gha_additional_install=gha_additional_install,
    services=gha_services, steps_before_checkout=gha_steps_before_checkout,
    gha_additional_config=gha_additional_config,
    gha_test_commands=gha_test_commands,
)


# Modify MANIFEST.in with meta options
additional_manifest_rules = meta_cfg['manifest'].get('additional-rules', [])
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
    appveyor_test_steps = meta_cfg['appveyor'].get(
        'test-steps', ['- zope-testrunner --test-path=src'])
    appveyor_additional_lines = meta_cfg['appveyor'].get(
        'additional-lines', [])
    appveyor_replacement = meta_cfg['appveyor'].get('replacement', [])
    copy_with_meta(
        'appveyor.yml.j2', path / 'appveyor.yml', config_type,
        with_legacy_python=with_legacy_python,
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
    # Remove empty sections:
    meta_cfg = {k: v for k, v in meta_cfg.items() if v}
    with open('.meta.toml', 'w') as meta_f:
        meta_f.write(META_HINT.format(config_type=config_type))
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
