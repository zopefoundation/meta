#!/usr/bin/env python3
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

import ast
import contextlib
import os
import pathlib
import shutil
import sys
from importlib.util import module_from_spec
from importlib.util import spec_from_file_location

import tomlkit

from .shared.call import call
from .shared.git import git_branch
from .shared.packages import get_pyproject_toml
from .shared.packages import META_HINT
from .shared.path import change_dir
from .shared.script_args import get_shared_parser


PROJECT_SIMPLE_KEYS = (
    'name', 'version', 'description', 'license',
    )
IGNORE_KEYS = (
    'zip_safe', 'long_description_content_type', 'package_dir',
    'packages', 'include_package_data',
    )
UNCONVERTIBLE_KEYS = (
    'cmdclass', 'ext_modules', 'headers', 'cffi_modules',
    )


def parse_setup_function(ast_node, assigned_names=None):
    """ Parse values out of the setup call ast definition """
    setup_kwargs = {}
    assigned_names = assigned_names or {}

    for kw_arg in ast_node.keywords:
        if isinstance(kw_arg.value, (ast.Constant, ast.List, ast.Tuple)):
            setup_kwargs[kw_arg.arg] = ast.literal_eval(kw_arg.value)
        elif isinstance(kw_arg.value, ast.Dict):
            # This could hide variables
            try:
                setup_kwargs[kw_arg.arg] = ast.literal_eval(kw_arg.value)
            except ValueError:
                # Need to crawl the dictionary
                gathered = {}
                for (key, value) in zip(kw_arg.value.keys,
                                        kw_arg.value.values):
                    if isinstance(value, ast.Name):
                        gathered[key.value] = assigned_names.get(value.id, '')
                    elif isinstance(value, ast.BinOp):
                        # Interpolated string 'x%sy' % foo
                        unformatted = value.left.value
                        variable = assigned_names.get(value.right.id, '')
                        formatted = unformatted.replace('%s', variable)
                        gathered[key.value] = formatted
                    elif isinstance(value, (ast.List, ast.Tuple)):
                        try:
                            gathered[key.value] = ast.literal_eval(value)
                        except ValueError:
                            # Probably a variable in the list
                            l = []
                            for member in value.elts:
                                if isinstance(member,
                                              (ast.Constant,
                                               ast.List,
                                               ast.Tuple)):
                                    l.append(ast.literal_eval(member.value))
                                elif isinstance(member, ast.BinOp):
                                    unformatted = member.left.value
                                    variable = assigned_names.get(
                                                    member.right.id, '')
                                    formatted = unformatted.replace(
                                                    '%s', variable)
                                    l.append(formatted)
                                else:
                                    l.append(ast.literal_eval(member.value))
                            gathered[key.value] = l
                    else:
                        try:
                            gathered[key.value] = ast.literal_eval(value)
                        except ValueError:
                            print('XXX Cannot convert dictionary value XXX')
                            print('XXX Please fix setup.py manually first XXX')
                            print(f'XXX Dictionary key: {key.value} XXX')
                            print(ast.dump(value, indent=2))
                            sys.exit(1)
                setup_kwargs[kw_arg.arg] = gathered
        elif isinstance(kw_arg.value, ast.Name):
            if kw_arg.value.id in assigned_names:
                value = assigned_names.get(kw_arg.value.id)
            else:
                value = kw_arg.value.id
            setup_kwargs[kw_arg.arg] = value

    return setup_kwargs


