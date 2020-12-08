#!/usr/bin/env python3
from shared.call import call
from shared.toml_encoder import TomlArraySeparatorEncoderWithNewline
import argparse
import collections
import jinja2
import os
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
    'path', type=str, help='path to the repository to be configured')
parser.add_argument(
    '--no-push',
    dest='no_push',
    action='store_true',
    help='Prevent direct push.')
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
        'pure-python',
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
path = pathlib.Path(args.path)
default_path = pathlib.Path(__file__).parent / 'default'

if not (path / '.git').exists():
    raise ValueError('`path` does not point to a git clone of a repository!')


# Read and update meta configuration
meta_toml_path = path / '.meta.toml'
if meta_toml_path.exists():
    meta_cfg = toml.load(meta_toml_path)
    meta_cfg = collections.defaultdict(dict, **meta_cfg)
else:
    meta_cfg = meta_dict_factory()

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
copy_with_meta(
    'setup.cfg.j2', path / 'setup.cfg', config_type,
    additional_flake8_config=additional_flake8_config,
    additional_check_manifest_ignores=additional_check_manifest_ignores,
    with_docs=with_docs, with_sphinx_doctests=with_sphinx_doctests)
copy_with_meta('editorconfig', path / '.editorconfig', config_type)
copy_with_meta('gitignore', path / '.gitignore', config_type)
workflows = path / '.github' / 'workflows'
workflows.mkdir(parents=True, exist_ok=True)

add_coveragerc = False
rm_coveragerc = False
if (config_type_path / 'coveragerc.j2').exists():
    copy_with_meta(
        'coveragerc.j2', path / '.coveragerc', config_type,
        package_name=path.name)
    add_coveragerc = True
elif (path / '.coveragerc').exists():
    rm_coveragerc = True


fail_under = meta_cfg['coverage'].setdefault('fail-under', 0)
copy_with_meta(
    'tox.ini.j2', path / 'tox.ini', config_type,
    fail_under=fail_under, with_pypy=with_pypy,
    with_legacy_python=with_legacy_python,
    with_docs=with_docs, with_sphinx_doctests=with_sphinx_doctests)
copy_with_meta(
    'tests.yml.j2', workflows / 'tests.yml', config_type,
    with_pypy=with_pypy, with_legacy_python=with_legacy_python,
    with_docs=with_docs)


# Modify MANIFEST.in with meta options
additional_manifest_rules = meta_cfg['manifest'].get('additional-rules', [])
copy_with_meta(
    'MANIFEST.in.j2', path / 'MANIFEST.in', config_type,
    additional_rules=additional_manifest_rules)

cwd = os.getcwd()
branch_name = args.branch_name or f'config-with-{config_type}'
try:
    os.chdir(path)
    if pathlib.Path('bootstrap.py').exists():
        call('git', 'rm', 'bootstrap.py')
    if pathlib.Path('.travis.yml').exists():
        call('git', 'rm', '.travis.yml')
    # Remove empty sections:
    meta_cfg = {k: v  for k, v in meta_cfg.items() if v}
    with open('.meta.toml', 'w') as meta_f:
        meta_f.write(
            '# Generated from:\n'
            '# https://github.com/zopefoundation/meta/tree/master/config/'
            f'{config_type}\n')
        toml.dump(
            meta_cfg, meta_f,
            TomlArraySeparatorEncoderWithNewline(
                separator=',\n   ', indent_first_line=True))

    call(pathlib.Path(cwd) / 'bin' / 'tox', '-p', 'auto')

    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'checkout', branch_name)
        updating = True
    else:
        call('git', 'checkout', '-b', branch_name)
        updating = False
    call('git', 'add',
         'setup.cfg', 'tox.ini', '.gitignore', '.github/workflows/tests.yml',
         'MANIFEST.in', '.editorconfig', '.meta.toml')
    if rm_coveragerc:
        call('git', 'rm', '.coveragerc')
    if add_coveragerc:
        call('git', 'add', '.coveragerc')
    call('git', 'commit', '-m', f'Configuring for {config_type}')
    if not args.no_push:
        call('git', 'push', '--set-upstream', 'origin', branch_name)
    print()
    print('If everything went fine up to here:')
    if updating:
        print('Updated the previously created PR.')
    else:
        print('Create a PR, using the URL shown above.')
finally:
    os.chdir(cwd)
