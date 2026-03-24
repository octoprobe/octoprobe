#!/usr/bin/env python3
"""
Build and upload Sphinx documentation for all octoprobe projects.

Replaces run_sphinx_copy.sh and run_sphinx_upload.sh.
"""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import jinja2


@dataclasses.dataclass
class Repo:
    directory: str
    name: str | None = None
    entry: str = "/big_picture"
    is_origin: bool = False
    automodule: bool = False

    def __post_init__(self) -> None:
        if self.name is None:
            self.name = self.directory

    @property
    def docs_dir(self) -> Path:
        return BASE_DIR / self.directory / "docs"

    def get_dir(self, relative_path: str, mandatory: bool = True) -> Path:
        directory = self.docs_dir / relative_path
        if not directory.is_dir():
            if mandatory:
                raise FileNotFoundError(f"Directory does not exist: {directory}")
        return directory


REPO_ORIGIN = Repo("octoprobe", name="Octoprobe", automodule=True, is_origin=True)
REPOS: list[Repo] = [
    REPO_ORIGIN,
    Repo("tentacle", name="Tentacle"),
    Repo("octohub4", name="Octohub4"),
    Repo("testbed_heatguard", automodule=True),
    Repo("testbed_showcase", automodule=True, entry="/introduction/index"),
    Repo("testbed_micropython", entry="/user_guide/index"),
]

BASE_DIR = Path.home() / "work_octoprobe"
SSH_HOST = "www-insecure@www.maerki.com"
SSH_REMOTE_DIR = "/home/www/htdocs_insecure/octoprobe"

_REDIRECT_TEMPLATE = jinja2.Template("""
{{ repo.name }}
===============================

.. meta::
    :http-equiv=refresh: 0; url=https://www.octoprobe.org/{{ repo.directory }}/{{ repo.entry }}.html
""")

_INDEX_TOP_TEMPLATE = jinja2.Template("""
.. Restructured text comment: IGNORE_SECTION_CHECK

{{ repo.name }}
====================

{% if repo.automodule -%}
.. automodule:: {{ repo.directory }}
    :members:
{%- endif %}

.. toctree::
    :caption: Contents:

{% for link in links %}    {{ link }}
{% endfor %}


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
""")


class SphinxProject:
    """Prepare docs directories: create redirect stubs and propagate shared files."""

    def __init__(self, repo: Repo) -> None:
        self.repo = repo

    def create_top_redirects(self) -> None:
        """Create docs/top/ with redirect .rst stubs pointing to all other projects."""
        top_dir = self.repo.docs_dir / "top"
        top_dir.mkdir(parents=True, exist_ok=True)
        for rst_file in top_dir.glob("*.rst"):
            rst_file.unlink()
        for other in REPOS:
            if self.repo is other:
                continue
            rst_file = top_dir / f"octoprobe_{other.directory}.rst"
            rst_file.write_text(_REDIRECT_TEMPLATE.render(repo=other))

    def create_index_top(self) -> None:
        """Create the top-level index for the origin repo using Jinja2."""

        def iter_links() -> Iterator[str]:
            for other_repo in REPOS:
                if other_repo is self.repo:
                    yield "index.rst"
                else:
                    yield f"top/octoprobe_{other_repo.directory}"

        index_top_file = self.repo.docs_dir / "index_top.rst"
        index_top_file.write_text(
            _INDEX_TOP_TEMPLATE.render(
                repo=self.repo,
                links=iter_links(),
            )
        )

    def copy_shared_files(self) -> None:
        """Copy shared _static/_templates dirs and config files from octoprobe docs."""
        for sub_dir in ("_static", "_templates"):
            dst = self.repo.docs_dir / sub_dir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(REPO_ORIGIN.docs_dir / sub_dir, dst)

        for filename in ("conf.py", "run_sphinx_upload.py", "Makefile"):
            shutil.copy2(REPO_ORIGIN.docs_dir / filename, self.repo.docs_dir / filename)

    def do_upload(self) -> None:
        html_dir = self.repo.get_dir("_build/html")

        print(f"Directory upload: {html_dir}")
        subprocess.run(["make", "-C", str(self.repo.docs_dir), "clean"], check=True)
        subprocess.run(["make", "-C", str(self.repo.docs_dir), "html"], check=True)

        # Stream the built HTML to the remote server via SSH, re-rooting the
        # tar archive under the repo name on the remote side.
        tar_cmd = [
            "tar",
            "cf",
            "-",
            "-C",
            str(html_dir),
            "--transform",
            f"s,^\\.,{self.repo.directory},",
            ".",
        ]
        ssh_cmd = ["ssh", SSH_HOST, "tar", "xf", "-", "-C", SSH_REMOTE_DIR]

        with subprocess.Popen(tar_cmd, stdout=subprocess.PIPE) as tar_proc:
            with subprocess.Popen(ssh_cmd, stdin=tar_proc.stdout) as ssh_proc:
                if tar_proc.stdout:
                    tar_proc.stdout.close()
                ssh_proc.wait()
            tar_proc.wait()

        if tar_proc.returncode != 0:
            raise subprocess.CalledProcessError(tar_proc.returncode, tar_cmd)
        if ssh_proc.returncode != 0:
            raise subprocess.CalledProcessError(ssh_proc.returncode, ssh_cmd)


def main() -> None:
    for repo in REPOS:
        project = SphinxProject(repo)
        project.create_top_redirects()
        project.create_index_top()
        if repo.is_origin:
            continue
        project.copy_shared_files()

    for repo in REPOS:
        project = SphinxProject(repo)
        project.do_upload()


if __name__ == "__main__":
    main()