def setup_args_to_toml_dict(setup_kwargs):
    """ Iterate over setup_kwargs and generate a dictionary of values suitable
    for pyproject.toml and a dictionary with unconverted arguments
    """
    toml_dict = {'project': {}}
    p_data = toml_dict['project']

    for key in IGNORE_KEYS:
        setup_kwargs.pop(key, None)

    for key in UNCONVERTIBLE_KEYS:
        setup_kwargs.pop(key, None)

    for key in PROJECT_SIMPLE_KEYS:
        if key in setup_kwargs:
            p_data[key] = setup_kwargs.pop(key)

    classifiers = setup_kwargs.pop('classifiers', [])
    new_classifiers = []
    for classifier in classifiers:
        if not classifier.startswith('License'):
            new_classifiers.append(classifier)
    p_data['classifiers'] = new_classifiers

    p_data['readme'] = 'README.rst'
    if 'python_requires' in setup_kwargs:
        p_data['requires-python'] = setup_kwargs.pop('python_requires')

    if 'author' in setup_kwargs:
        author_dict = {'name': setup_kwargs.pop('author')}
        if 'author_email' in setup_kwargs:
            author_dict['email'] = setup_kwargs.pop('author_email')
        p_data['authors'] = tomlkit.array()
        p_data['authors'].add_line(author_dict)

    maintainers_table = {'name': 'Plone Foundation and contributors',
                         'email': 'zope-dev@zope.dev'}
    p_data['maintainers'] = tomlkit.array()
    p_data['maintainers'].add_line(maintainers_table)

    entry_points = {}
    ep_data = setup_kwargs.pop('entry_points', {})

    if isinstance(ep_data, str):
        ep_lines = [x.strip() for x in ep_data.split('\n') if x]
        ep_data = {}
        for line in ep_lines:
            key_buffer = ''
            if line.startswith('['):
                line = line.replace('[', '').replace(']', '').strip()
                key_buffer = line
            else:
                if line and key_buffer:
                    line = line.replace(' = ', '=').strip()
                    ep_data[key_buffer] = line
                    key_buffer = ''
    for ep_type, ep_list in ep_data.items():
        if ep_type == 'console_scripts':
            scripts_dict = entry_points.setdefault('scripts', {})
        else:
            scripts_dict = entry_points.setdefault(ep_type, {})

        for ep in ep_list:
            ep_name, ep_target = [x.strip() for x in ep.split('=')]
            scripts_dict[ep_name] = ep_target
    if entry_points:
        p_data['entry-points'] = entry_points

    extras = setup_kwargs.pop('extras_require', {})
    if isinstance(extras, str):
        print(' XXX Error converting setup.py XXX')
        print(' XXX Clean up setup.py manually first:')
        print(f' Change extras_require value to not use variable {extras}!')
        print(f' Instead, insert the actual value of variable {extras}.')
        sys.exit(1)
    opt_deps = {}
    for e_name, e_list in extras.items():
        opt_deps[e_name] = e_list
    if opt_deps:
        p_data['optional-dependencies'] = opt_deps

    install_reqs = setup_kwargs.pop('install_requires', [])
    if install_reqs:
        p_data['dependencies'] = install_reqs

    keywords = setup_kwargs.pop('keywords', '')
    if keywords and isinstance(keywords, str):
        p_data['keywords'] = keywords.split()
    elif isinstance(keywords, (list, tuple)):
        p_data['keywords'] = keywords

    project_urls = setup_kwargs.pop('project_urls', {})
    url = setup_kwargs.pop('url', '')
    if 'github' in url and 'Source' not in project_urls:
        project_urls['Source'] = url
    if 'Sources' in project_urls:
        project_urls['Source'] = project_urls.pop('Sources')
    if 'Issue Tracker' in project_urls:
        project_urls['Issues'] = project_urls.pop('Issue Tracker')
    if project_urls:
        p_data['urls'] = project_urls

    return (setup_kwargs, toml_dict)

def parse_setup_py(path):
    """ Parse values out of setup.py """
    setup_kwargs = {}
    assigned_names = {}

    # Nasty: Import the setup module file to get at the resolved variables
    import_spec = spec_from_file_location('setup', path)
    setup_module = module_from_spec(import_spec)
    try:
        with open(os.devnull, 'w') as fp:
            with contextlib.redirect_stderr(fp):
                import_spec.loader.exec_module(setup_module)
    except (FileNotFoundError, SystemExit):
        pass

    for key in dir(setup_module):
        assigned_names[key] = getattr(setup_module, key)

    with open(path, 'r') as fp:
        file_contents = fp.read()

    # Create the ast tree for the setup module to find the setup call
    # definition in order to parse out the call arguments.
    ast_tree = ast.parse(file_contents)
    setup_node = None

    for ast_node in ast_tree.body:
        if isinstance(ast_node, ast.Expr) and \
           isinstance(ast_node.value, ast.Call) and \
           ast_node.value.func.id == 'setup':
            setup_node = ast_node.value

    if setup_node is not None:
        setup_kwargs = parse_setup_function(setup_node, assigned_names)
    leftover_setup_kwargs, toml_dict = setup_args_to_toml_dict(setup_kwargs)

    return leftover_setup_kwargs, toml_dict


def rewrite_pyproject_toml(path, toml_dict):
    p_toml = get_pyproject_toml(path)

    def recursive_merge(dict1, dict2):
        for key, value in dict2.items():
            if key in dict1 and \
               isinstance(dict1[key], dict) and \
               isinstance(value, dict):
                dict1[key] = recursive_merge(dict1[key], value)
            else:
                # We will not overwrite existing values!
                if key not in dict1:
                    dict1[key] = value

    recursive_merge(p_toml, toml_dict)

    # Format long lists
    p_toml['project']['classifiers'].multiline(True)
    p_toml['project']['authors'].multiline(True)
    p_toml['project']['maintainers'].multiline(True)
    if 'dependencies' in p_toml['project'] and \
       len(p_toml['project']['dependencies']) > 1:
        p_toml['project']['dependencies'].multiline(True)
    if 'keywords' in p_toml['project'] and \
       len(p_toml['project']['keywords']) > 4:
        p_toml['project']['keywords'].multiline(True)

    opt_deps = p_toml['project'].get('optional-dependencies', {})
    for key, value in opt_deps.items():
        if len(value) > 1:
            p_toml['project']['optional-dependencies'][key].multiline(True)

    # Create a fesh TOMLDocument instance so I can control section sorting
    with open(path.absolute().parent / '.meta.toml', 'rb') as fp:
        meta_cfg = tomlkit.load(fp)
    config_type = meta_cfg['meta'].get('template')
    new_doc = tomlkit.loads('%s\n' % META_HINT.format(config_type=config_type))
    for key in sorted(p_toml.keys()):
        new_doc[key] = p_toml.get(key)

    return tomlkit.dumps(new_doc)


