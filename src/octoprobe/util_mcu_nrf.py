"""
This file implements generic logic for all NRF boards
"""

import logging
import pathlib
import time

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareBuildSpec, FirmwareSpecBase
from .util_mcu import (
    FILENAME_FLASHING,
    UdevApplicationModeEvent,
    udev_filter_application_mode,
)
from .util_pyudev import UdevEventBase, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)

ARDUINO_NANO_33_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x2341, 0x005A),
    application=UsbID(0x2341, 0x025A),
)


class DutProgrammerBossac(DutProgrammerABC):
    LABEL = "bossac"

    def enter_boot_mode(
        self, tentacle: TentacleBase, udev: UdevPoller
    ) -> UdevEventBase:
        """
        https://micropython.org/download/ARDUINO_NANO_33_BLE_SENSE/
        Double tap the reset button to enter the bootloader...
        """
        tentacle.dut.mp_remote_close()

        time.sleep(0.5)  # Ok: 5.0, 1.0, 0.5, 0.2 Wrong: 0.1
        tentacle.infra.mcu_infra.relays(relays_close=[IDX1_RELAYS_DUT_BOOT])
        tentacle.power_dut = True

        with udev.guard as guard:
            # Now double tab. If the device is in application mode, this will bring it into boot mode.
            wait_ms = 500
            pulse_ms = 100
            tentacle.infra.mcu_infra.relays_pulse(
                relays=IDX1_RELAYS_DUT_BOOT,
                initial_closed=True,
                durations_ms=[
                    wait_ms,
                    pulse_ms,
                    pulse_ms,
                    # pulse_ms,
                    # pulse_ms,
                ],
            )

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

        event = self.enter_boot_mode(tentacle=tentacle, udev=udev)
        assert isinstance(event, UdevApplicationModeEvent)
        filename_dfu = firmware_spec.filename
        # See: https://micropython.org/download/ARDUINO_NANO_33_BLE_SENSE/
        args = [
            "bossac",
            "--erase",
            "--write",
            *tentacle.tentacle_spec_base.programmer_args,
            "--port",
            event.tty,
            "--info",
            # "--debug",
            "--usb-port",
            "--reset",
            str(filename_dfu),
        ]
        subprocess_run(
            args=args,
            cwd=directory_logs,
            logfile=directory_logs / FILENAME_FLASHING,
            timeout_s=60.0,
        )
