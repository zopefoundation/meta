======
Config
======

Purpose
-------

Bring the configuration of the zopefoundation packages into a common state and
keep it there.


Types
-----

This directory contains the configuration directories for different types of
packages:

* buildout-recipe

  - Configuration for a zc.buildout recipe. It is tested using multiple
    processes, so coverage has to be configured in a special way. (Supports
    pure python packages which also run on PyPy.)

* pure-python

  - Configuration for a pure python package.

* zope-product

  - Configuration for a pure python package which uses zc.buildout inside
    ``tox.ini`` to be able to pin the installed dependency versions the same
    way ``buildout.cfg`` does it.


Contents
--------

Each directory contains the following files if they differ from the default
(stored in a directory named ``default``):

* packages.txt

  - This file lists the packages which use the configuration in the
    directory.

* editorconfig

  - This file is copied to `.editorconfig` and allows developers to have a
    common editor configuration experience in all repos.

* gitignore

  - This file is copied to `.gitignore`.

* MANIFEST.in.j2

  - Configuration file for the MANIFEST to include all needed files in sdist
    and wheel.

* setup.cfg

  - common setup.cfg, which should be copied to the repository of the
    package

* tox.ini.j2

  - tox configuration, which should be copied to the repository of the
    package

* tests.yml.j2

  - Configuration for GitHub actions.


Usage
-----

Preparation
+++++++++++

The script needs a ``venv`` with some packages installed::

    $ python3.8 -m venv .
    $ bin/pip install -r requirements.txt

To use the configuration provided here in a package call the following script::

    $ bin/python config-package.py <path-to-package> <config-type-name>

See ``--help`` for details.

The script does the following steps:

1. Add the package name to ``packages.txt`` of the selected configuration type
   if it is not yet added.
2. Copy ``setup.cfg``, ``tox.ini``, ``tests.yml``, ``MANIFEST.in`` and
   ``.gitignore`` to the repository.
3. Remove a possibly existing ``.coveragerc`` and ``bootstrap.py``. (Coverage
   is now configured in ``tox.ini`` for packages which are no buildout
   recipes.)
4. Run the tests via: ``tox``
5. Create a branch and a pull request. (Prevent pushing to GitHub using the
   command line switch ``--no-push``.)

After running the script you should manually do the following steps:

1. Check for changes in the updated repository and for the need of a change log
   entry over there.
2. Make sure the package is activated on https://coveralls.io by trying to add
   the repository name and making it active.
3. Check in possible changes in the zopefoundation/meta repository.


CLI arguments
+++++++++++++

The following arguments are supported.

--no-push
  Avoid pushing at the end of the configuration run.

--branch
  Define a specific git branch name to be created for the changes. By default
  the script creates one which includes the name of the configuration type.

The following options are only needed one time as their values re stored in
``.meta.toml.``.

--type
  Define the configuration type (see `Types`_ section above) to be used for the
  repository.

--with-appveyor
  Enable running the tests on AppVeyor, too.

--with-pypy
  Enable PyPy support.

--without-legacy-python
  The package does not support Python versions which reached their end-of-life.
  (Currently this means dropping support for Python 2.7 and 3.5.) This as well
  drops support for PyPy2.

--with-docs
  Enable building the documentation using Sphinx.

--with-sphinx-doctests
  Enable running the documentation as doctest using Sphinx.


Options
+++++++

It is possible to configure some options in a `.meta.toml` file
inside the package repository. This file also stores the template name and
commit id of the *meta* repository at the time of the run. This file is
generated during the configuration run, if it does not exit or at least gets
updated. Example:

.. code-block:: ini

    [meta]
    template = "pure-python"
    commit-id = "< commit-hash >"

    [python]
    with-appveyor = false
    with-legacy-python = true
    with-pypy = false
    with-docs = true
    with-sphinx-doctests = false

    [coverage]
    fail-under = 98

    [coverage-run]
    additional-config = [
        "omit =",
        "    src/foo/bar.py",
        ]

    [tox]
    additional-envlist = [
        "py37-slim",
        "py38-fat",
        ]
    testenv-commands-pre = [
        "{envbindir}/buildout -c ...",
        ]
    testenv-commands = [
        "{envbindir}/test {posargs:-cv}",
        "{envbindir}/test_with_gs {posargs:-cv}",
        ]
    testenv-additional = [
        "setenv =",
        "    ZOPE_INTERFACE_STRICT_IRO=1",
        ]
    coverage-command = "coverage run {envbindir}/test_with_gs []"

    [flake8]
    additional-config = [
        "# E221 multiple spaces before operator",
        "# E222 multiple spaces after operator",
        "per-file-ignores =",
        "    src/foo/bar.py: E221 E222",
        "ignore = D203",
        ]

    [manifest]
    additional-rules = [
        "include *.foo",
        "include *.bar",
        ]

    [check-manifest]
    additional-ignores = [
        "docs/html/*",
        "docs/source/_static/*",
        ]
    ignore-bad-ideas = [
        "src/foo/bar.mo",
        ]

    [isort]
    known_first_party = "Products.GenericSetup, Products.CMFCore"

    [github-actions]
    additional-config = [
        "- [\"3.8\",   \"py38-slim\"]",
        ]
    additional-install = [
        "sudo apt-get update && sudo apt-get install -y libxml2-dev libxslt-dev"
        ]

