"""
This file implements generic logic for all SAMD boards

Device in application mode:
  * Mount volume with 2.1 MBytes
  * usb, add, 0x239A(9114)/0x8012(32786)

Device in boot mode:
  * Mount volume 'ITSYBOOT'
  * usb, add, 0x239A(9114)/0x000F(15)


USB Disk automount - links
==========================
https://wiki.ubuntuusers.de/UDisks2/
https://www.cyberciti.biz/faq/systemd-systemctl-view-status-of-a-service-on-linux/

systemctl status udisks2.service
sudo journalctl UNIT=udisks2.service --follow

udisksctl status


New 2025-06-02: bossac is supported too!
========================================
See: https://learn.adafruit.com/introducing-itsy-bitsy-m0?view=all
Chapter: Running bossac on the command line
"""

import logging
import pathlib
import time
import typing

import pyudev

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareBuildSpec, FirmwareSpecBase
from .util_mcu import (
    FILENAME_FLASHING,
    UdevApplicationModeEvent,
    udev_filter_application_mode,
)
from .util_pyudev import UdevEventBase, UdevFilter, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)

ADAFRUIT_ITSYBITSY_M0_EXPRESS_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x239A, 0x000F),
    application=UsbID(0xF055, 0x9802),
)


class SamdUdevBootModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.mount_point = UdevFilter.get_mount_point(device.device_node)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mount_point={self.mount_point})"


class DutProgrammerSamdBossac(DutProgrammerABC):
    LABEL = "samd_bossac"

    @typing.override
    def enter_boot_mode(
        self, tentacle: TentacleBase, udev: UdevPoller
    ) -> UdevEventBase:
        assert tentacle.tentacle_spec_base.mcu_usb_id is not None

        # Initial condition: Power and RESET pressed
        logger.debug("Close relay and power DUT")
        tentacle.switches.dut = False
        # This pause is required to make sure that a previous mount is removed
        # Try to lower 'duration_on_s' but make sure that the DUT is previously powered and a drive is mounted.
        time.sleep(0.1)
        with tentacle.infra.mcu_infra.relays_ctx(
            "Press boot button", relays_close=[IDX1_RELAYS_DUT_BOOT]
        ):
            tentacle.switches.dut = True
            logger.debug("Enter boot pulse section")

            with udev.guard as guard:
                # send 'double tab' pulse
                duration_pulse_ms = 200  # Ok: 100, 200, 500. Failed: 50

                tentacle.infra.mcu_infra.relays_pulse(
                    relays=IDX1_RELAYS_DUT_BOOT,
                    initial_closed=True,
                    durations_ms=[
                        duration_pulse_ms,  # Unpress, wait for booting. Ok: 200, 500, 1000
                        duration_pulse_ms,  # First tab
                        duration_pulse_ms,
                        duration_pulse_ms,  # Second tab
                        duration_pulse_ms,
                    ],
                )

                # udev_filter = samd_udev_filter_boot_mode2(
                #     usb_id=tentacle.tentacle_spec_base.mcu_usb_id.boot,
                #     usb_location=tentacle.infra.usb_location_dut,
                # )
                udev_filter = udev_filter_application_mode(
                    usb_id=tentacle.tentacle_spec_base.mcu_usb_id.boot,
                    usb_location=tentacle.infra.usb_location_dut,
                )

                return guard.expect_event(
                    udev_filter=udev_filter,
                    text_where=tentacle.dut.label,
                    text_expect="Expect mcu to become visible on udev after power on",
                    timeout_s=10.0,
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
        filename_bin = firmware_spec.filename
        # See: https://micropython.org/download/ARDUINO_NANO_33_BLE_SENSE/
        args = [
            "bossac",
            "--erase",
            "--write",
            "--port",
            event.tty,
            "--info",
            "--verify",
            # "--debug",
            # "--usb-port",
            "--reset",
            *tentacle.tentacle_spec_base.programmer_args,
            str(filename_bin),
        ]
        subprocess_run(
            args=args,
            cwd=directory_logs,
            logfile=directory_logs / FILENAME_FLASHING,
            timeout_s=60.0,
        )


def samd_udev_filter_boot_mode_obsolete(usb_id: UsbID, usb_location: str) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    assert isinstance(usb_location, str)

    return UdevFilter(
        label="Boot Mode",
        usb_location=usb_location,
        udev_event_class=SamdUdevBootModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="block",
        device_type="disk",
        actions=["add"],
    )
