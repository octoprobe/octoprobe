"""
This file implements generic logic for all boards with a RP2040/RP2350 mcu or alike.
"""

import pathlib

import pyudev  # type: ignore
from usbhubctl.util_subprocess import assert_root_and_s_bit, subprocess_run

from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_pyudev import UdevEventBase, UdevFilter

_RPI_PICO_VENDOR = 0x2E8A
FILENAME_PICOTOOL = "picotool"

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


def rp2_udev_filter_boot_mode(usb_id: UsbID, usb_location: str) -> UdevFilter:
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
        actions=[
            "add",
        ],
    )


def picotool_flash_micropython(
    event: UdevEventBase, filename_firmware: pathlib.Path
) -> None:
    assert isinstance(event, Rp2UdevBootModeEvent)
    assert filename_firmware.is_file(), str(filename_firmware)

    filename_binary = assert_root_and_s_bit(FILENAME_PICOTOOL)
    args = [
        str(filename_binary),
        "load",
        "--update",
        # "--verify",
        "--execute",
        str(filename_firmware),
        "--bus",
        str(event.bus_num),
        "--address",
        str(event.dev_num),
    ]
    subprocess_run(args=args)
