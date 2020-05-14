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

* pure-python

    - Configuration for a pure python package which supports PyPy.

* pure-python-without-pypy

    - Configuration for a pure python package which does not supports PyPy,
      e. g. the packages Zope depends on.

Contents
--------

Each directory contains the following files:

* packages.txt

    - This file lists the packages which use the configuration in the
      directory.
* editorconfig

  - This file is copied to `.editorconfig` and allows developers to have a
    common editor configuration experience in all repos.
* gitignore

  - This file is copied to `.gitignore`.
* MANIFEST.in

  - Configuration file for the MANIFEST to include all needed files in sdist
    and wheel.
* setup.cfg

    - common setup.cfg, which should be copied to the repository of the
      package
* tox.ini

    - tox configuration, which should be copied to the repository of the
      package
* travis.yml

    - Config for TravisCI.

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

1. Add the package name to `packages.txt` of the selected configuration type if
   it is not yet added.
2. Copy `setup.cfg`, `tox.ini`, `.travis_yml`, `MANIFEST.in` and `.gitignore`
   to the repository.
3. Remove a possibly existing `.coveragerc` and `bootstrap.py`. (Coverage is
   now configured in `setup.cfg`.)
4. Run the tests via: ``tox``
5. Create a branch and a pull request.

After running the script you should manually do the following steps:

1. Check for changes in the updated repository and for the need of a change log
   entry over there.
2. Make sure TravisCI runs the ``master`` branch once a week. (See settings of
   the package on TravisCI).
3. Make sure the package is activated on https://coveralls.io by trying to add
   the repository name and making it active.
4. Check in possible changes in the zopefoundation/meta repository.


CLI arguments
+++++++++++++

The following arguments are supported.

--no-push
  Avoid pushing at the end of the configuration run.


Options
+++++++

It is possible to configure a deliberately small set of options a `.meta.cfg`
inside the package repository. This file also stores the template name and
commit id of the *meta* repository at the time of the run. This file is
generated during the configuration run, if it does not exit or at least gets
updated.

  .. code-block:: ini

    [meta]
    template = pure-python
    commit-id = < commit-hash >
    fail-under = 98


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


Hints
-----

* Calling ``config-package.py`` again updates a previously created pull request
  if there are changes made in the files ``config-package.py`` touches.

* Call ``bin/check-python-versions <path-to-package> -h`` to see how to fix
  version mismatches in the *lint* tox environment.
