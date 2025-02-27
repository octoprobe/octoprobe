"""
This file implements generic logic for all pyboard alike boards.
"""

import logging
import pathlib
import typing

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareSpecBase
from .util_mcu import FILENAME_FLASHING
from .util_mcu_pico import Rp2UdevBootModeEvent
from .util_pyudev import UdevEventBase, UdevFilter, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)
PYBOARD_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x0483, 0xDF11),
    application=UsbID(0xF055, 0x9800),
)
NUCLEO_WB55_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x0483, 0xDF11),
    application=UsbID(0xF055, 0x9800),
)


def pyboard_udev_filter_boot_mode(usb_id: UsbID, usb_location: str) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    return UdevFilter(
        label="Pyboard Boot Mode",
        usb_location=usb_location,
        udev_event_class=Rp2UdevBootModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="usb",
        device_type="usb_device",
        actions=["add"],
    )


class DutProgrammerDfuUtil(DutProgrammerABC):
    LABEL = "dfu-util"

    @typing.override
    def enter_boot_mode(
        self, tentacle: TentacleBase, udev: UdevPoller
    ) -> UdevEventBase:
        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX1_RELAYS_DUT_BOOT])

        tentacle.power.dut = False
        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is not None
            udev_filter = pyboard_udev_filter_boot_mode(
                usb_id=tentacle.tentacle_spec_base.mcu_usb_id.boot,
                usb_location=tentacle.infra.usb_location_dut,
            )

            return guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after power on",
                timeout_s=3.0,
            )

    @typing.override
    def flash(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert isinstance(tentacle, TentacleBase)
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert (
            len(tentacle.tentacle_spec_base.programmer_args) == 0
        ), "Not yet supported"
        assert tentacle.dut is not None

        event = self.enter_boot_mode(tentacle=tentacle, udev=udev)

        assert isinstance(event, Rp2UdevBootModeEvent)
        filename_dfu = firmware_spec.filename
        args = [
            "dfu-util",
            "--serial",
            event.serial,
            "--download",
            str(filename_dfu),
        ]
        subprocess_run(
            args=args,
            cwd=directory_logs,
            logfile=directory_logs / FILENAME_FLASHING,
            timeout_s=60.0,
        )

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX1_RELAYS_DUT_BOOT])
