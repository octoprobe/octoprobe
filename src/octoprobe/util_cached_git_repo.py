"""
GIT CLONE / WORKTREES
"""

from __future__ import annotations

import hashlib
import logging
import pathlib
import shutil

import slugify

from .util_constants import relative_cwd
from .util_subprocess import subprocess_run

logger = logging.getLogger(__file__)


GIT_CLONE_TIMEOUT_S = 60.0


class CachedGitRepo:
    """
    Lacy cloning of the repo.
    The repo will clone/updated once per pytest session.
    The url of the repo will be stored in a file "repo_url.txt".
    If the url changed, the whole repo will be cloned again.
    """

    singleton_cloned: set[str] = set()
    """
    A set of all directory names which have been cloned and updated.
    """

    def __init__(
        self,
        directory_cache: pathlib.Path,
        git_spec: str,
        prefix: str = "",
    ) -> None:
        assert isinstance(directory_cache, pathlib.Path)
        assert isinstance(git_spec, str)
        assert isinstance(prefix, str)
        # Example 'directory_cache': ~/git_cache
        # Example 'git_spec': https://github.com/micropython/micropython.git@main
        # Example 'prefix': 'micropython_mpbuild_'

        self.prefix = prefix
        self._directory_bare = directory_cache / "bare"
        self._directory_worktree = directory_cache / "worktree"
        self.git_spec = git_spec
        self.url, _, self.branch = git_spec.partition("@")

        self.directory_git_bare.parent.mkdir(parents=True, exist_ok=True)
        self.filename_git_url.write_text(self.url)

    @property
    def hash_obsolete(self) -> str:
        return hashlib.md5(self.url.encode("utf-8")).hexdigest()

    @property
    def slugify(self) -> str:
        return slugify.slugify(
            self.url,
            replacements=[
                ["https://", ""],
                ["http://", ""],
                [
                    ".git",
                    "",
                ],
            ],
        )

    @property
    def filename_git_url(self) -> pathlib.Path:
        return self._directory_bare / f"{self.slugify}.git_url.txt"

    @property
    def directory_git_bare(self) -> pathlib.Path:
        return self._directory_bare / f"{self.slugify}.git"

    @property
    def directory_git_worktree(self) -> pathlib.Path:
        return self._directory_worktree / f"{self.prefix}{self.slugify}"

    def clone(self, git_clean: bool) -> None:
        """
        Clone or update the git repo.
        """
        if self.directory_git_bare.name not in CachedGitRepo.singleton_cloned:
            CachedGitRepo.singleton_cloned.add(self.directory_git_bare.name)
            logger.info(
                f"git clone {self.git_spec} -> {relative_cwd(self.directory_git_bare)}"
            )
            self._clone_bare()

        logger.info(
            f"git worktree {self.git_spec} -> {relative_cwd(self.directory_git_worktree)}"
        )
        self._worktree_add(git_clean=git_clean)

    def _clone_bare(self) -> None:
        #
        # Clone or fetch bare repo
        #
        if self.directory_git_bare.is_dir():
            subprocess_run(
                args=[
                    "git",
                    "fetch",
                    "--all",
                ],
                cwd=self.directory_git_bare,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )
        else:
            subprocess_run(
                args=[
                    "git",
                    "clone",
                    "--bare",
                    "--filter=blob:none",
                    self.url,
                    self.directory_git_bare.name,
                ],
                cwd=self.directory_git_bare.parent,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )

    def _worktree_add(self, git_clean: bool) -> None:
        #
        # Add worktree or checkout
        #
        if git_clean:
            shutil.rmtree(self.directory_git_worktree, ignore_errors=True)

        if self.directory_git_worktree.is_dir():
            subprocess_run(
                args=[
                    "git",
                    "checkout",
                    "--force",
                    self.branch,
                ],
                cwd=self.directory_git_worktree,
                timeout_s=5.0,
            )
        else:
            subprocess_run(
                args=[
                    "git",
                    "worktree",
                    "add",
                    "-f",
                    str(self.directory_git_worktree),
                    self.branch,
                ],
                cwd=self.directory_git_bare,
                timeout_s=5.0,
            )
