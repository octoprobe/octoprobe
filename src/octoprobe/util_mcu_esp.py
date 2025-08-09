"""
This file implements generic logic for all esp boards

Copy logic from util_mcu_pyboard.py
"""

import logging
import pathlib
import sys
import typing

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareSpecBase
from .util_mcu import (
    FILENAME_FLASHING,
    UdevApplicationModeEvent,
    udev_filter_application_mode,
)
from .util_pyudev import UdevEventBase, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)

ESP32_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x10C4, 0xEA60),
    application=UsbID(0x10C4, 0xEA60),
)
"""
The ESP32_DEVKIT uses a UART Bridge Controller CP2102.
Therefore the above usb-vender/usb-product equal.
"""

ESP32_C3_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x10C4, 0xEA60),
    application=UsbID(0x10C4, 0xEA60),
)
"""
The ESP32_C3_DEVKIT uses a UART Bridge Controller CP2102.
Therefore the above usb-vender/usb-product equal.
"""

ESP32_S3_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x303A, 0x1001),
    application=UsbID(0x303A, 0x4001),
)

LOLIN_C3_MINI_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x303A, 0x1001),
    application=UsbID(0x303A, 0x1001),
)


class DutProgrammerEsptool(DutProgrammerABC):
    LABEL = "esptool"

    @typing.override
    def enter_boot_mode(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> UdevEventBase:
        # Press Boot Button
        logger.debug("relais close: IDX1_RELAYS_DUT_BOOT")
        tentacle.infra.mcu_infra.relays(relays_close=[IDX1_RELAYS_DUT_BOOT])

        try:
            tentacle.power.dut = False
            tentacle.power_dut_off_and_wait()

            with udev.guard as guard:
                tentacle.power.dut = True

                assert tentacle.tentacle_spec_base.mcu_usb_id is not None
                udev_filter = udev_filter_application_mode(
                    usb_id=tentacle.tentacle_spec_base.mcu_usb_id.boot,
                    usb_location=tentacle.infra.usb_location_dut,
                )

                return guard.expect_event(
                    udev_filter=udev_filter,
                    text_where=tentacle.dut.label,
                    text_expect="Expect mcu to become visible on udev after power on",
                    timeout_s=3.0,
                )

        finally:
            # Release Boot Button
            logger.debug("relais open: IDX1_RELAYS_DUT_BOOT")
            tentacle.infra.mcu_infra.relays(relays_open=[IDX1_RELAYS_DUT_BOOT])

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
        assert isinstance(tentacle, TentacleBase)
        assert isinstance(udev, UdevPoller)
        assert isinstance(directory_logs, pathlib.Path)
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert tentacle.dut is not None

        if tentacle.tentacle_spec_base.mcu_usb_id is not None:
            # The boards vender/product is defined
            # We powercycle the board and set the boot button
            event = self.enter_boot_mode(tentacle=tentacle, udev=udev)
            assert isinstance(event, UdevApplicationModeEvent)
            tty = event.tty
        else:
            # The boards vender/product is NOT defined
            # We just flash the board without pressing the boot button
            assert tentacle.dut.mp_remote_is_initialized
            tty = tentacle.dut.mp_remote.close()
            assert tty is not None

        filename_dfu = firmware_spec.filename
        args = [
            sys.executable,
            "-m",
            "esptool",
            f"--port={tty}",
            *tentacle.tentacle_spec_base.programmer_args,
            str(filename_dfu),
        ]

        subprocess_run(
            args=args,
            cwd=directory_logs,
            logfile=directory_logs / FILENAME_FLASHING,
            timeout_s=60.0,
        )
