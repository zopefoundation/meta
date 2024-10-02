Using :mod:`zope.meta`
======================


Purpose
-------

Bring the configuration of the zopefoundation packages into a common state and
keep it there.


Configuration types
-------------------

This directory contains the configuration directories for different types of
packages:

* buildout-recipe

  - Configuration for a zc.buildout recipe. It is tested using multiple
    processes, so coverage has to be configured in a special way. (Supports
    pure Python packages which also run on PyPy.)

* c-code

  - Configuration for package containing C code besides the Python one.

* pure-python

  - Configuration for a pure Python package.

* zope-product

  - Configuration for a pure Python package which uses zc.buildout inside
    ``tox.ini`` to be able to pin the installed dependency versions the same
    way ``buildout.cfg`` does it.

* toolkit

  - Configuration used for the zopetoolkit and groktoolkit repositories.


Configuration templates
-----------------------

Each configuration type folder can override the default configuration in the
folder ``default`` by providing one or more of these files:

* packages.txt

  - This file lists the packages which use the configuration in the
    directory.

* CONTRIBUTING.md

  - This file is copied as is. It allows developers to easily find our
    contributing guidelines in the root of the repository.

* editorconfig

  - This file is copied to `.editorconfig` and allows developers to have a
    common editor configuration experience in all repos.

* gitignore.j2

  - This file is copied to `.gitignore` and can be appended trough
    configuration in ``.meta.cfg``.

* MANIFEST.in.j2

  - Configuration file for the MANIFEST to include all needed files in sdist
    and wheel.

* readthedocs.yaml.j2

  - Configuration for https://readthedocs.org to build the documentation over
    there if the package has documentation.

* setup.cfg.j2

  - common setup.cfg, which should be copied to the repository of the
    package

* tox.ini.j2

  - tox configuration, which should be copied to the repository of the
    package

* tests.yml.j2

  - Configuration for GitHub actions.


The ``config-package`` script
-----------------------------

The ``config-package`` script applies package configuration in a given Python
package.

Preparation
+++++++++++

The scripts needs a ``venv`` with some packages installed::

    $ python3.11 -m venv .
    $ bin/pip install .

To use the configuration provided here in a package call the following script::

    $ bin/config-package <path-to-package> --type <config-type-name> [<additional-options>]

See ``--help`` for details.

The script does the following steps:

#. Add the package name to ``packages.txt`` of the selected configuration type
   if it is not yet added.
#. Copy ``setup.cfg``, ``tox.ini``, ``tests.yml``, ``MANIFEST.in``,
   ``.readthedocs.yaml`` (if needed), and ``.gitignore`` to the repository.
#. Create or update a ``pyproject.toml`` project configuration file.
#. Remove a possibly existing ``.coveragerc`` and ``bootstrap.py``. (Coverage
   is now configured in ``tox.ini`` for packages which are no buildout
   recipes.)
#. Run the tests via: ``tox``. The ``tox`` script may be either on the current
   ``$PATH`` or in the ``bin`` subfolder of the current working directory.
#. Create a branch and a pull request. (Prevent an automatic commit of all
   changes with the command line switch ``--no-commit``, or an automatic push
   to GitHub using the command line switch ``--no-push``.)

After running the script you should manually do the following steps:

#. Check for changes in the updated repository and for the need of a change log
   entry over there.
#. Make sure the package is activated on https://coveralls.io by trying to add
   the repository name and making it active.
#. Check in possible changes in the zopefoundation/meta repository.


CLI arguments
+++++++++++++

The following arguments are supported.

--commit-msg=MSG
  Use MSG as commit message instead of an artificial one.

--no-commit
  Don't automatically commit changes after the configuration run. Implies
  --no-push.

--no-push
  Avoid pushing at the end of the configuration run.

--branch
  Define a specific git branch name to be created for the changes. By default
  the script creates one which includes the name of the configuration type.

The following options are only needed one time as their values are stored in
``.meta.toml.``.

--type
  Define the configuration type (see `Configuration types`_ section above) to
  be used for the repository.

--with-macos
  Enable running the tests on macOS on GitHub Actions.

--with-windows
  Enable running the tests on Windows on GitHub Actions.

--with-pypy
  Enable PyPy support.

--with-future-python
  The package supports the next upcoming Python version which does not yet have
  a final release thus it is not yet generally supported by the zopefoundation
  packages.

--with-docs
  Enable building the documentation using Sphinx. This will also create a
  configuration file `.readthedocs.yaml` for integration with
  https://readthedocs.org.

