"""
This file implements generic logic for all boards with a Pico040/Pico350 mcu or alike.
"""

import logging
import pathlib

import pyudev  # type: ignore

from .lib_tentacle import TentacleBase
from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_constants import DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN
from .util_dut_programmer_abc import DutProgrammerABC, IDX1_RELAYS_DUT_BOOT
from .util_firmware_spec import FirmwareSpecBase
from .util_mcu import FILENAME_FLASHING
from .util_pyudev import UdevEventBase, UdevFilter, UdevPoller
from .util_subprocess import subprocess_run

logger = logging.getLogger(__name__)

_RPI_PICO_VENDOR = 0x2E8A
FILENAME_PICOTOOL = DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN / "picotool"

RPI_PICO_USB_ID = BootApplicationUsbID(
    boot=UsbID(_RPI_PICO_VENDOR, 0x0003),
    application=UsbID(_RPI_PICO_VENDOR, 0x0005),
)
RPI_PICO2_USB_ID = BootApplicationUsbID(
    boot=UsbID(_RPI_PICO_VENDOR, 0x000F),
    application=UsbID(_RPI_PICO_VENDOR, 0x0005),
)


class Rp2UdevBootModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.serial = device.properties["ID_SERIAL_SHORT"]
        self.dev_num = int(device.properties["DEVNUM"])
        self.bus_num = int(device.properties["BUSNUM"])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(serial={self.serial}, bus_num={self.bus_num}, dev_num={self.dev_num})"


class Rp2UdevBootModeEvent2(UdevEventBase):
    """
    Triggers a mount point when a USB drive was inserted.
    """

    def __init__(self, device: pyudev.Device):
        self.mount_point = UdevFilter.get_mount_point(
            device.device_node, allow_partition_mount=True
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mount_point={self.mount_point})"


def pico_udev_filter_boot_mode(usb_id: UsbID, usb_location: str) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    assert isinstance(usb_location, str)
    return UdevFilter(
        label="Raspberry Pi Pico Boot Mode",
        usb_location=usb_location,
        udev_event_class=Rp2UdevBootModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="usb",
        device_type="usb_device",
        actions=["add"],
    )


def pico_udev_filter_boot_mode2(usb_id: UsbID, usb_location: str) -> UdevFilter:
    """
    Triggers a mount point when a USB drive was inserted.
    """
    assert isinstance(usb_id, UsbID)
    assert isinstance(usb_location, str)

    return UdevFilter(
        label="Boot Mode",
        usb_location=usb_location,
        udev_event_class=Rp2UdevBootModeEvent2,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="block",
        device_type="disk",
        actions=["add"],
    )


def picotool_cmd(event: UdevEventBase, filename_firmware: str) -> list[str]:
    assert isinstance(event, Rp2UdevBootModeEvent)
    assert isinstance(filename_firmware, str)

    return [
        str(FILENAME_PICOTOOL),
        "load",
        "--update",
        # "--verify",
        "--bus",
        str(event.bus_num),
        "--address",
        str(event.dev_num),
        "--execute",
        filename_firmware,
    ]


def picotool_flash_micropython(
    event: UdevEventBase, directory_logs: pathlib.Path, filename_firmware: pathlib.Path
) -> None:
    assert isinstance(event, Rp2UdevBootModeEvent)
    assert filename_firmware.is_file(), str(filename_firmware)

    args = picotool_cmd(event=event, filename_firmware=str(filename_firmware))
    subprocess_run(
        args=args,
        cwd=directory_logs,
        logfile=directory_logs / FILENAME_FLASHING,
        timeout_s=30.0,
    )


class DutProgrammerPicotool(DutProgrammerABC):
    LABEL = "picotool"

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

        tentacle.infra.power_dut_off_and_wait()

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX1_RELAYS_DUT_BOOT])

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is not None
            udev_filter = pico_udev_filter_boot_mode(
                tentacle.tentacle_spec_base.mcu_usb_id.boot,
                usb_location=tentacle.infra.usb_location_dut,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect  to become visible on udev after power on",
                timeout_s=2.0,
            )

        assert isinstance(event, Rp2UdevBootModeEvent)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX1_RELAYS_DUT_BOOT])

        picotool_flash_micropython(
            event=event,
            directory_logs=directory_logs,
            filename_firmware=firmware_spec.filename,
        )
