from __future__ import annotations

import contextlib
import datetime
import logging
import pathlib
from collections.abc import Generator
from typing import Any, Self

from mpremote import mip  # type: ignore
from mpremote.commands import do_filesystem_cp  # type: ignore
from mpremote.main import State  # type: ignore
from mpremote.transport_serial import SerialTransport, TransportError  # type: ignore

from .util_jinja2 import render

# pylint: disable=W0123 # Use of eval (eval-used)
logger = logging.getLogger(__file__)


class ExceptionMpRemote(Exception):
    pass


class ExceptionCmdFailed(ExceptionMpRemote):
    pass


class ExceptionTransport(ExceptionMpRemote):
    pass


class MpRemote:
    """
    A wrapper around 'mpremote'.
    Not sure if this is the best solution?
    Are there other ways to access micropython on a remote MCU?
    """

    def __init__(
        self,
        tty: str,
        baudrate: int = 115200,
        wait_s: int = 5,
        timeout_s: float | None = 2.0,
    ) -> None:
        self._tty = tty
        self._baudrate = baudrate
        self._wait_s = wait_s
        self._timeout_s = timeout_s
        self.state: State
        self._init()

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

    def close(self) -> str | None:
        """
        Return the serial port which was closed.
        """
        if self.state.transport is not None:
            self.state.transport.close()
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

    def cp(self, src: pathlib.Path, dest: str) -> None:
        assert isinstance(src, pathlib.Path)
        assert isinstance(dest, str)
        # def do_filesystem_cp(state, src, dest, multiple, check_hash=False):
        do_filesystem_cp(self.state, str(src), dest, multiple=True, check_hash=False)

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

    def exec_render(self, micropython_code: str, follow: bool = True, **kwargs) -> str:
        mp_program = render(micropython_code=micropython_code, **kwargs)
        return self.exec_raw(cmd=mp_program, follow=follow)

    def exec_raw(
        self,
        cmd: str,
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

        self.state.ensure_raw_repl(soft_reset=soft_reset)
        self.state.did_action()

        ret = None
        try:
            assert self.state.transport is not None
            self.state.transport.exec_raw_no_follow(cmd)
            if follow:
                # ret, ret_err = state.transport.follow(timeout=None, data_consumer=stdout_write_bytes)
                ret, ret_err = self.state.transport.follow(timeout=timeout)  # type: ignore
                if ret_err:
                    lines = [
                        ret_err.decode("ascii"),
                        "micropython-code:",
                        "v" * 20,
                        cmd,
                        "^" * 20,
                    ]
                    raise ExceptionCmdFailed("\n".join(lines))
        except TransportError as er:
            logger.warning(er)
            raise ExceptionTransport(er) from er

        assert isinstance(ret, bytes)
        return ret.decode("utf-8")

    def _exec(self, cmd: str) -> Any:
        "last statment in 'cmd' must be print(xxx)"
        value_text = self.exec_raw(cmd)
        return eval(value_text)

    def exec_bool(self, cmd: str) -> bool:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, bool)
        return v

    def exec_int(self, cmd: str) -> int:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, int)
        return v

    def exec_float(self, cmd: str) -> float:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, float)
        return v

    def exec_str(self, cmd: str) -> str:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, str)
        # Remove '\n\r' at the end of the string
        assert v.endswith("\r\n")
        v = v[:-2]
        return v

    def exec_bytes(self, cmd: str) -> bytes:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, bytes)
        return v

    def exec_list(self, cmd: str) -> list:
        "last statment in 'cmd' must be print(xxx)"
        v = self._exec(cmd)
        assert isinstance(v, list | tuple)
        return list(v)

    def _read_var(self, name: str) -> Any:
        value_text = self.exec_raw(f"print({name})")
        return eval(value_text)

    def read_bool(self, name: str) -> int:
        v = self._read_var(name)
        assert isinstance(v, bool)
        return v

    def read_int(self, name: str) -> int:
        v = self._read_var(name)
        assert isinstance(v, int)
        return v

    def read_float(self, name: str) -> float:
        v = self._read_var(name)
        assert isinstance(v, float)
        return v

    def read_str(self, name: str) -> str:
        v = self.exec_raw(f"print({name})")
        assert isinstance(v, str)
        # Remove '\n\r' at the end of the string
        assert v.endswith("\r\n")
        v = v[:-2]
        return v

    def read_bytes(self, name: str) -> bytes:
        v = self._read_var(name)
        assert isinstance(v, bytes)
        return v

    def read_list(self, name: str) -> list:
        v = self._read_var(name)
        assert isinstance(v, list | tuple)
        return list(v)
