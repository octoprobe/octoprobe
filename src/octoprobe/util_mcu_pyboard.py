"""
This file implements generic logic for all pyboard alike boards.
"""

from .util_baseclasses import BootApplicationUsbID, UsbID
from .util_mcu_rp2 import Rp2UdevBootModeEvent
from .util_pyudev import UdevFilter

PYBOARD_USB_ID = BootApplicationUsbID(
    boot=UsbID(0x0483, 0xDF11),
    application=UsbID(0xF055, 0x9800),
)


def pyboard_udev_filter_boot_mode(usb_id: UsbID) -> UdevFilter:
    assert isinstance(usb_id, UsbID)
    return UdevFilter(
        label="Pyboard Boot Mode",
        udev_event_class=Rp2UdevBootModeEvent,
        id_vendor=usb_id.vendor_id,
        id_product=usb_id.product_id,
        subsystem="usb",
        device_type="usb_device",
        actions=[
            "add",
        ],
    )
