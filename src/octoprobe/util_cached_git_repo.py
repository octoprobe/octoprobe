"""
GIT CLONE / CHECKOUT

git clone/checkoug strategy
===========================

git-cache/work
--------------

Repos are cloned into work folder

Directory
  ~/octoprobe_downloads/git-cache/work/<use>_<repo>

  use: 'firmware' or 'test'
  This allows to have different versions checked out for 'firmware' and 'test'!

For example
  ~/octoprobe_downloads/git-cache/work/firmware_github-com-micropython-micropython.git
  ~/octoprobe_downloads/git-cache/work/firmware_github-com-dpgeorge-micropython.git

commands
  * rm -rf ~/octoprobe_downloads/git-cache/work/<use>_<repo>
  * git clone ...
"""

from __future__ import annotations

import dataclasses
import json
import logging
import pathlib
import re
import shutil

import slugify

from .util_constants import relative_cwd
from .util_subprocess import subprocess_run

logger = logging.getLogger(__file__)
GIT_CLONE_TIMEOUT_S = 240.0

GIT_REF_SUFFIX_GIT = ".git"
GIT_REF_TAG_BRANCH = "@"
GIT_REF_TAG_PR = "~"

DIRECTORY_WORK = "work"

# We use '~' as this is not allowed in branch names
# See: https://git-scm.com/docs/git-check-ref-format
RE_GIT_SPEC = re.compile(
    rf"^(?P<url>(.+?://)?.+?)({GIT_REF_TAG_PR}(?P<pr>.+?))?({GIT_REF_TAG_BRANCH}(?P<branch>.+))?$"
)
"""
https://github.com/micropython/micropython.git
https://github.com/micropython/micropython.git~17232
https://github.com/micropython/micropython.git@1.25.0
https://github.com/micropython/micropython.git~17232@1.25.0
"""

RE_GITHUB_URL = re.compile(
    r"^(?P<url>(.+?://)?.+?)(?P<trash>/|.git|.git/)?(/pull/(?P<pr>\d+?))?(/tree/(?P<branch>.+))?$"
)
"""
https://github.com/micropython/micropython
https://github.com/micropython/micropython/
https://github.com/micropython/micropython.git
https://github.com/micropython/micropython.git/
https://github.com/micropython/micropython/pull/17419
https://github.com/micropython/micropython/tree/v1.22-release
"""


@dataclasses.dataclass(frozen=True)
class MetadataGitCommand:
    command: str
    stdout: str


@dataclasses.dataclass(frozen=True)
class Metadata:
    git_spec: str
    url_link: str
    command_describe: MetadataGitCommand
    command_log: MetadataGitCommand


METADATA_SUFFIX = ".metadata.json"


@dataclasses.dataclass(frozen=True, repr=True)
class GitSpec:
    """
    https://github.com/micropython/micropython.git~17232@v1.25.0
    """

    git_spec: str
    "https://github.com/micropython/micropython.git~17232@v1.25.0"
    url: str
    "https://github.com/micropython/micropython.git"
    pr: str | None
    "17232"
    branch: str | None
    "v1.25.0"

    @property
    def url_without_git(self) -> str:
        if self.url.endswith(GIT_REF_SUFFIX_GIT):
            return self.url[: -len(GIT_REF_SUFFIX_GIT)]
        return self.url

    @property
    def url_link(self) -> str:
        """
        Example:
        https://github.com/micropython/micropython/tree/master
        https://github.com/micropython/micropython/pull/17419
        """
        if self.pr is not None:
            return f"{self.url_without_git}/pull/{self.pr}"
        if self.branch is not None:
            return f"{self.url_without_git}/tree/{self.branch}"
        return self.url_without_git

    @property
    def render_git_spec(self) -> str:
        spec = self.url
        if self.pr is not None:
            spec += f"{GIT_REF_TAG_PR}{self.pr}"
        if self.branch is not None:
            spec += f"{GIT_REF_TAG_BRANCH}{self.branch}"
        return spec

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

    @staticmethod
    def parse_github(github_url: str) -> GitSpec:
        match = RE_GITHUB_URL.match(github_url)
        if match is None:
            raise ValueError(f"Failed to parse github_url '{github_url}'!")

        url = match.group("url")
        assert not url.endswith(GIT_REF_SUFFIX_GIT)
        url += GIT_REF_SUFFIX_GIT

        git_spec = GitSpec(
            git_spec="-",
            url=url,
            pr=match.group("pr"),
            branch=match.group("branch"),
        )
        return dataclasses.replace(git_spec, git_spec=git_spec.render_git_spec)


