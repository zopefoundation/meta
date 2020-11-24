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

--no-push
  Avoid pushing at the end of the configuration run.

--with-pypy
  Enable PyPy support. (Only needed one time as it is stored in .meta.cfg.)

--without-legacy-python
  The package does not support Python versions which reached their end-of-life.
  (Currently this means dropping support for Python 2.7 and 3.5.) This as well
  drops support for PyPy2. (Only needed one time as it is stored in .meta.cfg.)

--with-docs
  Enable building the documentation using Sphinx. (Only needed one time as it
  is stored in .meta.cfg.)

--with-sphinx-doctests
  Enable running the documentation as doctest using Sphinx. (Only needed one
  time as it is stored in .meta.cfg.)


Options
+++++++

It is possible to configure a deliberately small set of options a `.meta.cfg`
inside the package repository. This file also stores the template name and
commit id of the *meta* repository at the time of the run. This file is
generated during the configuration run, if it does not exit or at least gets
updated. Example:

.. code-block:: ini

    [meta]
    template = pure-python
    commit-id = < commit-hash >
    fail-under = 98
    with-pypy = False
    with-docs = True
    with-sphinx-doctests = False
    with-legacy-python = True
    additional-manifest-rules =
    additional-flake8-config =
      ignore = D203


Meta Options
------------

template
  Name of the template, the configuration was run.
  Currently read-only.

commit-id
  Commit of the meta repository, which was used for the last configuration run.
  Currently read-only.

fail-under
  A minimal value of code coverage below which a test failure is issued.

with-pypy
  Does the package support PyPy: True/False

with-legacy-python
  Run the tests even on Python 2.7, PyPy2 and Python 3.5: True/False

with-docs
  Build the documentation via Sphinx: True/False

with-sphinx-doctests
  Run the documentation as doctest using Sphinx: True/False

additional-manifest-rules
  Additional rules to be added at the end of the MANIFEST.in file.

additional-flake8-config
  Additional configuration options be added at the end of the flake8
  configuration section in ``setup.cfg``.


Hints
-----

* Calling ``config-package.py`` again updates a previously created pull request
  if there are changes made in the files ``config-package.py`` touches.

* Call ``bin/check-python-versions <path-to-package> -h`` to see how to fix
  version mismatches in the *lint* tox environment.
