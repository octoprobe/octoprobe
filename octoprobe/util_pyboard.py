from .util_pyudev import UdevFilter
from .util_rp2 import UdevApplicationModeEvent, UdevBootModeEvent

PYBOARD_VENDOR_BOOT_MODE = 0x0483
PYBOARD_PRODUCT_BOOT_MODE = 0xDF11

PYBOARD_VENDOR_APPLICATION_MODE = 0xF055
PYBOARD_PRODUCT_APPLICATION_MODE = 0x9800

UDEV_FILTER_PYBOARD_BOOT_MODE = UdevFilter(
    label="Pyboard Boot Mode",
    udev_event_class=UdevBootModeEvent,
    id_vendor=PYBOARD_VENDOR_BOOT_MODE,
    id_product=PYBOARD_PRODUCT_BOOT_MODE,
    subsystem="usb",
    device_type="usb_device",
    actions=[
        "add",
    ],
)

UDEV_FILTER_PYBOARD_APPLICATION_MODE = UdevFilter(
    label="Pyboard Application Mone",
    udev_event_class=UdevApplicationModeEvent,
    id_vendor=PYBOARD_VENDOR_APPLICATION_MODE,
    id_product=PYBOARD_PRODUCT_APPLICATION_MODE,
    subsystem="tty",
    device_type=None,
    actions=[
        "add",
        "remove",
    ],
)
