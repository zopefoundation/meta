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

Moving package metadata from setup.py to pyproject.toml
-------------------------------------------------------

The script ``setup-to-pyproject`` parses package metadata out of the call to
the ``setup`` function in ``setup.py`` and moves it to ``pyproject.toml``.
The ``setup`` call in ``setup.py`` is then replaced with an invocation that
only uses those function arguments that have not been moved, such as arguments
related to building C code modules. These are currently not fully supported in
``pyproject.toml``.

.. note::

    The format and code of a ``setup.py`` file can vary widely. This script is
    a best effort attempt to cover the most common cases. Your mileage may
    vary. You should always view the conversion results yourself.

Usage
+++++

To convert package metadata from ``setup.py`` and move it to ``pyproject.toml``
call::

    $ bin/setup-to-pyproject <path-to-package>

The script supports these parameters:

- ``--dry-run``: Do not make any changes but print the contents of ``setup.py``
  and ``pyproject.toml`` with all changes to the console.
- ``--commit-msg``: To provide a custom commit message for the git commit.
- ``--no-commit``: Make changes, but do not commit them with git.
- ``--no-push``: Make changes and commit them, but do not push the commit.
- ``--no-tests``: Do not run the packages' ``tox`` tests after making changes.
- ``--branch``: Use a custom branch name for the change branch.
- ``--interactive``: Make changes and open the changed ``setup.py``
  and ``pyproject.toml`` files in the console text editor.


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
