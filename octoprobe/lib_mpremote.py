from __future__ import annotations

import logging
from typing import Any, Self

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

    def __init__(self, tty: str, baudrate: int = 115200, wait_s: int = 5) -> None:
        self.state = State()
        self.state.transport = SerialTransport(tty, baudrate=baudrate, wait=wait_s)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def exec_render(self, micropython_code: str, follow: bool = True, **kwargs) -> str:
        mp_program = render(micropython_code=micropython_code, **kwargs)
        return self.exec_raw(cmd=mp_program, follow=follow)

    def exec_raw(self, cmd: str, follow: bool = True) -> str:
        """
        Derived from mpremote.commands.do_exec / do_execbuffer
        """
        self.state.ensure_raw_repl()
        self.state.did_action()

        ret = None
        try:
            self.state.transport.exec_raw_no_follow(cmd)
            if follow:
                # ret, ret_err = state.transport.follow(timeout=None, data_consumer=stdout_write_bytes)
                ret, ret_err = self.state.transport.follow(timeout=None)
                if ret_err:
                    logger.warning(ret_err)
                    raise ExceptionCmdFailed(ret_err)
        except TransportError as er:
            logger.warning(er)
            raise ExceptionTransport(er) from er

        assert isinstance(ret, bytes)
        return ret.decode("utf-8")

    def _read_var(self, name: str) -> Any:
        value_text = self.exec_raw(f"print({name})")
        return eval(value_text)

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

    def close(self) -> None:
        self.state.transport.close()
