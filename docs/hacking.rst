Hacking on :mod:`zope.meta`
===========================


Getting the Code
################

The main repository for :mod:`zope.meta` is in the Zope Foundation
Github repository:

  https://github.com/zopefoundation/meta

You can get a read-only checkout from there:

.. code-block:: sh

   $ git clone https://github.com/zopefoundation/meta.git

or fork it and get a writeable checkout of your fork:

.. code-block:: sh

   $ git clone git@github.com/jrandom/meta.git


Working in a Python virtual environment
#######################################

Installing
----------

You can use Python's standard ``venv`` package to create lightweight Python
development environments, where you can run the tests using nothing more
than the ``python`` binary in a virtualenv.  First, create a scratch
environment:

.. code-block:: sh

   $ python3.12 -m venv /tmp/hack-zope.meta

Next, install this package in "development mod" in the newly-created
environment:

.. code-block:: sh

   $ /tmp/hack-zope.meta/bin/pip install -e .

Running the tests
-----------------

You can install test tools using the ``test`` extra:

.. code-block:: sh

   $ /tmp/hack-zope.meta/bin/pip install -e ".[test]"


That command installs the tools needed to run
the tests:  in particular, the ``zope.testrunner`` (see
:external+testrunner:std:doc:`getting-started`) and
:external+coverage:std:doc:`index` tools.

To run the tests via ``zope.testrunner``:

.. code-block:: sh

   $ /tmp/hack-zope.meta/bin/zope-testrunner --test-path=src
   Running zope.testrunner.layer.UnitTests tests:
   ...

Running the tests under :mod:`coverage` lets you see how well the tests
cover the code:

.. code-block:: sh

   $ /tmp/hack-zope.meta/bin/coverage run -m zope.testrunner \
      --test-path=src
   ...
   $ coverage report -i -m --fail-under=100
   Name                                 Stmts   Miss Branch BrPart    Cover   Missing
   ----------------------------------------------------------------------------------
   ...


Building the documentation
--------------------------

:mod:`zope.meta` uses the nifty :mod:`Sphinx` documentation system
for building its docs.  Using the same virtualenv you set up to run the
tests, you can build the docs:

The ``docs`` command alias downloads and installs Sphinx and its dependencies:

.. code-block:: sh

   $ /tmp/hack-zope.meta/bin/pip install ".[docs]"
   ...
   $ /tmp/hack-zope.meta/bin/sphinx-build -b html -d docs/_build/doctrees docs docs/_build/html
   ...
   build succeeded.

   The HTML pages are in docs/_build/html.


Using :mod:`tox`
################


Running Tests on Multiple Python Versions
-----------------------------------------

`tox <http://tox.testrun.org/latest/>`_ is a Python-based test automation
tool designed to run tests against multiple Python versions.  It creates
a virtual environment for each configured version, installs the current
package and configured dependencies into each environment, and then runs the
configured commands.
   
:mod:`zope.meta` configures the following :mod:`tox` environments via
its ``tox.ini`` file:

- The ``lint`` environment runs various "code quality" tests on the source,
  and fails on any errors they find.

- The ``pyXX`` and ``pypy3`` environments each build an environment from the
  corresponding
  Python version, install :mod:`zope.meta` and testing dependencies,
  and runs the tests.  It then installs ``Sphinx`` and runs the doctest
  snippets.

- The ``coverage`` environment builds a virtual environment,
  installs :mod:`zope.meta` and dependencies, installs
  :mod:`coverage`, and runs the tests with statement and branch
  coverage.

- The ``docs`` environment builds a virtual environment, installs
  :mod:`zope.meta` and dependencies, installs ``Sphinx`` and
  dependencies, and then builds the docs and exercises the doctest snippets.

This example requires that you have a working ``python3.12`` on your path,
as well as installing ``tox``:

.. code-block:: sh

   $ tox -e py312
   py312: install_deps> python -I -m pip install 'setuptools<74' Sphinx
   ...
   py312: commands[0]> zope-testrunner --test-path=src -vc
   Running tests at level 1
   Running zope.testrunner.layer.UnitTests tests:
     Set up zope.testrunner.layer.UnitTests in 0.000 seconds.
     Running:
   .....

Running ``tox`` with no arguments runs all the configured environments,
including building the docs and testing their snippets.


Contributing to :mod:`zope.meta`
################################

Submitting a Bug Report
-----------------------

:mod:`zope.meta` tracks its bugs on Github:

  https://github.com/zopefoundation/meta/issues

Please submit bug reports and feature requests there.

Sharing Your Changes
--------------------

.. note::

   Please ensure that all tests are passing before you submit your code.
   If possible, your submission should include new tests for new features
   or bug fixes, although it is possible that you may have tested your
   new code by updating existing tests.

   Contributions to Plone/Zope Foundation packages require contributor status.
   Please see https://www.zope.dev/developer/becoming-a-committer.html.

If you have made changes you would like to share, the best route is to create a
branch in the GitHub repository and push changes there, which requires
`contributor status 
<https://www.zope.dev/developer/becoming-a-committer.html>`_. You can
also fork the GitHub repository, check out your fork, make your changes on a
branch in your fork, and then push them. A private fork makes it harder for
others and the package maintainers to work with your changes, so it is
discouraged. Either way, you can then submit a pull request from your branch:

  https://github.com/zopefoundation/meta/pulls
