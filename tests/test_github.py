from __future__ import annotations

import dataclasses
import pathlib

import pytest

from octoprobe.util_cached_git_repo import GitSpec

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent


@dataclasses.dataclass
class Ttestparam:
    github: str
    expected_gitspec: str

    @property
    def pytest_id(self) -> str:
        return self.github
        # return self.spec.replace(" ", "-").replace("https://", "").replace("/", "_")


_TESTPARAMS = [
    Ttestparam(
        github="https://github.com/micropython/micropython",
        expected_gitspec="https://github.com/micropython/micropython.git",
    ),
    Ttestparam(
        github="https://github.com/micropython/micropython/",
        expected_gitspec="https://github.com/micropython/micropython.git",
    ),
    Ttestparam(
        github="https://github.com/micropython/micropython.git",
        expected_gitspec="https://github.com/micropython/micropython.git",
    ),
    Ttestparam(
        github="https://github.com/micropython/micropython.git/",
        expected_gitspec="https://github.com/micropython/micropython.git",
    ),
    Ttestparam(
        github="https://github.com/micropython/micropython/pull/17419",
        expected_gitspec="https://github.com/micropython/micropython.git~17419",
    ),
    Ttestparam(
        github="https://github.com/micropython/micropython/tree/v1.22-release",
        expected_gitspec="https://github.com/micropython/micropython.git@v1.22-release",
    ),
]


def _test_github(testparam: Ttestparam) -> None:
    git_spec = GitSpec.parse_github(testparam.github)
    assert git_spec.render_git_spec == testparam.expected_gitspec


@pytest.mark.parametrize(
    "testparam", _TESTPARAMS, ids=lambda testparam: testparam.pytest_id
)
def test_github(testparam: Ttestparam) -> None:
    _test_github(testparam)