def rewrite_setup_py(path, leftover_setup_kwargs):
    """ Write new setup py with unconverted call arguments

    While it's possible to take the ``setup.py`` source, parse out an ast
    tree and manipulate that to generate new code it loses all comments,
    spacing and formatting when dumping it back out. So I am doing it with an
    axe. This code assumes that the call to ``setup`` is the last thing in the
    file.
    """
    new_setup_py = []
    with open(path, 'r') as fp:
        old_setup_py = fp.readlines()

    for line in old_setup_py:
        if line.startswith('setup('):
            break

        new_setup_py.append(line)

    new_setup_py.append('# See pyproject.toml for package metadata\n')
    if not leftover_setup_kwargs:
        new_setup_py.append('setup()\n')
    else:
        new_setup_py.append('setup(\n')
        for key, value in leftover_setup_kwargs.items():
            new_setup_py.append(f'    {key}={value},\n')
        new_setup_py.append(')\n')

    return ''.join(new_setup_py)


def package_sanity_check(path):
    """ Sanity checks for the provided path """
    sane = True

    if not path.exists():
        print(f' - no such path {path}.')
        sane = False

    if not path.is_dir():
        print(f' - {path} is not a folder')
        sane = False

    if not (path / 'setup.py').exists():
        print(' - no setup.py found, cannot convert package.')
        sane = False

    if not (path / '.meta.toml').exists():
        print(' - no pyproject.toml found, cannot convert package.')
        sane = False

    return sane


def main():
    parser = get_shared_parser(
        "Move package metadata from setup.py to pyproject.toml.",
        interactive=True)
    parser.add_argument(
        '--dry-run',
        dest='dry_run',
        action='store_true',
        default=False,
        help='Do not make any changes but output contents for the changed'
             ' setup.py and pyproject.toml files.',
        )
    args = parser.parse_args()

    print(f'Converting package {args.path.name}')

    if not package_sanity_check(args.path):
        print('Conversion not possible, exiting.')
        sys.exit()

    (leftover_setup_kwargs, toml_dict) = parse_setup_py(args.path / 'setup.py')

    # Sanity check - if project has been converted already, give up.
    if 'name' not in toml_dict['project'] and \
       'version' not in toml_dict['project']:
        print('Package has been converted already, exiting.')
        sys.exit()

    toml_content = rewrite_pyproject_toml(args.path / 'pyproject.toml',
                                          toml_dict)
    setup_content = rewrite_setup_py(args.path / 'setup.py',
                                     leftover_setup_kwargs)

    # If this is a dry run, just print the end result and exit.
    if args.dry_run:
        print('\n------------> pyproject.toml with all changes applied:')
        print(toml_content)
        print('\n------------> setup.py with all changes applied:')
        print(setup_content)
        sys.exit()

    with open(args.path / 'pyproject.toml', 'w') as fp:
        fp.write(toml_content)
    with open(args.path / 'setup.py', 'w') as fp:
        fp.write(setup_content)

    if args.interactive or args.commit:
        print('Look through setup.py to see if it needs changes.')
        call(os.environ['EDITOR'], 'setup.py')
        print('Look through pyproject.toml to see if it needs changes.')
        call(os.environ['EDITOR'], 'pyproject.toml')

    with change_dir(args.path) as cwd:
        if args.run_tests:
            tox_path = shutil.which('tox') or (
                pathlib.Path(cwd) / 'bin' / 'tox')
            call(tox_path, '-p', 'auto')

        branch_name = args.branch_name or "convert-setup-py-to-pyproject-toml"
        updating = git_branch(branch_name)

        if args.commit:
            if args.commit_msg:
                commit_msg = args.commit_msg
            else:
                commit_msg = ('Move package metadata from setup.py'
                              ' to pyproject.toml.')
            call('git', 'commit', '-m', commit_msg)
            if args.push:
                call('git', 'push', '--set-upstream', 'origin', branch_name)

        print('If everything went fine up to here:')
        if updating:
            print('Updated the previously created PR.')
        else:
            print('Create a PR, using the URL shown above.')

    print(f'Finished converting {args.path.name}.')
