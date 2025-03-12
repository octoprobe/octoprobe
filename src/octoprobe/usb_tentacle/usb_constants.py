"""
This module defines the different USB functions like rp2_infra or dut.
The different version are hidden so for one function, for exaple rp2_infra, different
USB hub ports may be assigned depending of the version of the tentacle.
"""

from __future__ import annotations

import enum


class TyperPowerCycle(str, enum.Enum):
    """
    Used as command line argument (Typer)
    """

    INFRA = "infra"
    PROBE = "probe"  # Only v0.4
    INFRBOOT = "infraboot"
    DUT = "dut"
    OFF = "off"


class UsbPlug(int, enum.Enum):
    """
    Every tentacle has a USB hub.
    Every port of this hub as a function, we call it 'UsbPlug'.
    """

    # TODO: Rename to PICOINFRA
    INFRA = 42
    """
    Power AND data for rp2_infra.
    Power for rp2_probe
    """
    # TODO: Rename to PICOPROBE
    PROBE = 43
    """
    Only v0.4
    Data ONLY for rp2_probe (power is shared with rp2_infra)
    """
    INFRABOOT = 44
    """
    If low: Enable Boot for rp2_infra AND rp2_probe.
    """
    DUT = 45
    """
    Power AND data for DUT.
    """
    ERROR = 46
    """
    Only v0.3
    Power for red error led
    """

    @property
    def text(self) -> str:
        return self.name.lower()


class TyperUsbPlug(str, enum.Enum):
    """
    Used as command line argument (Typer)
    """

    INFRA = "infra"
    PROBE = "probe"  # Only v0.4
    INFRABOOT = "infraboot"
    DUT = "dut"

    ERROR = "error"  # only v0.3

    @property
    def usbplug(self) -> UsbPlug:
        return {
            TyperUsbPlug.INFRA: UsbPlug.INFRA,
            TyperUsbPlug.PROBE: UsbPlug.PROBE,
            TyperUsbPlug.INFRABOOT: UsbPlug.INFRABOOT,
            TyperUsbPlug.DUT: UsbPlug.DUT,
            TyperUsbPlug.ERROR: UsbPlug.ERROR,
        }[self]

    @staticmethod
    def convert(typer_usb_plugs: list[TyperUsbPlug] | None) -> list[UsbPlug] | None:
        if typer_usb_plugs is None:
            return None
        return [plug.usbplug for plug in typer_usb_plugs]


class UsbPlugs(dict[UsbPlug, bool]):
    _DICT_DEFAULT_OFF = {
        UsbPlug.INFRA: False,
        UsbPlug.PROBE: False,
        UsbPlug.INFRABOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.ERROR: False,
    }

    _DICT_INFRA_ON = {
        UsbPlug.INFRA: True,
        UsbPlug.PROBE: True,
        UsbPlug.INFRABOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.ERROR: False,
    }

    @property
    def ordered(self) -> list[tuple[UsbPlug, bool]]:
        """
        Always power the power in the same order:
        * first switch off plugs.
        * then switch on plugs.
        """
        return sorted(self.items(), key=lambda item: (item[1], item[0].value))

    @property
    def text(self) -> str:
        plugs: list[str] = []
        for up in UsbPlug:
            try:
                plugs.append(self._get_text(up))
            except KeyError:
                continue
        return ",".join(plugs)

    def _get_text(self, up: UsbPlug) -> str:
        """
        Raise KeyError if UsbPower not found
        """
        v = self[up]
        sign = "+" if v else "-"
        return sign + up.text

    @staticmethod
    def all_on() -> UsbPlugs:
        return UsbPlugs({p: True for p in UsbPlug})

    @staticmethod
    def all_off() -> UsbPlugs:
        return UsbPlugs({p: False for p in UsbPlug})

    @classmethod
    def default_off(cls) -> UsbPlugs:
        return UsbPlugs(cls._DICT_DEFAULT_OFF)

    @classmethod
    def default_infra_on(cls) -> UsbPlugs:
        return UsbPlugs(cls._DICT_INFRA_ON)
