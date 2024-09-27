##############################################################################
#
# Copyright (c) 2022 Zope Foundation and Contributors.
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

from .call import call
from .path import change_dir


def get_commit_id():
    """Return the first 8 digits of the commit id of this repository."""
    with change_dir(pathlib.Path(__file__).parent):
        return call(
            'git', 'rev-parse', '--short=8', 'HEAD',
            capture_output=True).stdout.strip()


def get_branch_name(override, config_type):
    """Get the default branch name but prefer override if not empty.

    The commit ID is based on the meta repository.
    """
    return (
        override
        or f"config-with-{config_type}-template-{get_commit_id()}")


def git_branch(branch_name) -> bool:
    """Switch to existing or create new branch.

    Return `True` if updating.
    """
    branches = call(
        'git', 'branch', '--format', '%(refname:short)',
        capture_output=True).stdout.splitlines()
    if branch_name in branches:
        call('git', 'checkout', branch_name)
        updating = True
    else:
        call('git', 'checkout', '-b', branch_name)
        updating = False
    return updating
