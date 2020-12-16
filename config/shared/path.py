import contextlib
import os


@contextlib.contextmanager
def change_dir(path):
    """Change current working directory temporarily to `path`.

    Yields the current working directory before the change.
    """
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield cwd
    finally:
        os.chdir(cwd)
