"""
This file implements generic logic for all esp boards
"""

import logging
import pathlib
import sys

from usbhubctl.util_subprocess import subprocess_run

logger = logging.getLogger(__name__)


def esptool_flash_micropython(
    tty: str,
    filename_firmware: pathlib.Path,
    programmer_args: list[str],
) -> None:
    assert isinstance(tty, str)
    assert filename_firmware.is_file(), str(filename_firmware)
    assert isinstance(programmer_args, list)

    args = [
        sys.executable,
        "-m",
        "esptool",
        f"--port={tty}",
        *programmer_args,
        str(filename_firmware),
    ]

    subprocess_run(args=args, timeout_s=60.0)
