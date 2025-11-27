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
# Shared script argument handling

import argparse
import pathlib


def get_shared_parser(description, interactive=False):
    parser = argparse.ArgumentParser(description=description)
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
        '--no-tests',
        dest='run_tests',
        action='store_false',
        default=True,
        help='Skip running unit tests.')
    parser.add_argument(
        '--branch',
        dest='branch_name',
        default=None,
        help='Define a git branch name to be used for the changes. '
        'If not given it is constructed automatically and includes '
        'the configuration type')
    parser.add_argument(
        '--overrides',
        type=pathlib.Path,
        dest='overrides_path',
        default=None,
        help='Filesystem path to a folder with subfolders for configuration '
        'types. Used to override built-in configuration templates.')

    if interactive:
        parser.add_argument(
            "--interactive",
            dest="interactive",
            action="store_true",
            default=False,
            help="Run interactively: Scripts will prompt for input. Implies "
            "--no-commit, changes will not be committed and pushed "
            "automatically.",
        )

    return parser
