Change log
==========

1.2 (unreleased)
----------------

- Add script ``bin/switch-to-pep420`` to convert a package from the old
  namespace package layout to the new PEP 420 native layout.

- Add ability to run ``bin/update-python-support`` in CI.


1.1 (2025-01-29)
----------------

- Drop support for Python 3.8.

- Allow specifying a minimum supported Python version other than the previously
  hardcoded default of Python 3.8.

- Allow ``setuptools <= 75.6.0``.

- Add ``omit`` option to ``coverage-run`` configuration because when defined in
  ``pyproject.toml`` it needs to be a list of strings.

- Update ``setup.py`` of configured packages with small textual changes to
  match current best practices.

1.0 (2024-10-02)
----------------

- Converted to an installable Python package.
