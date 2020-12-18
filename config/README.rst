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

  - Configuration for a pure python package which supports PyPy.


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

* MANIFEST.in.jj2

  - Configuration file for the MANIFEST to include all needed files in sdist
    and wheel.

* setup.cfg

  - common setup.cfg, which should be copied to the repository of the
    package

* tox.ini.jj2

  - tox configuration, which should be copied to the repository of the
    package

* tests.yml.jj2

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

--type
  Define the configuration type (see `Types`_ section above) to be used for the
  repository. (Only needed one time as it is stored in .meta.toml.)

--no-push
  Avoid pushing at the end of the configuration run.

--with-pypy
  Enable PyPy support. (Only needed one time as it is stored in .meta.toml.)

--without-legacy-python
  The package does not support Python versions which reached their end-of-life.
  (Currently this means dropping support for Python 2.7 and 3.5.) This as well
  drops support for PyPy2. (Only needed one time as it is stored in
  .meta.toml.)

--with-docs
  Enable building the documentation using Sphinx. (Only needed one time as it
  is stored in .meta.toml.)

--with-sphinx-doctests
  Enable running the documentation as doctest using Sphinx. (Only needed one
  time as it is stored in .meta.toml.)

--branch
  Define a specific git branch name to be created for the changes. By default
  the script creates one which includes the name of the configuration type.


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

fail-under
  A minimal value of code coverage below which a test failure is issued.


Coverage:run options
````````````````````

additional-config
  Additional options for the ``[run]`` section of the coverage configuration.
  This option has to be a list of strings.


Flake8 options
``````````````

additional-config
  Additional configuration options be added at the end of the flake8
  configuration section in ``setup.cfg``. *Caution:* This option has to be a
  list of strings so the leading white spaces and comments are preserved when
  writing the value to ``setup.cfg``.


Manifest options
````````````````

additional-rules
  Additional rules to be added at the end of the MANIFEST.in file. This option
  has to be a list of strings.


Check-manifest options
``````````````````````

additional-ignores
  Additional files to be ignored by ``check-manifest`` via its section in
  ``setup.cfg``. This option has to be a list of strings.

ignore-bad-ideas
  Ignore bad idea files/directories matching these patterns.

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
