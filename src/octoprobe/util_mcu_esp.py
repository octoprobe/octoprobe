"""
This file implements generic logic for all esp boards
"""

import logging
import pathlib
import sys

from .lib_tentacle import TentacleBase
from .util_dut_programmer_abc import DutProgrammerABC
from .util_firmware_spec import FirmwareSpecBase
from .util_mcu import FILENAME_FLASHING
from .util_pyudev import UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)


def esptool_flash_micropython(
    tty: str,
    filename_firmware: pathlib.Path,
    programmer_args: list[str],
    directory_test: pathlib.Path,
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

    subprocess_run(
        args=args,
        cwd=directory_test,
        logfile=directory_test / FILENAME_FLASHING,
        timeout_s=120.0,
    )


class DutProgrammerEsptool(DutProgrammerABC):
    LABEL = "esptool"

    def flash(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """
        The exp8622 does not require to be booted into boot(programming) mode.
        So we can reuse the port name from mp_remote
        """
        assert isinstance(tentacle, TentacleBase)
        assert isinstance(udev, UdevPoller)
        assert isinstance(directory_logs, pathlib.Path)
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert tentacle.dut is not None
        assert tentacle.dut.mp_remote_is_initialized
        tty = tentacle.dut.mp_remote.close()
        assert tty is not None

        esptool_flash_micropython(
            tty=tty,
            filename_firmware=firmware_spec.filename,
            programmer_args=tentacle.tentacle_spec_base.programmer_args,
            directory_test=directory_logs,
        )
