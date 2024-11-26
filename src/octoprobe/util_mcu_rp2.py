"""
This file implements generic code for all boards with a RP2040/RP2350 mcu or alike.
"""

import pathlib

import pyudev  # type: ignore
from usbhubctl.util_subprocess import assert_root_and_s_bit, subprocess_run

from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_constants import DIRECTORY_USR_SBIN
from .util_pyudev import UdevEventBase, UdevFilter

_RPI_PICO_VENDOR = 0x2E8A

RPI_PICO_USB_ID = BootApplicationUsbID(
    boot=UsbID(_RPI_PICO_VENDOR, 0x0003),
    application=UsbID(_RPI_PICO_VENDOR, 0x0005),
)
RPI_PICO2_USB_ID = BootApplicationUsbID(
    boot=UsbID(_RPI_PICO_VENDOR, 0x000F),
    application=UsbID(_RPI_PICO_VENDOR, 0x0005),
)


class UdevBootModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.serial = device.properties["ID_SERIAL_SHORT"]
        self.dev_num = int(device.properties["DEVNUM"])
        self.bus_num = int(device.properties["BUSNUM"])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(serial={self.serial}, bus_num={self.bus_num}, dev_num={self.dev_num})"


class UdevApplicationModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.tty = device.device_node

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(tty={self.tty})"


def rp2_udev_filter_boot_mode(usb_id: UsbID) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    return UdevFilter(
        label="Raspberry Pi Pico Boot Mode",
        udev_event_class=UdevBootModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="usb",
        device_type="usb_device",
        actions=[
            "add",
        ],
    )


def rp2_udev_filter_application_mode(usb_id: UsbID) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    return UdevFilter(
        label="Raspberry Pi Pico Application Mone",
        udev_event_class=UdevApplicationModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="tty",
        device_type=None,
        actions=[
            "add",
            "remove",
        ],
    )


def rp2_flash_micropython(event: UdevEventBase, filename_uf2: pathlib.Path) -> None:
    assert isinstance(event, UdevBootModeEvent)
    assert filename_uf2.is_file(), str(filename_uf2)

    filename_picotool = DIRECTORY_USR_SBIN / "picotool"
    assert_root_and_s_bit(filename_picotool)
    args = [
        str(filename_picotool),
        "load",
        "--update",
        # "--verify",
        "--execute",
        str(filename_uf2),
        "--bus",
        str(event.bus_num),
        "--address",
        str(event.dev_num),
    ]
    subprocess_run(args=args)
