import argparse
import contextlib
import os
import pathlib


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


def path_factory(parameter_name, *, has_extension=None, is_dir=False):
    """Return factory creating pathlib.Path object if requirements are matched.

    The factory raises an exception otherwise.
    """
    def factory(str):
        path = pathlib.Path(str)
        if not path.exists():
            raise argparse.ArgumentTypeError(f'{str!r} does not exist!')
        if has_extension is not None and path.suffix != has_extension:
            raise argparse.ArgumentTypeError(
                f'The required extension is {has_extension!r}'
                f' not {path.suffix!r}.')
        if is_dir and not path.is_dir():
            raise argparse.ArgumentTypeError('has to point to a directory!')
        return path
    return factory
