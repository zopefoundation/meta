import pathlib


def list_packages(path: pathlib.Path) -> list:
    """List the packages in ``path``.

    ``path`` must point to a packages.txt file.
    """
    return [
        p
        for p in path.read_text().split('\n')
        if p and not p.startswith('#')
    ]
