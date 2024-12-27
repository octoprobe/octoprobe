from __future__ import annotations

import abc
import logging
import typing

from usbhubctl.util_subprocess import subprocess_run

from octoprobe.util_mcu_pyboard import pyboard_udev_filter_boot_mode

from .util_baseclasses import PropertyString
from .util_constants import (
    TAG_PROGRAMMER,
)
from .util_firmware_spec import FirmwareBuildSpec, FirmwareSpecBase
from .util_mcu_esp import esptool_flash_micropython
from .util_mcu_rp2 import (
    Rp2UdevBootModeEvent,
    picotool_flash_micropython,
    rp2_udev_filter_boot_mode,
)

if typing.TYPE_CHECKING:
    from octoprobe.lib_tentacle import Tentacle
    from octoprobe.util_pyudev import UdevPoller


logger = logging.getLogger(__file__)

IDX_RELAYS_DUT_BOOT = 1


class DutProgrammer(abc.ABC):
    @abc.abstractmethod
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None: ...


class DutProgrammerDfuUtil(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareBuildSpec)
        assert len(tentacle.tentacle_spec.programmer_args) == 0, "Not yet supported"
        assert tentacle.dut is not None

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX_RELAYS_DUT_BOOT])

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = pyboard_udev_filter_boot_mode(
                usb_id=tentacle.tentacle_spec.mcu_usb_id.boot,
                usb_location=tentacle.infra.usb_location_dut,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after power on",
                timeout_s=3.0,
            )

        assert isinstance(event, Rp2UdevBootModeEvent)
        filename_dfu = firmware_spec.filename
        args = [
            "dfu-util",
            "--serial",
            event.serial,
            "--download",
            str(filename_dfu),
        ]
        subprocess_run(args=args, timeout_s=60.0)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX_RELAYS_DUT_BOOT])


class DutProgrammerPicotool(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert len(tentacle.tentacle_spec.programmer_args) == 0, "Not yet supported"
        assert tentacle.dut is not None

        tentacle.infra.power_dut_off_and_wait()

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX_RELAYS_DUT_BOOT])

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = rp2_udev_filter_boot_mode(
                tentacle.tentacle_spec.mcu_usb_id.boot,
                usb_location=tentacle.infra.usb_location_dut,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect RP2 to become visible on udev after power on",
                timeout_s=2.0,
            )

        assert isinstance(event, Rp2UdevBootModeEvent)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX_RELAYS_DUT_BOOT])

        picotool_flash_micropython(
            event=event, filename_firmware=firmware_spec.filename
        )


class DutProgrammerEsptool(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """
        The exp8622 does not require to be booted into boot(programming) mode.
        So we can reuse the port name from mp_remote
        """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpecBase)

        assert tentacle.dut is not None
        assert tentacle.dut.mp_remote_is_initialized
        tty = tentacle.dut.mp_remote.close()
        assert tty is not None

        esptool_flash_micropython(
            tty=tty,
            filename_firmware=firmware_spec.filename,
            programmer_args=tentacle.tentacle_spec.programmer_args,
        )


def dut_programmer_factory(tags: str) -> DutProgrammer:
    """
    Example 'tags': programmer=picotool,xy=5
    """
    programmer = PropertyString(tags).get_tag_mandatory(TAG_PROGRAMMER)
    if programmer == "picotool":
        return DutProgrammerPicotool()
    if programmer == "dfu-util":
        return DutProgrammerDfuUtil()
    if programmer == "esptool":
        return DutProgrammerEsptool()
    raise ValueError(f"Unknown '{programmer}' in '{tags}'!")
