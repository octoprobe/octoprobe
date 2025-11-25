"""
This file implements generic logic for all esp boards

Copy logic from util_mcu_pyboard.py
"""

import logging
import pathlib
import typing

from .lib_tentacle import TentacleBase
from .util_dut_programmer_abc import DutProgrammerABC
from .util_firmware_spec import FirmwareSpecBase
from .util_pyudev import UdevPoller

logger = logging.getLogger(__name__)


class DutProgrammerPicoprobe(DutProgrammerABC):
    LABEL = "picoprobe"

    @typing.override
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
        raise NotImplementedError()
