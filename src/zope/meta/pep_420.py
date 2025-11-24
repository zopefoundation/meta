#!/usr/bin/env python3
##############################################################################
#
# Copyright (c) 2025 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import pathlib
import shutil

from .shared.call import call
from .shared.git import git_branch
from .shared.path import change_dir
from .shared.script_args import get_shared_parser


def main():
    parser = get_shared_parser(
        "Update a repository to PEP 420 native namespace.",
        interactive=True)
    args = parser.parse_args()
    path = args.path.absolute()

    if not (path / ".git").exists():
        raise ValueError(
            "`path` does not point to a git clone of a repository!")

    with change_dir(path) as cwd_str:
        cwd = pathlib.Path(cwd_str)
        bin_dir = cwd / "bin"
        branch_name = args.branch_name or "pep-420-native-namespace"
        updating = git_branch(branch_name)

        non_interactive_params = []
        if not args.interactive and args.commit:
            non_interactive_params = ["--no-input"]
        else:
            args.commit = False

        call(bin_dir / "bumpversion", "--breaking", *non_interactive_params)
        call(
            bin_dir / "addchangelogentry",
            "Replace ``pkg_resources`` namespace with PEP 420"
            " native namespace."
        )

        setup_py = []
        for line in (path / "setup.py").read_text().splitlines():
            if "from setuptools import find_packages" in line:
                continue
            elif "namespace_packages" in line:
                continue
            elif "packages=" in line:
                continue
            elif "package_dir=" in line:
                continue
            elif "zope.testrunner" in line:
                setup_py.append(
                    line.replace("zope.testrunner", "zope.testrunner >= 6.4")
                )
            else:
                setup_py.append(line)

        (path / "setup.py").write_text("\n".join(setup_py) + "\n")

        for src_dir_cont in (path / "src").iterdir():
            if not src_dir_cont.is_dir():
                continue
            pkg_init = src_dir_cont / "__init__.py"
            if pkg_init.exists():
                pkg_init.unlink()
            for pkg_dir_cont in src_dir_cont.iterdir():
                if not pkg_dir_cont.is_dir():
                    continue
                sub_pkg_init = pkg_dir_cont / "__init__.py"
                if sub_pkg_init.exists():
                    if "pkg_resources" in sub_pkg_init.read_text():
                        sub_pkg_init.unlink()

        if args.commit:
            print("Adding all changes ...")
            call("git", "add", ".")

        if args.run_tests:
            tox_path = shutil.which("tox") or (cwd / "bin" / "tox")
            call(tox_path, "-p", "auto")

        if args.commit:
            print("Committing and pushing all changes ...")
            call("git", "commit", "-m", "Switch to PEP 420 native namespace.")
            call("git", "push", "--set-upstream", "origin", branch_name)
            if updating:
                print("Updated the previously created PR.")
            else:
                print(
                    "Are you logged in via `gh auth login` to create a PR?"
                    " (y/N)?", end=" ",
                )
                if input().lower() == "y":
                    call(
                        "gh",
                        "pr",
                        "create",
                        "--fill",
                        "--title",
                        "Switch to PEP 420 native namespace.",
                    )
                else:
                    print("If everything went fine up to here:")
                    print("Create a PR, using the URL shown above.")
        else:
            print("Applied all changes. Please check and commit manually.")
