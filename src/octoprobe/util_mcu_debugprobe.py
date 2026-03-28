"""
This file implements generic logic the Raspberry Pi Debug Probe.

https://www.raspberrypi.com/documentation/microcontrollers/debug-probe.html
https://github.com/raspberrypi/debugprobe
"""

import logging
import pathlib

import pyudev

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC
from .util_firmware_spec import FirmwareBuildSpec, FirmwareSpecBase
from .util_pyudev import UdevEventBase, UdevPoller

logger = logging.getLogger(__name__)

_RPI_DEBUGPROBE_VENDOR = 0x2E8A

RPI_DEBUGPROBE_USB_ID = BootApplicationUsbID(
    boot=UsbID(_RPI_DEBUGPROBE_VENDOR, 0x2E8A),
    application=UsbID(_RPI_DEBUGPROBE_VENDOR, 0x000C),
)


class Rp2UdevBootModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.serial = device.properties["ID_SERIAL_SHORT"]
        self.dev_num = int(device.properties["DEVNUM"])
        self.bus_num = int(device.properties["BUSNUM"])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(serial={self.serial}, bus_num={self.bus_num}, dev_num={self.dev_num})"


class DutProgrammerDebugprobe(DutProgrammerABC):
    LABEL = "debugprobe"

    def flash(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert isinstance(tentacle, TentacleBase)
        assert isinstance(directory_logs, pathlib.Path)
        assert isinstance(firmware_spec, FirmwareBuildSpec)
        assert tentacle.dut is not None
        assert tentacle.tentacle_spec_base.mcu_usb_id is not None

        raise NotImplementedError()
