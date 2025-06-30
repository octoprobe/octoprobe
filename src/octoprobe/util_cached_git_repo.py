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

LEN_COMMIT_HASH_SHORT = 7
"9bde125"

DIRECTORY_WORK = "work"

# We use '~' as this is not allowed in branch names
# See: https://git-scm.com/docs/git-check-ref-format
RE_GIT_SPEC = re.compile(
    rf"^(?P<url>(.+?://)?.+?)({GIT_REF_TAG_PR}(?P<pr>.+?))?({GIT_REF_TAG_BRANCH}(?P<branch>.+))?$"
)
"""
# Git specs to be used for manual testing
https://github.com/micropython/micropython.git
# tag:
https://github.com/micropython/micropython.git@1.25.0
# branch:
https://github.com/micropython/micropython.git@v1.24-release
# commit hash:
https://github.com/micropython/micropython.git@7118942a8c03413e0e85b9b42fc9e1b167966d57
# PR
https://github.com/micropython/micropython.git~17468
# rebase PR on tag (edit meaningful values)
https://github.com/micropython/micropython.git~17468@1.25.0
# rebase PR on branch (edit meaningful values)
https://github.com/micropython/micropython.git~17468@v1.24-release
# rebase PR on commit hash (edit meaningful values)
https://github.com/micropython/micropython.git~17468@7118942a8c03413e0e85b9b42fc9e1b167966d57
"""

RE_IS_GITHUB_URL = re.compile(r"/(tree|pull|commit|commits)/")
"""
It is a github url if it contains '/tree/' or '/pull/'
"""

RE_GITHUB_URL = re.compile(
    r"^(?P<url>(.+?://)?.+?)(?P<trash>/|.git|.git/)?(|(/pull/(?P<pr>\d+).*)|(/(tree|commits)/(?P<branch>.+?)/?)|(/commit/(?P<commit>[a-f0-9]+).*))$"
)
"""
https://github.com/micropython/micropython
https://github.com/micropython/micropython/
https://github.com/micropython/micropython.git
https://github.com/micropython/micropython.git/
https://github.com/micropython/micropython/commit/f498a16c7db6d4b2de200b3e0856528dfe0613c3
https://github.com/micropython/micropython/commit/f498a16c7db6d4b2de200b3e0856528dfe0613c3#diff-69528cf7
https://github.com/micropython/micropython/pull/17468
https://github.com/micropython/micropython/pull/17468/commits
https://github.com/micropython/micropython/tree/master
https://github.com/micropython/micropython/tree/docs/library/bluetooth
"""

RE_COMMIT_HASH = re.compile(r"^[a-f0-9]+$")
"""
This pattern is used to distinquish a branch from a commit hash.
"""


@dataclasses.dataclass(frozen=True)
class MetadataGitCommand:
    command: str
    stdout: str


@dataclasses.dataclass(frozen=True)
class GitMetadata:
    git_spec: str
    url_link: str
    commit_hash: str
    "0a98f3a91130d127c937d6865ead24b6693182eb"
    rebased: bool
    command_describe: MetadataGitCommand
    command_log: MetadataGitCommand

    @property
    def commit_hash_short(self) -> str:
        "0a98f3a"
        return self.commit_hash[0:LEN_COMMIT_HASH_SHORT]

    @property
    def commit_comment(self) -> str:
        """
        '0a98f3a' or 'rebased on 0a98f3a'
        """
        if self.rebased:
            return f"rebased on {self.commit_hash_short}"
        return self.commit_hash_short

    @property
    def url_commit_hash(self) -> str:
        """
        Example:
        https://github.com/micropython/micropython/commit/0a98f3a91130d127c937d6865ead24b6693182eb
        """
        git_spec = GitSpec.parse(self.git_spec)
        return f"{git_spec.url_without_git}/commit/{self.commit_hash}"

    @classmethod
    def from_dict(cls, json_dict: dict) -> GitMetadata:
        for key in ("command_describe", "command_log"):
            json_dict[key] = MetadataGitCommand(**json_dict[key])
        return GitMetadata(**json_dict)


METADATA_SUFFIX = ".metadata.json"


@dataclasses.dataclass(frozen=True, repr=True)
class GitSpec:
    """
    https://github.com/micropython/micropython.git~17468@v1.25.0
    """

    git_spec: str
    "https://github.com/micropython/micropython.git~17468@v1.25.0"
    url: str
    "https://github.com/micropython/micropython.git"
    pr: str | None
    "17468"
    branch: str | None
    "v1.25.0"

    @property
    def is_commit_hash(self) -> bool:
        """
        Returns True if 'self.branch' is a commit hash.
        """
        if self.branch is None:
            return False
        match_commit_hash = RE_COMMIT_HASH.match(self.branch)
        return match_commit_hash is not None

    @property
    def is_branch(self) -> bool:
        """
        Returns True if 'self.branch' is a branch and not a commit hash.
        """
        if self.branch is None:
            return False
        match_commit_hash = RE_COMMIT_HASH.match(self.branch)
        return match_commit_hash is None

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

    @classmethod
    def parse(cls, git_ref: str) -> GitSpec:
        match = RE_GIT_SPEC.match(git_ref)
        if match is None:
            raise ValueError(f"Failed to parse git_spec '{git_ref}'!")

        return GitSpec(
            git_spec=git_ref,
            url=match.group("url"),
            pr=match.group("pr"),
            branch=match.group("branch"),
        )

    @classmethod
    def parse_github(cls, github_url: str) -> GitSpec:
        match = RE_GITHUB_URL.match(github_url)
        if match is None:
            raise ValueError(f"Failed to parse github_url '{github_url}'!")

        url = match.group("url")
        assert not url.endswith(GIT_REF_SUFFIX_GIT)
        url += GIT_REF_SUFFIX_GIT

        branch = match.group("branch")
        if branch is None:
            branch = match.group("commit")
        git_spec = GitSpec(
            git_spec="-",
            url=url,
            pr=match.group("pr"),
            branch=branch,
        )
        return dataclasses.replace(git_spec, git_spec=git_spec.render_git_spec)

    @classmethod
    def parse_tolerant(cls, git_ref: str) -> GitSpec:
        match_is_github_url = RE_IS_GITHUB_URL.search(git_ref)
        if match_is_github_url:
            return cls.parse_github(github_url=git_ref)

        return cls.parse(git_ref=git_ref)


