"""
This module defines the different USB functions like pico_infra or dut.
The different version are hidden so for one function, for exaple pico_infra, different
USB hub ports may be assigned depending of the version of the tentacle.
"""

from __future__ import annotations

import abc
import enum


class HwVersion(enum.StrEnum):
    V03 = "v0.3"
    V05 = "v0.5"
    V06 = "v0.6"

    @staticmethod
    def is_V05or_newer(version: str) -> bool:
        return HwVersion.factory(version) >= HwVersion.V05

    @staticmethod
    def factory(version: str) -> HwVersion:
        assert isinstance(version, str)
        if isinstance(version, HwVersion):
            return version

        try:
            return HwVersion(version)
        except ValueError as e:
            raise ValueError(
                f"Unknown HwVersion '{version}'! Valid values are {', '.join([v.value for v in HwVersion])}."
            ) from e


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
    TODO(Hans):
    Before:
      This matched to the usb ports.
    Now:
      This matches to on/off functionality which may be implemented differently on different tentacle hardware versions.
      It matches TyperUsbPlug

    Every tentacle has a USB hub.
    Every port of this hub as a function, we call it 'UsbPlug'.
    """

    PICO_INFRA = enum.auto()
    """True: rp_infra is powered"""
    PICO_INFRA_BOOT = enum.auto()
    """False: rp_infra boot button pressed"""
    PICO_PROBE_RUN = enum.auto()
    """True: rp_probe run (reset released)"""
    PICO_PROBE_BOOT = enum.auto()
    """False: rp_probe boot button pressed"""

    DUT = enum.auto()
    """True: DUT is powerered"""
    LED_ERROR = enum.auto()
    """True: LED_ERROR is on bright"""
    LED_ACTIVE = enum.auto()
    """True: LED_ACTIVE is on bright"""

    RELAY1 = enum.auto()
    """True: RELAYx is closed"""
    RELAY2 = enum.auto()
    RELAY3 = enum.auto()
    RELAY4 = enum.auto()
    RELAY5 = enum.auto()
    RELAY6 = enum.auto()
    RELAY7 = enum.auto()

    @property
    def text(self) -> str:
        return self.name.lower()

    @property
    def is_hub_plug(self) -> bool:
        """
        Return true if control is (on all hardware versions of the tentacles) via USB plugs
        """
        return self in (UsbPlug.PICO_INFRA, UsbPlug.PICO_INFRA_BOOT)

    @staticmethod
    def RELAYS() -> list[UsbPlug]:
        return [
            UsbPlug.RELAY1,
            UsbPlug.RELAY2,
            UsbPlug.RELAY3,
            UsbPlug.RELAY4,
            UsbPlug.RELAY5,
            UsbPlug.RELAY6,
            UsbPlug.RELAY7,
        ]

    @property
    def is_relay(self) -> bool:
        return UsbPlug.RELAY1 <= self <= UsbPlug.RELAY7

    @property
    def relay_number(self) -> int:
        """
        Returns 5 for RELAY5
        """
        assert UsbPlug.RELAY1 <= self <= UsbPlug.RELAY7
        return int(self.name[5])


class TyperUsbPlug(str, enum.Enum):
    """
    Used as command line argument (Typer)
    """

    PICO_INFRA = "infra"
    PICO_INFRA_BOOT = "infraboot"
    PICO_PROBE_BOOT = "probeboot"  # >= v0.5
    PICO_PROBE_RUN = "proberun"  # >= v0.5
    DUT = "dut"

    LED_ERROR = "led_error"
    LED_ACTIVE = "led_active"

    RELAY1 = "relay1"
    RELAY2 = "relay2"
    RELAY3 = "relay3"
    RELAY4 = "relay4"
    RELAY5 = "relay5"
    RELAY6 = "relay6"
    RELAY7 = "relay7"

    @property
    def usbplug(self) -> UsbPlug | None:
        return {
            TyperUsbPlug.PICO_INFRA: UsbPlug.PICO_INFRA,
            TyperUsbPlug.PICO_INFRA_BOOT: UsbPlug.PICO_INFRA_BOOT,
            TyperUsbPlug.DUT: UsbPlug.DUT,
            TyperUsbPlug.LED_ERROR: UsbPlug.LED_ERROR,
        }[self]

    @staticmethod
    def convert(typer_usb_plugs: list[TyperUsbPlug] | None) -> list[UsbPlug] | None:
        if typer_usb_plugs is None:
            return None
        return [plug.usbplug for plug in typer_usb_plugs]


_TRANSLATION_TABLE = (
    (UsbPlug.PICO_INFRA, TyperUsbPlug.PICO_INFRA),
    (UsbPlug.PICO_INFRA_BOOT, TyperUsbPlug.PICO_INFRA_BOOT),
    (UsbPlug.PICO_PROBE_BOOT, TyperUsbPlug.PICO_PROBE_BOOT),
    (UsbPlug.PICO_PROBE_RUN, TyperUsbPlug.PICO_PROBE_RUN),
    (UsbPlug.DUT, TyperUsbPlug.DUT),
    (UsbPlug.LED_ERROR, TyperUsbPlug.LED_ERROR),
    (UsbPlug.LED_ACTIVE, TyperUsbPlug.LED_ACTIVE),
    (UsbPlug.RELAY1, TyperUsbPlug.RELAY1),
    (UsbPlug.RELAY2, TyperUsbPlug.RELAY2),
    (UsbPlug.RELAY3, TyperUsbPlug.RELAY3),
    (UsbPlug.RELAY4, TyperUsbPlug.RELAY4),
    (UsbPlug.RELAY5, TyperUsbPlug.RELAY5),
    (UsbPlug.RELAY6, TyperUsbPlug.RELAY6),
    (UsbPlug.RELAY7, TyperUsbPlug.RELAY7),
)


class UsbPlugs(dict[UsbPlug, bool]):
    _DICT_DEFAULT_OFF = {
        UsbPlug.PICO_INFRA: False,
        UsbPlug.PICO_INFRA_BOOT: True,
        UsbPlug.PICO_PROBE_RUN: False,
        UsbPlug.PICO_PROBE_BOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.LED_ERROR: False,
    }

    _DICT_INFRA_ON = {
        UsbPlug.PICO_INFRA: True,
        UsbPlug.PICO_INFRA_BOOT: True,
        UsbPlug.PICO_PROBE_RUN: False,
        UsbPlug.PICO_PROBE_BOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.LED_ERROR: False,
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
        return UsbPlugs(dict.fromkeys(UsbPlug, True))

    @staticmethod
    def all_off() -> UsbPlugs:
        return UsbPlugs(dict.fromkeys(UsbPlug, False))

    @classmethod
    def default_off(cls) -> UsbPlugs:
        return UsbPlugs(cls._DICT_DEFAULT_OFF)

    @classmethod
    def default_infra_on(cls) -> UsbPlugs:
        return UsbPlugs(cls._DICT_INFRA_ON)


def usbplug2typerusbplug(usb_plug: UsbPlug) -> TyperUsbPlug:
    for u, t in _TRANSLATION_TABLE:
        if u is usb_plug:
            return t
    raise ValueError(f"Unknown {usb_plug}")


def typerusbplug2usbplug(typer_usb_plug: TyperUsbPlug) -> UsbPlug:
    for u, t in _TRANSLATION_TABLE:
        if t is typer_usb_plug:
            return u
    raise ValueError(f"Unknown {typer_usb_plug}")


class SwitchABC(abc.ABC):
    @property
    @abc.abstractmethod
    def usb_plug(self) -> UsbPlug: ...

    @abc.abstractmethod
    def set(self, on: bool) -> bool:
        """
        return True if the value changed.
        return True if the value did not change
        """
        ...

    @abc.abstractmethod
    def get(self) -> bool:
        """
        return True: LED on, Power on, Relays closed
        return False: LED off, Power off, Relays open
        """
        ...
