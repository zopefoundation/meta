Other topics
============

Configuring a package for PyPI Trusted Publishing
-------------------------------------------------

With the introduction of the ``trusted-publishing`` option you can now use the
so-called Trusted Publishing mechanism to automatically create release packages
(source distribution ``tar.gz`` files and wheels) and publish them to PyPI. To
make this work you will need to make changes in several places:

Package configuration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the following to your ``.meta.toml`` and re-run the ``config-package``
script to add a publishing step to the GitHub ``tests`` workflow:

.. code-block:: toml

    [pypi]
    trusted-publishing = true

Commit and push the changes to GitHub.

GitHub configuration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Log into GitHub and bring up the repository page for your package. Then...

- go to Settings -> Environments
- add new environment "pypi"
- select "Required reviewers" and add teams or individual GitHub user accounts
  that must approve the package publishing process. GitHub calls this
  "deployment". For Zope Foundation repositories you should add the team
  ``zopefoundation/release-managers``.
- select "Allow administrators to bypass" so that repository- and
  organization-level administrators  can approve releases without being in the
  Release Managers group
- Under `Deployment branches and tags` you should limit the branches from which
  a release can be made. A good start would be to specify `Protected branches
  only`, because those usually match the main and older release branches.

PyPI configuration changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

Log into PyPI and bring up the page for your package. Then...

- click on "Manage project" and then "Publishing" on the left
- fill in and submit the "Add a new publisher form". The following values will
  work with the ``trusted-publishing`` setting for Zope Foundation
  repositories:

    - Owner: zopefoundation
    - Repository name: (repo name)
    - Workflow name: tests.yml
    - Environment name: pypi

Test publishing
~~~~~~~~~~~~~~~

With the changes above in place you can test the trusted publishing process by
preparing a new package release and then pushing its tag to GitHub. On GitHub,
visit the `Actions` tab on the package's page and select the workflow run for
your new tag. You should see a job named `Publish to PyPI` on the left side
that you can click to see the logs. If this job finishes successfully, it will
create a new release and upload a wheel and a source distribution to PyPI.