Meta Options
````````````

template
  Name of the configuration type, to be used as the template for the
  repository. Currently read-only.

commit-id
  Commit of the meta repository, which was used for the last configuration run.
  Currently read-only.


Python options
``````````````

with-appveyor
  Run the tests also on AppVeyor: true/false

with-legacy-python
  Run the tests even on Python 2.7, PyPy2 and Python 3.5: true/false

with-pypy
  Does the package support PyPy: true/false

with-docs
  Build the documentation via Sphinx: true/false

with-sphinx-doctests
  Run the documentation as doctest using Sphinx: true/false


Coverage options
````````````````

The corresponding section is named: ``[coverage]``.

fail-under
  A minimal value of code coverage below which a test failure is issued.


Coverage:run options
````````````````````

The corresponding section is named: ``[coverage-run]``.

additional-config
  Additional options for the ``[run]`` section of the coverage configuration.
  This option has to be a list of strings.

tox.ini options
```````````````

The corresponding section is named: ``[tox]``.

additional-envlist
  This option contains additional entries for the ``envlist`` in ``tox.ini``.
  The configuration for the needed additional environments can be added using
  ``testenv-additional`` (see below). This option has to be a list of strings
  without indentation.

testenv-commands-pre
  Replacement for the default ``commands_pre`` option in ``[testenv]`` of
  ``tox.ini``. This option has to be a list of strings without indentation.

testenv-commands
  Replacement for the default ``commands`` option in ``[testenv]`` of
  ``tox.ini``. This option has to be a list of strings without indentation.

testenv-additional
  Additional lines for the section ``[testenv]`` in ``tox.ini``.
  This option has to be a list of strings.

coverage-command
  This option replaces the coverage call in the section ``[testenv:coverage]``
  in ``tox.ini``. *Caution:* only the actual call to collect the coverage data
  is replaced. The calls to create the reporting are not changed. This option
  has to be a string. If it is not set or empty the default is used.


Flake8 options
``````````````

The corresponding section is named: ``[flake8]``.

additional-config
  Additional configuration options be added at the end of the flake8
  configuration section in ``setup.cfg``. *Caution:* This option has to be a
  list of strings so the leading white spaces and comments are preserved when
  writing the value to ``setup.cfg``.


Manifest options
````````````````

The corresponding section is named: ``[manifest]``.

additional-rules
  Additional rules to be added at the end of the MANIFEST.in file. This option
  has to be a list of strings.


Check-manifest options
``````````````````````

The corresponding section is named: ``[check-manifest]``.

additional-ignores
  Additional files to be ignored by ``check-manifest`` via its section in
  ``setup.cfg``. This option has to be a list of strings.

ignore-bad-ideas
  Ignore bad idea files/directories matching these patterns.

Isort options
`````````````

The corresponding section is named: ``[isort]``.

known_first_party
  This options defines the value for ``known_first_party`` in the ``isort``
  configuration. Please note the usage of underscores for the option name,
  which used to be consistent with the name of the option in ``isort``.
  This option has to be a single string. It defaults to the empty string.
  (Currently only the configuration type ``zope-product`` supports ``isort``
  configurations.)


GitHub Actions options
``````````````````````

The corresponding section is named: ``[github-actions]``.

additional-config
  Additional entries for the config matrix. This option has to be a list of
  strings without leading whitespace but it has to start with a hyphen.

additional-install
  Additional lines to be executed during the install dependencies step when
  running the tests on GitHub Actions. This option has to be a list of strings.


Hints
-----

* Calling ``config-package.py`` again updates a previously created pull request
  if there are changes made in the files ``config-package.py`` touches.

* Call ``bin/check-python-versions <path-to-package> -h`` to see how to fix
  version mismatches in the *lint* tox environment.


Calling a script on multiple repositories
-----------------------------------------

The ``config-package.py`` script only runs on a single repository. To update
multiple repositories at once you can use ``multi-call.py``. It runs a given
script on all repositories listed in a ``packages.txt`` file.

Usage
+++++

To run a script on all packages listed in a ``packages.txt`` file call
``multi-call.py`` the following way::

    $ bin/python multi-call.py <name-of-the-script.py> <path-to-packages.txt> <path-to-clones> <arguments-for-script>

See ``--help`` for details.

The script does the following steps:

1. It does the following steps for each line in the given ``packages.txt``
   which does not start with ``#``.
2. Check if there is a repository in ``<path-to-clones>`` with the name of the
   repository. If it does not exist: clone it. If it exists: clean the clone
   from changes, switch to ``master`` branch and pull from origin.
3. Call the given script with the package name and arguments for the script.

.. caution::

  Running this script discards any uncommitted changes in the repositories it
  runs on! There is no undo for this operation.