class CachedGitRepo:
    """
    Lacy cloning of the repo.
    The repo will clone/updated once per pytest session.
    The url of the repo will be stored in a file "repo_url.txt".
    If the url changed, the whole repo will be cloned again.
    """

    GIT_DEPTH_DEEP = 1000
    GIT_DEPTH_SHALLOW = 20

    def __init__(
        self,
        directory_cache: pathlib.Path,
        git_spec: str,
        prefix: str = "",
        subdir: str = DIRECTORY_WORK,
    ) -> None:
        assert isinstance(directory_cache, pathlib.Path)
        assert isinstance(git_spec, str)
        assert isinstance(prefix, str)
        # Example 'directory_cache': ~/git_cache
        # Example 'git_spec': https://github.com/micropython/micropython.git@main
        # Example 'prefix': 'micropython_mpbuild_'

        self.prefix = prefix
        self._directory_work = directory_cache / subdir
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

    def clone(self, git_clean: bool, submodules=False) -> GitMetadata:
        """
        Clone or update the git repo.
        """
        #
        # Clone repo
        #
        self._directory_work.mkdir(parents=True, exist_ok=True)

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
            "--quiet",
            self.git_spec.url,
            self.directory_git_work_repo.name,
        ]
        if self.git_spec.is_branch:
            assert self.git_spec.branch is not None
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

        if self.git_spec.is_commit_hash:
            assert self.git_spec.branch is not None
            subprocess_run(
                args=[
                    "git",
                    "checkout",
                    self.git_spec.branch,
                ],
                cwd=self.directory_git_work_repo,
                timeout_s=GIT_CLONE_TIMEOUT_S,
            )

        commit_log_begin = commit_hash = subprocess_run(
            args=[
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=self.directory_git_work_repo,
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
            commit_hash = subprocess_run(
                args=[
                    "git",
                    "rev-parse",
                    "HEAD",
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

        metadata = self.get_metadata(
            depth=depth,
            rebased=require_rebase,
            commit_log_begin=commit_log_begin,
            commit_hash=commit_hash,
        )
        with self.filename_metadata.open("w") as f:
            json.dump(dataclasses.asdict(metadata), fp=f, indent=4, sort_keys=True)

        logger.info(
            f"git clone {self.git_spec.git_spec} -> {relative_cwd(self.directory_git_work_repo)}"
        )
        return metadata

    def get_metadata(
        self,
        depth: int,
        rebased: bool,
        commit_log_begin: str | None,
        commit_hash: str | None,
    ) -> GitMetadata:
        assert isinstance(commit_log_begin, str)
        assert isinstance(commit_hash, str)
        command_describe = self.get_git_describe()
        command_log = self.get_git_log(depth=depth, commit_log_begin=commit_log_begin)

        return GitMetadata(
            git_spec=self.git_spec.git_spec,
            url_link=self.git_spec.url_link,
            commit_hash=commit_hash,
            rebased=rebased,
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
            "--always",
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

    def get_git_log(self, depth: int, commit_log_begin: str) -> MetadataGitCommand:
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
            f"-n {depth}",
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
            remaining_lines = 1_000_000
            # end_trigger = f" (origin/{self.git_spec.branch}"
            end_trigger = f"{commit_log_begin[0:LEN_COMMIT_HASH_SHORT]} "
            # if (self.git_spec.pr is not None) and (self.git_spec.branch is None):
            #     end_trigger = f" (HEAD -> pr-{self.git_spec.pr})"
            for line in git_log.splitlines():
                if line.startswith(end_trigger):
                    line = (
                        line[0:LEN_COMMIT_HASH_SHORT]
                        + " (BASE)"
                        + line[LEN_COMMIT_HASH_SHORT:]
                    )
                    remaining_lines = 1
                lines.append(line)
                if remaining_lines <= 0:
                    break
                remaining_lines -= 1
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
        if directory_work.is_dir():
            for subdirectory in directory_work.iterdir():
                if subdirectory.is_dir():
                    shutil.rmtree(subdirectory)
                else:
                    subdirectory.unlink()

    @staticmethod
    def git_metadata(directory: pathlib.Path) -> GitMetadata | None:
        if not directory.is_dir():
            return None
        filename_metadata = directory.with_suffix(METADATA_SUFFIX)

        try:
            metadata_text = filename_metadata.read_text()
            metadata_dict = json.loads(metadata_text)
            assert isinstance(metadata_dict, dict)
            return GitMetadata.from_dict(metadata_dict)
        except Exception as e:
            logger.debug(f"{filename_metadata}: {e}")
            return None
