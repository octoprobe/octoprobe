from __future__ import annotations

import enum


class TyperPowerCycle(str, enum.Enum):
    INFRA = "infra"
    INFRBOOT = "infraboot"
    DUT = "dut"
    OFF = "off"


class UsbPlug(int, enum.Enum):
    INFRA = 1
    INFRABOOT = 2
    DUT = 3
    ERROR = 4

    @property
    def number(self) -> int:
        """
        Return the plug/port number from 1 to 4
        """
        return self.value

    @property
    def text(self) -> str:
        return self.name.lower()


class TyperUsbPlug(str, enum.Enum):
    INFRA = "infra"
    INFRABOOT = "infraboot"
    DUT = "dut"
    ERROR = "error"

    @property
    def usbplug(self) -> UsbPlug:
        return {
            TyperUsbPlug.INFRA: UsbPlug.INFRA,
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
        UsbPlug.INFRABOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.ERROR: False,
    }

    _DICT_INFRA_ON = {
        UsbPlug.INFRA: True,
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
        return sorted(self.items(), key=lambda item: (item[1], item[0].number))

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