class CachedGitRepo:
    """
    Lacy cloning of the repo.
    The repo will clone/updated once per pytest session.
    The url of the repo will be stored in a file "repo_url.txt".
    If the url changed, the whole repo will be cloned again.
    """

    GIT_DEPTH_DEEP = 1000
    GIT_DEPTH_SHALLOW = 2

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
        self._directory_work = directory_cache / DIRECTORY_WORK
        self.git_spec = GitSpec.parse(git_ref=git_spec)

        logger.debug(f"{self.git_spec.git_spec} -> {self.git_spec}")

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
    def filename_metadata(self) -> pathlib.Path:
        return self.directory_git_work_repo.with_suffix(METADATA_SUFFIX)

    @property
    def directory_git_work_repo(self) -> pathlib.Path:
        return self._directory_work / f"{self.prefix}{self.slugify}"

    def clone(self, git_clean: bool, submodules=False) -> None:
        """
        Clone or update the git repo.
        """
        #
        # Clone repo
        #
        self._directory_work.mkdir(exist_ok=True)

        assert not self.directory_git_work_repo.is_dir(), self.directory_git_work_repo
        # logger.debug(f"Remove directory: {self.directory_git_work_repo}")
        # shutil.rmtree(self.directory_git_work_repo)

        require_rebase = (self.git_spec.branch is not None) and (
            self.git_spec.pr is not None
        )
        depth = self.GIT_DEPTH_DEEP if require_rebase else self.GIT_DEPTH_SHALLOW
        args = [
            "git",
            "clone",
            f"--depth={depth}",
            "--filter=blob:none",
            "--jobs=8",
            self.git_spec.url,
            self.directory_git_work_repo.name,
        ]
        if self.git_spec.branch is not None:
            args.append(f"--branch={self.git_spec.branch}")
        if submodules:
            args.extend(
                [
                    "--recurse-submodules",
                    "--shallow-submodules",  # All submodules which are cloned will be shallow with a depth of 1.
                ]
            )
        subprocess_run(
            args=args,
            cwd=self.directory_git_work_repo.parent,
            timeout_s=GIT_CLONE_TIMEOUT_S,
        )

        if self.git_spec.pr is not None:
            subprocess_run(
                args=[
                    "git",
                    "fetch",
                    "origin",
                    f"pull/{self.git_spec.pr}/head:pr-{self.git_spec.pr}",
                ],
                cwd=self.directory_git_work_repo,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )
            subprocess_run(
                args=[
                    "git",
                    "checkout",
                    f"pr-{self.git_spec.pr}",
                ],
                cwd=self.directory_git_work_repo,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )

            if require_rebase:
                assert self.git_spec.branch is not None
                subprocess_run(
                    args=[
                        "git",
                        "rebase",
                        self.git_spec.branch,
                    ],
                    cwd=self.directory_git_work_repo,
                    timeout_s=GIT_CLONE_TIMEOUT_S,
                )

        metadata = self.get_metadata()
        with self.filename_metadata.open("w") as f:
            json.dump(dataclasses.asdict(metadata), fp=f, indent=4, sort_keys=True)

        logger.info(
            f"git clone {self.git_spec.git_spec} -> {relative_cwd(self.directory_git_work_repo)}"
        )

    def get_metadata(self) -> Metadata:
        command_describe = self.get_git_describe()
        command_log = self.get_git_log()
        return Metadata(
            git_spec=self.git_spec.git_spec,
            url_link=self.git_spec.url_link,
            command_describe=command_describe,
            command_log=command_log,
        )

    def get_git_describe(self) -> MetadataGitCommand:
        args = [
            "git",
            "describe",
            "--all",
            "--long",
            "--dirty",
        ]

        git_describe = subprocess_run(
            args=args,
            cwd=self.directory_git_work_repo,
            timeout_s=GIT_CLONE_TIMEOUT_S,
        )
        assert git_describe is not None

        return MetadataGitCommand(
            command=" ".join(args),
            stdout=git_describe,
        )

    def get_git_log(self) -> MetadataGitCommand:
        """
        call 'git log' and concatinate the output.
        Example:
            436b067 (HEAD -> pr-17418) pyproject.toml: Enforce trailing newline on python files.
            5f058e9 (origin/master, origin/HEAD, master) esp32: Update ADC driver update to the new esp_adc API.
            2c2f0b2 esp32: Re-use allocated timer interrupts and simplify UART timer code.
        Concatenations is triggered by ' (origin/'
        """
        args = [
            "git",
            "log",
            "--oneline",
            "--decorate",
            f"-n {self.GIT_DEPTH_DEEP}",
        ]
        git_log = subprocess_run(
            args=args,
            cwd=self.directory_git_work_repo,
            timeout_s=GIT_CLONE_TIMEOUT_S,
        )
        assert git_log is not None

        def head() -> str:
            "return all relevant lines plus one"
            lines: list[str] = []
            done = False
            end_trigger = f" (origin/{self.git_spec.branch}"
            if (self.git_spec.pr is not None) and (self.git_spec.branch is None):
                end_trigger = f" (HEAD -> pr-{self.git_spec.pr})"
            for line in git_log.splitlines():
                lines.append(line)
                if done:
                    break
                if line.find(end_trigger) >= 0:
                    # Example:
                    # 5f058e9 (origin/master, origin/HEAD, master) esp32: Update ADC driver update
                    done = True
            return "\n".join(lines)

        return MetadataGitCommand(
            command=" ".join(args),
            stdout=head(),
        )

    @staticmethod
    def clean_directory_work_repo(directory_cache=pathlib.Path) -> None:
        """
        Before we start cloning/checkout: Remove all git-cache/work directories!
        """
        assert isinstance(directory_cache, pathlib.Path)
        directory_work = directory_cache / DIRECTORY_WORK
        for subdirectory in directory_work.iterdir():
            if subdirectory.is_dir():
                shutil.rmtree(subdirectory)
            else:
                subdirectory.unlink()

    @staticmethod
    def git_metadata(directory: pathlib.Path) -> dict:
        if not directory.is_dir():
            return {}
        filename_metadata = directory.with_suffix(METADATA_SUFFIX)

        try:
            metadata_text = filename_metadata.read_text()
            metadata_dict = json.loads(metadata_text)
            assert isinstance(metadata_dict, dict)
            return metadata_dict
        except Exception as e:
            logger.error(f"{filename_metadata}: {e}")
            return {}
