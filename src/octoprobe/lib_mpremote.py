from __future__ import annotations

import contextlib
import datetime
import hashlib
import logging
import pathlib
import typing
from collections.abc import Generator
from typing import Any, Self

from mpremote import mip  # type: ignore
from mpremote.commands import do_filesystem_cp  # type: ignore
from mpremote.main import State  # type: ignore
from mpremote.transport_serial import SerialTransport, TransportError  # type: ignore

from .util_ftrace_marker import FTRACE_MARKER
from .util_jinja2 import render

# pylint: disable=W0123 # Use of eval (eval-used)
logger = logging.getLogger(__file__)


class ExceptionMpRemote(Exception):
    pass


class ExceptionCmdFailed(ExceptionMpRemote):
    pass


class ExceptionCmdError(ExceptionMpRemote):
    pass


class ExceptionTransport(ExceptionMpRemote):
    pass


class MpRemote:
    """
    A wrapper around 'mpremote'.
    Not sure if this is the best solution?
    Are there other ways to access micropython on a remote MCU?
    """

    RESULT_TAG = "[RESULT]"
    ERROR_TAG = "[ERROR]"

    def __init__(
        self,
        tty: str,
        label: str,
        baudrate: int = 115200,
        wait_s: int = 5,
        timeout_s: float | None = 2.0,
    ) -> None:
        self._tty = tty
        self._label = label
        self._baudrate = baudrate
        self._wait_s = wait_s
        self._timeout_s = timeout_s
        self.state: State
        self._init()
        FTRACE_MARKER.print(f"{self._label}: mpremote {self._tty} open()")

    def _init(self) -> None:
        self.state = State()
        self.state.transport = SerialTransport(
            self._tty,
            baudrate=self._baudrate,
            wait=self._wait_s,
            timeout=self._timeout_s,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> str:
        """
        Return the serial port which was closed.
        """
        if self.state.transport is not None:
            try:
                FTRACE_MARKER.print(f"{self._label}: mpremote {self._tty} close()")
                self.state.transport.close()
            finally:
                self.state.transport = None

        return self._tty

    @contextlib.contextmanager
    def borrow_tty(self) -> Generator[str]:
        """
        Context manager that yields the tty (/dev/ttyACM1).
        After use, mpremote will reattach to the tty!
        """
        self.close()
        try:
            yield self._tty
        finally:
            self._init()
            # Make sure we still can communicate
            # self.exec_raw(cmd="print('hello pico')", soft_reset=True)
            self.state.ensure_raw_repl(soft_reset=True)

    def set_rtc(self, now: datetime.datetime | None = None) -> None:
        assert isinstance(now, datetime.datetime | None)
        if now is None:
            now = datetime.datetime.now()
        timetuple = (
            now.year,
            now.month,
            now.day,
            now.weekday(),
            now.hour,
            now.minute,
            now.second,
            now.microsecond,
        )
        cmd = f"import machine; machine.RTC().datetime({timetuple})"
        self.exec_raw(cmd)

    def cp(self, src: pathlib.Path, dest: str, multiple: bool = True) -> None:
        assert isinstance(src, pathlib.Path)
        assert isinstance(dest, str)
        assert isinstance(multiple, bool)

        self.state.ensure_raw_repl(soft_reset=False)
        self.state.did_action()

        # def do_filesystem_cp(state, src, dest, multiple, check_hash=False):
        do_filesystem_cp(self.state, str(src), dest, multiple=multiple, check_hash=True)

    def file_equal(self, src: pathlib.Path, dest: str) -> bool:
        """
        return False if the src and dest are equal and therefore do not have to be copied.
        """
        assert isinstance(src, pathlib.Path)
        assert isinstance(dest, str)
        assert dest.startswith(":")

        self.state.ensure_raw_repl(soft_reset=False)
        self.state.did_action()

        remote_hash = self.state.transport.fs_hashfile(dest[1:], "sha256")
        source_hash = hashlib.sha256(src.read_bytes()).digest()
        return remote_hash == source_hash

    def mip_install_package(self, package: str) -> None:
        assert isinstance(package, str)

        # list package specifications, e.g. name, name@version, github:org/repo, github:org/repo@branch, gitlab:org/repo, gitlab:org/repo@branch
        # package = package

        # package index to use (defaults to micropython-lib)
        # See: https://github.com/micropython/micropython-lib/blob/v1.22.0/README.md
        # mpremote connect /dev/ttyUSB0 mip install --index https://USERNAME.github.io/micropython-lib/mip/BRANCH_NAME PACKAGE_NAME
        index: str | None = mip._PACKAGE_INDEX  # pylint: disable=W0212:protected-access

        # destination direction on the device
        target = "mip"

        # Example package: github:org/repo@branch
        # version -> 'branch'
        version: str | None = None
        if "@" in package:
            package, version = package.split("@")

        # download as compiled .mpy files (default)
        mpy: bool = False

        self.state.ensure_raw_repl()
        self.state.did_action()

        mip._install_package(  # pylint: disable=W0212:protected-access
            transport=self.state.transport,
            package=package,
            index=index,
            target=target,
            version=version,
            mpy=mpy,
        )

    def exec_render(
        self,
        micropython_code: str,
        follow: bool = True,
        **kwargs: Any,
    ) -> str:
        mp_program = render(micropython_code=micropython_code, **kwargs)
        return self.exec_raw(cmd=mp_program, follow=follow)

    def exec_file(
        self,
        filename: pathlib.Path,
        follow: bool = True,
        timeout: int | None = 2,
        soft_reset: bool | None = None,
    ) -> str:
        assert isinstance(filename, pathlib.Path)

        cmd = filename.read_text()
        return self.exec_raw(
            cmd=cmd,
            follow=follow,
            timeout=timeout,
            soft_reset=soft_reset,
        )

    def exec_file_result(
        self,
        filename: pathlib.Path,
        follow: bool = True,
        timeout: int | None = 2,
        soft_reset: bool | None = None,
    ) -> str:
        assert isinstance(filename, pathlib.Path)

        cmd = filename.read_text()
        return self.exec_raw(
            cmd=cmd,
            timeout=timeout,
            check_result=True,
            follow=follow,
            soft_reset=soft_reset,
        )

    def exec_raw(
        self,
        cmd: str,
        check_result: bool = False,
        follow: bool = True,
        timeout: int | None = 2,
        soft_reset: bool | None = None,
    ) -> str:
        """
        Derived from mpremote.commands.do_exec / do_execbuffer
        """
        assert isinstance(cmd, str)
        assert isinstance(follow, bool)
        assert isinstance(timeout, int | None)

        FTRACE_MARKER.print(f"{self._label}: mpremote {self._tty} exec_raw() {cmd}")

        self.state.ensure_raw_repl(soft_reset=soft_reset)
        self.state.did_action()

        ret = b"follow=False"
        try:
            assert self.state.transport is not None
            self.state.transport.exec_raw_no_follow(cmd)
            if follow:
                # ret, ret_err = state.transport.follow(timeout=None, data_consumer=stdout_write_bytes)
                ret, ret_err = self.state.transport.follow(timeout=timeout)
                if ret_err:
                    lines = [
                        ret_err.decode("ascii"),
                        "micropython-code:",
                        "v" * 20,
                        cmd,
                        "^" * 20,
                    ]
                    result = "\n".join(lines)
                    raise ExceptionCmdFailed(f"{self._label}: {result}")
        except TransportError as ex:
            logger.warning(
                f"{self._label}: tty={self._tty}, cmd='{cmd}': exception={ex!r}"
            )
            FTRACE_MARKER.print(
                f"{self._label}: mpremote {self._tty} exec_raw() {cmd}: ERROR {ex!r}"
            )
            raise ExceptionTransport(ex) from ex

        assert isinstance(ret, bytes)
        full_output = ret.decode("utf-8")

        if check_result:
            return self._extract_result(cmd=cmd, full_output=full_output)
        return full_output

    def _extract_result(self, cmd: str, full_output: str) -> str:
        """
        Find '[RESULT]' result and returns the consecutive text.
        If '[ERROR]' is found and throw ExceptionCmdError().

        Example expr: 1+3
        Executes 1+3 on micropython by calling 'print(1+3)' and capturing its output.
        However, the textoutput may contain text which was emitted bevor the the result.
        Therefore a tag '[RESULT]' is inserted.
        """
        # Example full_output: DebugXYZ[ERROR]'I2C_EIO'[RESULT]4
        list_elements = full_output.split(self.RESULT_TAG)
        if len(list_elements) != 2:
            raise ExceptionCmdFailed(
                f"{self._label}: '{cmd}': Expected '{self.RESULT_TAG}' exactly once but got: {full_output}"
            )

        program_output, expression_result = list_elements
        # Example program_output: DebugXYZ[ERROR]'I2C_EIO'
        list_elements = program_output.split(self.ERROR_TAG)
        if len(list_elements) == 2:
            # We found an error tag
            _program_output, error_result = list_elements
            raise ExceptionCmdError(eval(error_result))

        # Example _program_output: DebugXYZ
        # Example expression_result: 4
        return expression_result

    def eval_expression(
        self,
        expr: str,
        check_result: bool,
        timeout: int | None = 2,
    ) -> Any:
        # Example expr: '1+3'
        # First evaluate expr which may produce unwanted debug text output.
        # _v is of datatype str and therefor this print will have no sideeffects: print('{RESULT_TAG}' + _v)
        cmd = f"_v=repr({expr}); print('{self.RESULT_TAG}' + _v)"

        expression_result = self.exec_raw(
            cmd=cmd,
            timeout=timeout,
            check_result=check_result,
        )

        return eval(expression_result)

    def read_None(self, expr: str) -> None:
        v = self.eval_expression(expr, check_result=True)
        assert v is None

    def read_bool(self, expr: str) -> bool:
        v = self.eval_expression(expr, check_result=True)
        assert isinstance(v, bool), v
        return v

    def read_int(self, expr: str) -> int:
        v = self.eval_expression(expr, check_result=True)
        assert isinstance(v, int), v
        return v

    def read_float(self, expr: str) -> float:
        v = self.eval_expression(expr, check_result=True)
        assert isinstance(v, float), v
        return v

    def read_str(self, expr: str) -> str:
        v = self.eval_expression(expr=expr, check_result=True)
        assert isinstance(v, str), v
        return v

    def read_bytes(self, expr: str) -> bytes:
        v = self.eval_expression(expr, check_result=True)
        assert isinstance(v, bytes), v
        return v

    def read_list(self, expr: str) -> list[typing.Any]:
        v = self.eval_expression(expr, check_result=True)
        assert isinstance(v, list | tuple), v
        return list(v)
