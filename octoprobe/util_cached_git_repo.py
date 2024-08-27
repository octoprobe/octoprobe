import logging
import pathlib
import shutil

from .util_subprocess import subprocess_run

logger = logging.getLogger(__file__)


class CachedGitRepo:
    """
    Lacy cloning of the repo.
    The repo will clone/updated once per pytest session.
    The url of the repo will be stored in a file "repo_url.txt".
    If the url changed, the whole repo will be cloned again.
    """

    singleton_cloned: bool | None = None

    def clone(self, directory: pathlib.Path, git_spec: str) -> bool:
        """
        Clone or update the git_micropython repo.
        return True: If the repo was successfully cloned
        return False: If no PYTEST_OPT_GIT_MICROPYTHON parameter was given.
        """
        if CachedGitRepo.singleton_cloned is None:
            CachedGitRepo.singleton_cloned = self._clone(
                directory=directory, git_spec=git_spec
            )
        return CachedGitRepo.singleton_cloned

    def _clone(self, directory: pathlib.Path, git_spec: str) -> bool:
        """
        return True: If the repo was successfully cloned
        return False: If no PYTEST_OPT_GIT_MICROPYTHON parameter was given.
        """
        assert isinstance(git_spec, str)
        if git_spec is None:
            return False

        directory.parent.mkdir(parents=True, exist_ok=True)
        filename_git_url = directory.parent / f"{directory.name}_url.txt"

        # git_spec example: https://github.com/micropython/micropython.git@main
        url, _, branch = git_spec.partition("@")

        def remove_repo_if_url_changed(url: str):
            try:
                url_present = filename_git_url.read_text()
            except FileNotFoundError:
                url_present = "..."
            if url != url_present:
                filename_git_url.write_text(url)
                shutil.rmtree(directory, ignore_errors=True)

        remove_repo_if_url_changed(url=url)

        if (directory / ".git").is_dir():
            _stdout = subprocess_run(
                args=["git", "fetch", "--all"],
                cwd=directory,
                timeout_s=20.0,
            )
        else:
            _stdout = subprocess_run(
                args=["git", "clone", url, directory.name],
                cwd=directory.parent,
                timeout_s=20.0,
            )
        _stdout = subprocess_run(
            args=["git", "checkout", "--force", branch],
            cwd=directory,
            timeout_s=20.0,
        )
        return True
