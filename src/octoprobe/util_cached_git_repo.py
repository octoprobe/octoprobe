from __future__ import annotations

import hashlib
import logging
import pathlib

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
        self.directory_cache = directory_cache
        self.git_spec = git_spec
        self.url, _, self.branch = git_spec.partition("@")

        self.directory.mkdir(parents=True, exist_ok=True)
        self.filename_git_url.write_text(self.url)

    @property
    def hash(self) -> str:
        return hashlib.md5(self.url.encode("utf-8")).hexdigest()

    @property
    def filename_git_url(self) -> pathlib.Path:
        return self.directory_cache / f"{self.prefix}{self.hash}_url.txt"

    @property
    def directory(self) -> pathlib.Path:
        return self.directory_cache / f"{self.prefix}{self.hash}"

    def clone(self, git_clean: bool) -> None:
        """
        Clone or update the git repo.
        """
        if self.directory.name in CachedGitRepo.singleton_cloned:
            return

        logger.info(f"git clone {self.git_spec} -> {relative_cwd(self.directory)}")
        self._clone(git_clean=git_clean)
        CachedGitRepo.singleton_cloned.add(self.directory.name)

    def _clone(self, git_clean: bool) -> None:
        if (self.directory / ".git").is_dir():
            subprocess_run(
                args=["git", "fetch", "--all"],
                cwd=self.directory_cache,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )
        else:
            subprocess_run(
                args=[
                    "git",
                    "clone",
                    "--filter=blob:none",
                    self.url,
                    self.directory.name,
                ],
                cwd=self.directory.parent,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )
        if git_clean:
            args = ["git", "clean", "-fXd"]
            logger.info(" ".join(args))
            subprocess_run(
                args=args,
                cwd=self.directory,
                timeout_s=20.0,
            )
        subprocess_run(
            args=["git", "checkout", "--force", self.branch],
            cwd=self.directory,
            timeout_s=20.0,
        )
