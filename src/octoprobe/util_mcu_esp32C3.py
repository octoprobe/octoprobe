"""
This file implements generic logic for esp32 boards
"""

import logging

from .util_baseclasses import BootApplicationUsbID, UsbID

logger = logging.getLogger(__name__)

_ESP32C3_VENDOR = 0x303A
_ESP32C3_PRODUCT = 0x1001

LOLIN_C3_MINI_USB_ID = BootApplicationUsbID(
    boot=UsbID(0xAAAA, 0xAAAA),  # boot mode not used!
    application=UsbID(_ESP32C3_VENDOR, _ESP32C3_PRODUCT),
)
