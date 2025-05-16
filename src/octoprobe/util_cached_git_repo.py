"""
GIT CLONE / WORKTREES
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
import pathlib
import re
import shutil

import slugify

from .util_constants import relative_cwd
from .util_subprocess import subprocess_run

logger = logging.getLogger(__file__)
GIT_CLONE_TIMEOUT_S = 60.0

RE_GIT_SPEC = re.compile(r"^(?P<url>(.+?://)?.+?)(\+(?P<pr>.+?))?(@(?P<branch>.+))?$")
"""
https://github.com/micropython/micropython.git
https://github.com/micropython/micropython.git+17232
https://github.com/micropython/micropython.git@1.25.0
https://github.com/micropython/micropython.git+17232@1.25.0
"""


@dataclasses.dataclass(frozen=True, repr=True)
class GitSpec:
    """
    https://github.com/micropython/micropython.git+17232@1.25.0
    """

    git_spec: str
    "https://github.com/micropython/micropython.git+17232@1.25.0"
    url: str
    "https://github.com/micropython/micropython.git"
    pr: str | None
    "17232"
    branch: str | None
    "1.25.0"

    @staticmethod
    def parse(git_ref: str) -> GitSpec:
        match = RE_GIT_SPEC.match(git_ref)
        if match is None:
            raise ValueError(f"Failed to parse git_spec '{git_ref}'!")

        return GitSpec(
            git_spec=git_ref,
            url=match.group("url"),
            pr=match.group("pr"),
            branch=match.group("branch"),
        )


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
        self.git_spec = GitSpec.parse(git_ref=git_spec)

        logger.debug(f"{self.git_spec.git_spec} -> {self.git_spec}")

        self.directory_git_bare.parent.mkdir(parents=True, exist_ok=True)
        self.filename_git_url.write_text(self.git_spec.url)

    @property
    def hash_obsolete(self) -> str:
        return hashlib.md5(self.git_spec.url.encode("utf-8")).hexdigest()

    @property
    def slugify(self) -> str:
        return slugify.slugify(
            self.git_spec.url,
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
                f"git clone {self.git_spec.git_spec} -> {relative_cwd(self.directory_git_bare)}"
            )
            self._clone_bare()

        logger.info(
            f"git worktree {self.git_spec.git_spec} -> {relative_cwd(self.directory_git_worktree)}"
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
                    "origin",
                    "+refs/heads/*:refs/remotes/origin/*",
                ],
                cwd=self.directory_git_bare,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )
            subprocess_run(
                args=[
                    "git",
                    "fetch",
                    "--all",
                    "--prune",
                    "--tags",
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
                    "--depth=1",  # This is fast and will provoke if fetch does not work
                    "--filter=blob:none",
                    self.git_spec.url,
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

        if self.git_spec.branch is not None:
            args = [
                "git",
                "fetch",
                "origin",
                "+refs/heads/*:refs/remotes/origin/*",
            ]
            subprocess_run(
                args=args,
                cwd=self.directory_git_bare,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )

            # Force reset the branch to match the remote
            args = [
                "git",
                "branch",
                "-f",
                self.git_spec.branch,
                f"origin/{self.git_spec.branch}",
            ]
            subprocess_run(
                args=args,
                cwd=self.directory_git_bare,
                timeout_s=GIT_CLONE_TIMEOUT_S,
                success_returncodes=[0, 128],
            )

        #
        # Add worktree or checkout
        #
        if self.directory_git_worktree.is_dir():
            args = [
                "git",
                "checkout",
                "--force",
                "--detach",  # https://github.com/octoprobe/testbed_micropython/issues/14
            ]
            if self.git_spec.branch is not None:
                args.append(self.git_spec.branch)
            subprocess_run(args=args, cwd=self.directory_git_worktree, timeout_s=5.0)

        else:
            args = [
                "git",
                "worktree",
                "add",
                "-f",
                str(self.directory_git_worktree),
            ]
            if self.git_spec.branch is not None:
                args.append(self.git_spec.branch)
            subprocess_run(
                args=args, cwd=self.directory_git_bare, timeout_s=GIT_CLONE_TIMEOUT_S
            )

        if self.git_spec.pr is not None:
            #
            # checkout the PR
            #
            subprocess_run(
                args=[
                    "git",
                    "fetch",
                    "origin",
                    f"pull/{self.git_spec.pr}/head:pr-{self.git_spec.pr}",
                ],
                cwd=self.directory_git_worktree,
                timeout_s=5.0,
            )
            subprocess_run(
                args=[
                    "git",
                    "checkout",
                    "--force",
                    "--detach",  # https://github.com/octoprobe/testbed_micropython/issues/14
                    f"pr-{self.git_spec.pr}",
                ],
                cwd=self.directory_git_worktree,
                timeout_s=5.0,
            )
            if self.git_spec.branch is not None:
                #
                # rebase the PR
                #
                subprocess_run(
                    args=[
                        "git",
                        "rebase",
                        self.git_spec.branch,
                    ],
                    cwd=self.directory_git_worktree,
                    timeout_s=5.0,
                )

    @staticmethod
    def git_ref_describe(repo_directory: pathlib.Path) -> str:
        """
        Call 'git describe --dirty'
        """
        assert isinstance(repo_directory, str | pathlib.Path)

        ref_describe = subprocess_run(
            args=[
                "git",
                "describe",
                "--all",
                "--long",
                "--dirty",
            ],
            cwd=repo_directory,
            timeout_s=1.0,
        )
        assert ref_describe is not None
        return ref_describe
