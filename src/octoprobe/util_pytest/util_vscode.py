import sys
import typing

import pytest


def pytest_break_into_debugger(dict_module: dict[typing.Any, typing.Any]) -> None:
    """
    pytest by default catches exceptions and logs them later.
    However, in vscode, we prefer to break into the debugger.

    However, when running on the command line, the exception will be logged by pytest.

    https://github.com/pytest-dev/pytest/issues/7409
    https://docs.pytest.org/en/stable/reference.html
    """

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(
        node: typing.Any,
        call: typing.Any,
        report: typing.Any,
    ) -> None:
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excrepr: typing.Any, excinfo: typing.Any) -> None:
        raise excinfo.value

    dict_module["pytest_exception_interact"] = pytest_exception_interact
    dict_module["pytest_internalerror"] = pytest_internalerror


def is_debugger_connected() -> bool:
    # https://www.pythoninsight.com/2020/06/underhanded-python-detecting-the-debugger/
    # return sys.gettrace() is not None
    # pylint: disable=no-member
    debugger = sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID)
    return debugger is not None


def break_into_debugger_on_exception(dict_module: dict[typing.Any, typing.Any]) -> None:
    if is_debugger_connected():
        pytest_break_into_debugger(dict_module)
