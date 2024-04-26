import pathlib

import pyudev  # type: ignore
from usbhubctl.util_subprocess import assert_root_and_s_bit, subprocess_run

from .util_constants import DIRECTORY_DOWNLOADS
from .util_pyudev import UdevEventBase, UdevFilter

RP2_VENDOR = 0x2E8A
RP2_PRODUCT_BOOT_MODE = 0x0003
RP2_PRODUCT_APPLICATION_MODE = 0x0005


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


UDEV_FILTER_RP2_BOOT_MODE = UdevFilter(
    label="Raspberry Pi Pico Boot Mode",
    udev_event_class=UdevBootModeEvent,
    id_vendor=RP2_VENDOR,
    id_product=RP2_PRODUCT_BOOT_MODE,
    subsystem="usb",
    device_type="usb_device",
    actions=[
        "add",
    ],
)
UDEV_FILTER_RP2_APPLICATION_MODE = UdevFilter(
    label="Raspberry Pi Pico Application Mone",
    udev_event_class=UdevApplicationModeEvent,
    id_vendor=RP2_VENDOR,
    id_product=RP2_PRODUCT_APPLICATION_MODE,
    subsystem="tty",
    device_type=None,
    actions=[
        "add",
        "remove",
    ],
)


def rp2_flash_micropython(event: UdevEventBase, filename_uf2: pathlib.Path) -> None:
    assert isinstance(event, UdevBootModeEvent)
    assert filename_uf2.is_file()

    filename_picotool = DIRECTORY_DOWNLOADS / "picotool"
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
