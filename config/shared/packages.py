import itertools
import pathlib


TYPES = ['buildout-recipe', 'c-code', 'pure-python', 'zope-product', 'toolkit']
ORG = 'zopefoundation'
BASE_PATH = pathlib.Path(__file__).parent.parent
OLDEST_PYTHON_VERSION = '3.7'
NEWEST_PYTHON_VERSION = '3.11'
MANYLINUX_PYTHON_VERSION = '3.9'


def list_packages(path: pathlib.Path) -> list:
    """List the packages in ``path``.

    ``path`` must point to a packages.txt file.
    """
    return [
        p
        for p in path.read_text().split('\n')
        if p and not p.startswith('#')
    ]


ALL_REPOS = itertools.chain(
    *[list_packages(BASE_PATH / type / 'packages.txt')
      for type in TYPES])
