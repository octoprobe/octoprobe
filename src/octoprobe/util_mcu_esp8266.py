"""
This file implements generic logic for all esp8266 boards
"""

import logging

from .util_baseclasses import BootApplicationUsbID, UsbID

logger = logging.getLogger(__name__)

_ESP8266_VENDOR = 0x1A86
_ESP8266_PRODUCT = 0x7523

LOLIN_D1_MINI_USB_ID = BootApplicationUsbID(
    boot=UsbID(0xAAAA, 0xAAAA),  # boot mode not used!
    application=UsbID(_ESP8266_VENDOR, _ESP8266_PRODUCT),
)
