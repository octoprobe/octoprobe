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


def udev_filter_application_mode(usb_id: UsbID) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    return UdevFilter(
        label="Application Mone",
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
