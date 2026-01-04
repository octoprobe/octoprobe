from __future__ import annotations

import io
import logging
import os
import pathlib

logger = logging.getLogger(__file__)

ENV_OCTOPROBE_ENABLE_FTRACE_MARKER = "OCTOPROBE_ENABLE_FTRACE_MARKER"

ENABLE_FTRACE_MARKER = os.environ.get(ENV_OCTOPROBE_ENABLE_FTRACE_MARKER, "0") != "0"


class FtraceMarker:
    """
    sudo chmod a+w /sys/kernel/tracing/trace_marker

    See also:
    https://github.com/sruffell/trace-marker-example

sudo trace-cmd record -p function_graph \
  -l tty_open \
  -l tty_read \
  -l tty_write \
  -l tty_release \
  -l usb_serial_open \
  -l acm_open

sudo trace-cmd report

    """

    f: io.TextIOWrapper | None = None

    @classmethod
    def init(cls) -> None:
        cls.f = pathlib.Path("/sys/kernel/tracing/trace_marker").open("w")

    @classmethod
    def print(cls, msg: str) -> None:
        if cls.f is None:
            return
        cls.f.write(f"{msg}\n")
        cls.f.flush()


FTRACE_MARKER = FtraceMarker()

if ENABLE_FTRACE_MARKER:
    FTRACE_MARKER.init()