--with-sphinx-doctests
  Enable running the documentation as doctest using Sphinx.


Options
+++++++

It is possible to configure some options in a `.meta.toml` file
inside the package repository. This file also stores the template name and
commit id of the *meta* repository at the time of the run. This file is
generated during the configuration run, if it does not exist or at least gets
updated. Example:

.. code-block:: ini

    [meta]
    template = "pure-python"
    commit-id = "< commit-hash >"

    [python]
    with-pypy = false
    with-docs = true
    with-sphinx-doctests = false
    with-macos = false
    with-windows = false

    [coverage]
    fail-under = 98

    [coverage-run]
    additional-config = [
        "omit =",
        "    src/foo/bar.py",
        ]
    source = "src"

    [tox]
    additional-envlist = [
        "py311-slim",
        "py312-fat",
        ]
    testenv-additional-extras = [
        "extra-feature",
        ]
    testenv-commands-pre = [
        "{envbindir}/buildout -c ...",
        ]
    testenv-commands = [
        "{envbindir}/test {posargs:-cv}",
        "{envbindir}/test_with_gs {posargs:-cv}",
        ]
    testenv-deps = [
        "zope.testrunner",
        ]
    testenv-setenv = [
        "ZOPE_INTERFACE_STRICT_IRO=1",
    ]
    testenv-additional = [
        "passenv =",
        "    DISPLAY",
        ]
    coverage-basepython = "python3.9"
    coverage-command = [
        "coverage run {envbindir}/test_with_gs []",
        ]
    coverage-setenv = [
        "COVERAGE_HOME={toxinidir}",
        ]
    coverage-additional = [
        "depends = py312,docs",
        ]
    docs-deps = [
        "urllib3 < 2",
        ]

    [flake8]
    additional-config = [
        "# D203 1 blank line required before class docstring",
        "# E221 multiple spaces before operator",
        "# E222 multiple spaces after operator",
        "# W503 Line break occurred before a binary operator",
        "per-file-ignores =",
        "    src/foo/bar.py: E221 E222",
        "extend-ignore = D203, W503",
        ]
    additional-sources = "testproj foo bar.py"

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
    known_third_party = "ipaddress, PasteDeploy"
    known_zope = "AccessControl, Acquisition, App"
    known_first_party = "Products.GenericSetup, Products.CMFCore"
    additional-sources = "{toxinidir}/tests {toxinidir}/bar.py"

    [github-actions]
    services = [
        "postgres:",
        "  image: postgres",
        ]
    additional-config = [
        "- [\"3.8\",   \"py38-slim\"]",
        ]
    additional-exclude = [
        "- { os: windows, config: [\"pypy-3.10\", \"pypy3\"] }",
        "- { os: macos, config: [\"pypy-3.10\", \"pypy3\"] }",
        ]
    steps-before-checkout = [
        "- name: \"Set some Postgres settings\"",
        "  run: ...",
        ]
    additional-install = [
        "sudo apt-get update && sudo apt-get install -y libxml2-dev libxslt-dev",
        "pip install tox-factor"
        ]
    additional-build-dependencies = [
        "cffi",
        "python-ldap",
        ]
    test-enviroment = [
        "TEST_DSN: 'host=localhost port=5432 user=postgres'"
        ]
    test-commands = [
        "tox -f ${{ matrix.config[1] }}",
        ]

    [c-code]
    manylinux-install-setup = [
        "export CFLAGS=\"-pipe\"",
        ]
    manylinux-aarch64-tests = [
        "cd /io/",
        "\"${PYBIN}/pip\" install tox",
        "\"${PYBIN}/tox\" -e py",
        "cd ..",
        ]
    require-cffi = true

    [zest-releaser]
    options = [
        "prereleaser.before =",
        "    zest.pocompile.compile.main",
        ]

    [git]
    ignore = [
        "*.mo",
        ]

    [pre-commit]
    teyit-exclude = "App/tests/fixtures/error\.py"

    [readthedocs]
    build-extra = [
        "apt_packages:",
        "  - libldap2-dev",
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

with-macos
  Run the tests also on macOS on GitHub Actions: true/false, default: false

with-windows
  Run the tests also on Windows on GitHub Actions: true/false, default: false

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

source
  This option defines the value of ``source`` in the coverage ``[run]``
  section. This option has to be a string. It defaults to the name of the
  package if it is not set.


tox.ini options
```````````````

The corresponding section is named: ``[tox]``.

additional-envlist
  This option contains additional entries for the ``envlist`` in ``tox.ini``.
  The configuration for the needed additional environments can be added using
  ``testenv-additional`` (see below). This option has to be a list of strings
  without indentation.

testenv-additional-extras
  Additional entries for the ``extras`` option in ``[testenv]`` of
  ``tox.ini``.  This option has to be a list of strings without indentation.

testenv-commands-pre
  Replacement for the default ``commands_pre`` option in ``[testenv]`` of
  ``tox.ini``. This option has to be a list of strings without indentation.

testenv-commands
  Replacement for the default ``commands`` option in ``[testenv]`` of
  ``tox.ini``. This option has to be a list of strings without indentation.

testenv-deps
  Additional dependencies for the ``deps`` option in ``[testenv]`` of
  ``tox.ini``. This option has to be a list of strings without indentation.
  It is empty by default.

testenv-setenv
  Set the value of the ``setenv`` option in ``[testenv]`` of ``tox.ini``.
  Depending in the template used this might be an addition to the predefined
  values for this option. This option has to be a list of strings.

testenv-additional
  Additional lines for the section ``[testenv]`` in ``tox.ini``.
  This option has to be a list of strings.

coverage-basepython
  This option replaces the value for the ``basepython`` option in the section
  ``[testenv:coverage]``. This option has to be a string. The default value is
  ``python3``.

coverage-command
  This option replaces the coverage call in the section ``[testenv:coverage]``
  in ``tox.ini``. *Caution:* only the actual call to collect the coverage data
  is replaced. The calls to create the reporting are not changed. This option
  has to be a list or a string. If it is not set or empty the default is used.

coverage-setenv
  This option defines the contents for the option ``setenv`` in the section
  ``[testenv:coverage]`` in ``tox.ini``. If it has a default value (e. g. as
  in the buildout-recipe template), the default value is replaced by the value
  given here. This option has to be a list of strings.

coverage-additional
  This option allows to add additional lines below ``[testenv:coverage]`` in
  ``tox.ini``. This option has to be a list of strings.

docs-deps
  This option allows to add additional install dependencies for
  ``[testenv:docs]`` in ``tox.ini``. This option has to be a list of strings
  and is empty by default. Caution: The values set for this option override
  the ones set in ``[testenv]``.


Flake8 options
``````````````

The corresponding section is named: ``[flake8]``.

additional-config
  Additional configuration options be added at the end of the flake8
  configuration section in ``setup.cfg``. *Caution:* This option has to be a
  list of strings so the leading white spaces and comments are preserved when
  writing the value to ``setup.cfg``.

additional-sources
  Sometimes not only ``src`` and ``setup.py`` contain Python code to be checked
  by flake8. Additional files or directories can be configured here. This
  option is a string. The sources inside have to be space separated.


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
  Ignore bad idea files/directories matching these patterns. This option has to
  be a list of strings.


Isort options
`````````````

The corresponding section is named: ``[isort]``.

Please note the usage of underscores for the option name, which used to be
consistent with the name of the option in ``isort``.

Currently only the configuration type ``zope-product`` supports ``isort``
configurations.

known_third_party
  This option defines the value for ``known_third_party`` in the ``isort``
  configuration. This option has to be a string. It defaults to
  ``"docutils, pkg_resources, pytz"``.

known_zope
  This option defines the value for ``known_zope`` in the ``isort``
  configuration. This option has to be a string. It defaults to the empty
  string.

known_first_party
  This option defines the value for ``known_first_party`` in the ``isort``
  configuration. This option has to be a string. It defaults to the empty
  string.

known_local_folder
  This option defines the value for ``known_local_folder`` in the ``isort``
  configuration. This option has to be a string. It defaults to the empty
  string.

additional-sources
  This option defines additional files and/or directories where ``isort``
  should be applied. This option has to be a string. It defaults to the empty
  string.

additional-config
  Additional options for the ``[isort]`` section.  This option has to be a
  list of strings.


GitHub Actions options
``````````````````````

The corresponding section is named: ``[github-actions]``.

services
  Lines which will be added in the services section of the GitHub Actions build
  section. This option has to be a list of strings.

additional-config
  Additional entries for the config matrix. This option has to be a list of
  strings without leading whitespace but it has to start with a hyphen.

additional-exclude
  Additional entries to exclude from the config matrix. This option has to be a
  list of strings without leading whitespace but it has to start with a hyphen.

steps-before-checkout
  Add steps definitions to be inserted into ``tests.yml`` before the checkout
  action i. e. as the first step. This option has to be a list of strings.

additional-install
  Additional lines to be executed during the install dependencies step when
  running the tests on GitHub Actions. This option has to be a list of strings.
  For the template ``c-code`` this option is currently used to replace how to
  install the package itself and run tests and coverage.

additional-build-dependencies
  Additional Python packages to install into the virtual environment before
  building a package with C extensions. This is used for the ``c-code``
  template to work around issues on macOS where setuptools attempts to retrieve
  wheels and convert them to eggs multiple times.

test-environment
  Environment variables to be set during the test run. This option has to be a
  list of strings.

test-commands
  Replacement for the test command in ``tests.yml``.
  This option has to be a list of strings.


C-code options
``````````````

The corresponding section is named: ``[c-code]`` it is used only for packages
built with the template ``c-code``.

manylinux-install-setup
  Additional setup steps necessary in ``manylinux-install.sh``. This option has
  to be a list of strings and defaults to an empty list.

manylinux-aarch64-tests
  Replacement for the tests against the aarch64 architecture. This option has
  to be a list of strings and defaults to testing using ``tox`` against all
  supported Python versions, which could be too slow for some packages.

require-cffi
  Require to install ``cffi`` via pip before trying to build the package. This
  is needed for some packages to circumvent build problems on MacOS. This
  option has to be a boolean (true or false).


zest.releaser options
`````````````````````

The corresponding section is named: ``[zest-releaser]`` (with an ``-`` instead
of the ``.``).

options
  (Additional) options used to configure ``zest.releaser``. This option has to
  be a list of strings and defaults to an empty list.


git options
```````````

The corresponding section is named: ``[git]``.

ignore
  Additional lines to be added to the ``.gitignore`` file. This option has to
  be a list of strings and defaults to an empty list.


pre-commit options
``````````````````

The corresponding section is named: ``[pre-commit]``.

teyit-exclude
  Regex for files to be hidden from teyit. It fails on files containing syntax
  errors. This option has to be a string and is omitted when not defined.


ReadTheDocs options
```````````````````

The corresponding section is named: ``[readthedocs]``.

build-extra
  Additional lines to be added to the ``build`` configuration in the
  ReadTheDocs configuration file ``.readthedocs.yaml``. This option has to
  be a list of strings and defaults to an empty list.


Configuration script hints
--------------------------

* Calling ``config-package`` again updates a previously created pull request
  if there are changes made in the files ``config-package`` touches.

* Call ``bin/check-python-versions <path-to-package> -h`` to see how to fix
  version mismatches in the *lint* tox environment.


Other helper scripts
====================

Updating to the currently supported Python versions
---------------------------------------------------

There is a script `update-python-support` for updating a repository to
the currently supported Python versions as defined in ``shared/package.py``.


Usage
+++++

To update a repository to the currently supported Python versions call::

    $ bin/update-python-support <path-to-package>

It supports a parameter ``--interactive`` to gather user input for its changes
and not automatically commit them. It also supports a parameter ``--no-commit``
that prevents automatic commits but attempts to cut down on interactively
asking for user input. Some of that still happens due to limitations
of the ``zest.releaser`` scripts used by ``update-python-support``.


Calling a script on multiple repositories
-----------------------------------------

The ``config-package`` script only runs on a single repository. To update
multiple repositories at once you can use ``multi-call``. It runs a given
script on all repositories listed in a ``packages.txt`` file.


Usage
+++++

To run a script on all packages listed in a ``packages.txt`` file call
``multi-call`` the following way::

    $ bin/multi-call <name-of-the-script> <path-to-packages.txt> <path-to-clones> <arguments-for-script>

See ``--help`` for details.

The script does the following steps:

#. It does the following steps for each line in the given ``packages.txt``
   which does not start with ``#``.
#. Check if there is a repository in ``<path-to-clones>`` with the name of the
   repository. If it does not exist: clone it. If it exists: clean the clone
   from changes, switch to ``master`` branch and pull from origin.
#. Call the given script with the package name and arguments for the script.

.. caution::

  Running this script stashes any uncommitted changes in the repositories,
  run `git stash pop` to recover them.


Re-enabling GitHub Actions
--------------------------

After a certain period of time (currently 60 days) without commits GitHub
automatically disables Actions. They can be re-enabled manually per repository.
There is a script to do this for all repositories. It does no harm if Actions
is already enabled for a repository.


Preparation
+++++++++++

* Install GitHub's CLI application, see https://github.com/cli/cli.

* Authorize using the application:

  - ``gh auth login``
  - It is probably enough to do it once.


Usage
+++++

To run the script just call it::

    $ bin/re-enable-actions
