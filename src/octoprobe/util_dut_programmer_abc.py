from __future__ import annotations

import abc
import logging
import pathlib
import typing

from .util_firmware_spec import FirmwareSpecBase
from .util_pyudev import UdevEventBase, UdevPoller

if typing.TYPE_CHECKING:
    from .lib_tentacle import TentacleBase


logger = logging.getLogger(__file__)


IDX1_RELAYS_DUT_BOOT = 1


class DutProgrammerABC(abc.ABC):
    LABEL = "dummy"

    @abc.abstractmethod
    def flash(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None: ...

    def enter_boot_mode(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> UdevEventBase:
        raise NotImplementedError()
