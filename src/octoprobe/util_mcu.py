"""
This file implements generic logic for all boards
"""

import pyudev  # type: ignore

from .util_baseclasses import UsbID
from .util_pyudev import UdevEventBase, UdevFilter


class UdevApplicationModeEvent(UdevEventBase):
    def __init__(self, device: pyudev.Device):
        self.tty = device.device_node

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(tty={self.tty})"


def udev_filter_application_mode(usb_location: str) -> UdevFilter:
    assert isinstance(usb_location, str)
    return UdevFilter(
        label="Application Mone",
        usb_location=usb_location,
        udev_event_class=UdevApplicationModeEvent,
        id_vendor=None,
        id_product=None,
        subsystem="tty",
        device_type=None,
        actions=[
            "add",
            "remove",
        ],
    )
