from __future__ import annotations

import dataclasses
import pathlib

import pytest

from octoprobe.util_cached_git_repo import GitSpec

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent


@dataclasses.dataclass
class Ttestparam:
    spec: str

    expected_url: str
    expected_pr: str | None
    expected_branch: str | None

    @property
    def pytest_id(self) -> str:
        return self.spec
        # return self.spec.replace(" ", "-").replace("https://", "").replace("/", "_")


_TESTPARAM_A = Ttestparam(
    spec="https://github.com/micropython/micropython.git",
    expected_url="https://github.com/micropython/micropython.git",
    expected_pr=None,
    expected_branch=None,
)
_TESTPARAM_B = Ttestparam(
    spec="https://github.com/micropython/micropython.git~17232",
    expected_url="https://github.com/micropython/micropython.git",
    expected_pr="17232",
    expected_branch=None,
)
_TESTPARAM_C = Ttestparam(
    spec="https://github.com/micropython/micropython.git@v1.25.0",
    expected_url="https://github.com/micropython/micropython.git",
    expected_pr=None,
    expected_branch="v1.25.0",
)
_TESTPARAM_D = Ttestparam(
    spec="https://github.com/micropython/micropython.git~17232@v1.25.0",
    expected_url="https://github.com/micropython/micropython.git",
    expected_pr="17232",
    expected_branch="v1.25.0",
)
_TESTPARAMS = [
    _TESTPARAM_A,
    _TESTPARAM_B,
    _TESTPARAM_C,
    _TESTPARAM_D,
]


def _test_collection(testparam: Ttestparam) -> None:
    git_spec = GitSpec.parse(testparam.spec)
    assert git_spec.url == testparam.expected_url
    assert git_spec.pr == testparam.expected_pr
    assert git_spec.branch == testparam.expected_branch


@pytest.mark.parametrize(
    "testparam", _TESTPARAMS, ids=lambda testparam: testparam.pytest_id
)
def test_collection(testparam: Ttestparam) -> None:
    _test_collection(testparam)


if __name__ == "__main__":
    _test_collection(testparam=_TESTPARAM_A)
    # _test_collection(testparam=_TESTPARAM_POTPOURRY)
