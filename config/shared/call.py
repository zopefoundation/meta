import subprocess
import sys


def call(*args, capture_output=False, cwd=None):
    """Call `args` as a subprocess.

    If it fails exit the process.
    """
    result = subprocess.run(
        args, capture_output=capture_output, text=True, cwd=cwd)
    if result.returncode != 0:
        print('ABORTING: Please fix the errors shown above.')
        print('Proceed anyway (y/N)?', end=' ')
        if input().lower() != 'y':
            sys.exit(result.returncode)
    return result
