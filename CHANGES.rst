Change log
==========

2.2 (unreleased)
----------------

- Add tox option ``testenv-skip-test-extra``.
  Set this to true if your package does not have a ``test`` extra.
  Otherwise tests fail with latest ``tox``.

- Remove special treatment for macOS test runners on GitHub

- Print out a warning if a ``setuptools`` install time dependency is found
  when runing the the ``config-package`` and ``setup-to-pyproject`` scripts.

- Change ``c-code`` GitHub Actions publishing step to use
  PyPI's "Trusted Publishing".
  (`#198 <https://github.com/zopefoundation/meta/issues/198>`_)

- Move package metadata from setup.py to pyproject.toml.

- When moving metadata to ``pyproject.toml``, ignore ``setup py test`` fossils.
  (`#260 <https://github.com/zopefoundation/meta/issues/260>`_)

- Allow overriding configuration values in ``zope.meta.shared.packages``
  by using the ``--overrides`` option and placing a TOML file named
  ``overrides.toml`` into the overrides folder.

- Rename the ``--template-overrides`` option to simply ``--overrides``.

- Add option to show file changes after a failed ``tox`` ``lint`` run or not.
  For backwards compatibility this is still ``True`` if not set.

- Add script to move package metadata from ``setup.py`` to ``pyproject.toml``.

- Move commonly used script argument processing into shared library file.


2.1 (2025-11-21)
----------------

- editorconfig: Don't use inline comments.
  Inline comments are invalid since editorconfig v0.15.0.

- Fix publishing Linux/arm64 wheels, which did not work after switching the
  GHA manylinux wheel build step for arm64 to a real arm64 runner.

- Fix Python version used for pre-commit at 3.13 so 3.14 is not used.
  Some linters like teyit are not compatible with Python 3.14.

- Update Python version used for manylinux builds to 3.13

- Run the GHA manylinux wheel build step for arm64 architecture on an actual
  Linux on arm64 VM instead of emulated on a x86_64 VM to speed things up.

- Fix ``update_python_support`` script for the case when ``with-future-python``
  is enabled.


2.0 (2025-10-28)
----------------

- Also check ``pyproject.toml`` when running ``check-python-versions``.

- Fix handling of ``tool`` section during ``pyproject.toml`` generation.

- Add support for Python 3.14.

- Drop support for Python 3.9.

- Allow ``setuptools >= 78.1.1, <81``.

- Replace ``pkg_resources`` namespace with PEP 420 native namespace.

- Update to ``pypy-3.11``.

- Add flag ``--no-tests`` to the scripts for switching to PEP 420
  namespaces and for updating supported Python versions.

- Add support for the ``--template-overrides`` flag to the Python version
  update script because it calls ``config-package``.

- Add ability to omit creating files by providing empty override templates.

- Fixed a regression that removed GHA additional installs from the
  default template for GHA testing.

- Upgrade setuptools pin to 75.8.2, which is extensively tested with the
  latest zc.buildout release 4.1.4. **Package maintainers should update
  all their sandboxes to use ``setuptools==75.8.2`` and ``zc.buildout>=4.1.4``
  to avoid issues with building and/or loading wheels!**

- Use Jinja templates to generate ``pyproject.toml`` files as well.

- Add argument ``--template-overrides`` to configuration script to specify
  an additional configuration templates folder. This folder is expected to
  contain subfolders for each overridden configuration type or a ``default``
  folder. The templates in these template folders will override the built-in
  templates.

- Add argument ``--no-tests`` to configuration script to skip unit tests.
  Useful for quick iterative configuration or code changes.

- Retire configurations ``require-cffi`` and ``additional-build-requirement``.
  Build dependencies should go into ``pyproject.toml`` instead.

- Fixes for changed wheel name issues with the latest setuptools/pip

- Improve ``pyproject.toml`` generation

- Add the tox ``release-check`` step to the ``c-code`` templates

- Add script ``bin/switch-to-pep420`` to convert a package from the old
  namespace package layout to the new PEP 420 native layout.

- Add ``pyupgrade-exclude`` to ``[pre-commit]`` section in ``.meta.toml``.

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
