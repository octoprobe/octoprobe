"""
This file implements generic logic for all Mimxrt boards
"""

import logging
import pathlib
import time

import pyudev  # type: ignore

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareBuildSpec, FirmwareSpecBase
from .util_mcu import FILENAME_FLASHING
from .util_pyudev import UdevEventBase, UdevFilter, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)

TEENSY40_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x16C0, 0x0478),
    application=UsbID(0xF055, 0x9802),
)


class MimxrtUdevBootModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.tty = device.device_node

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(tty={self.tty})"


def mimxrt_udev_filter_boot_mode(usb_location: str) -> UdevFilter:
    assert isinstance(usb_location, str)

    return UdevFilter(
        label="Boot Mode",
        usb_location=usb_location,
        udev_event_class=MimxrtUdevBootModeEvent,
        id_vendor=None,
        id_product=None,
        subsystem="usb",
        device_type="usb_device",
        actions=["bind"],
    )


class DutProgrammerTeensyLoaderCli(DutProgrammerABC):
    LABEL = "teensy_loader_cli"

    def flash(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """
        https://github.com/PaulStoffregen/teensy_loader_cli/blob/master/README.md
        https://micropython.org/download/TEENSY40/
        """
        assert isinstance(tentacle, TentacleBase)
        assert isinstance(directory_logs, pathlib.Path)
        assert isinstance(firmware_spec, FirmwareBuildSpec)
        assert tentacle.dut is not None
        assert tentacle.tentacle_spec_base.mcu_usb_id is not None

        # tentacle.infra.power_dut_off_and_wait()

        # Press Program Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX1_RELAYS_DUT_BOOT])
        tentacle.power_dut = True
        time.sleep(0.5)

        with udev.guard as guard:
            # Release Program Button
            tentacle.infra.mcu_infra.relays(relays_open=[IDX1_RELAYS_DUT_BOOT])

            udev_filter = mimxrt_udev_filter_boot_mode(
                usb_location=tentacle.infra.usb_location_dut
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after power on",
                timeout_s=3.0,
            )

        assert isinstance(event, MimxrtUdevBootModeEvent)
        filename_dfu = firmware_spec.filename
        # Attention: NO port is supported...
        # This might have unwanted sideffects!
        # event.tty
        args = [
            "teensy_loader_cli",
            *tentacle.tentacle_spec_base.programmer_args,
            "-v",
            "-w",
            str(filename_dfu),
        ]
        subprocess_run(
            args=args,
            cwd=directory_logs,
            logfile=directory_logs / FILENAME_FLASHING,
            timeout_s=60.0,
        )
