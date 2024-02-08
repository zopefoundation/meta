##############################################################################
#
# Copyright (c) 2020 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import subprocess
import sys


def abort(exitcode):
    """Ask the user to abort."""
    print('ABORTING: Please fix the errors shown above.')
    print('Proceed anyway (y/N)?', end=' ')
    if input().lower() != 'y':
        sys.exit(exitcode)


def wait_for_accept():
    """Wait until the user has hit enter."""
    print('Proceed by hitting <ENTER>')
    input()


def call(*args, capture_output=False, cwd=None, allowed_return_codes=(0, )):
    """Call `args` as a subprocess.

    If it fails exit the process.
    """
    result = subprocess.run(
        args, capture_output=capture_output, text=True, cwd=cwd)
    if result.returncode not in allowed_return_codes:
        abort(result.returncode)
    return result
