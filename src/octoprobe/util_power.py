from __future__ import annotations

import enum

from usbhubctl import Location, util_octohub4


class PowerCycle(str, enum.Enum):
    INFRA = "infra"
    INFRBOOT = "infraboot"
    DUT = "dut"
    OFF = "off"


class UsbPlug(str, enum.Enum):
    INFRA = "infra"
    INFRABOOT = "infraboot"
    DUT = "dut"
    ERROR = "error"

    @property
    def number(self) -> int:
        """
        Return the plug/port number from 1 to 4
        """
        return {
            UsbPlug.INFRA: 1,
            UsbPlug.INFRABOOT: 2,
            UsbPlug.DUT: 3,
            UsbPlug.ERROR: 4,
        }[self]


class UsbPlugs(dict[UsbPlug, bool]):
    _DICT_DEFAULT_OFF = {
        UsbPlug.INFRA: False,
        UsbPlug.INFRABOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.ERROR: False,
    }

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
        return sign + up.value

    @staticmethod
    def all_on() -> UsbPlugs:
        return UsbPlugs({p: True for p in UsbPlug})

    @staticmethod
    def all_off() -> UsbPlugs:
        return UsbPlugs({p: False for p in UsbPlug})

    @classmethod
    def default_off(cls) -> UsbPlugs:
        return UsbPlugs(cls._DICT_DEFAULT_OFF)


class TentaclePlugsPower:
    def __init__(self, hub_location: Location) -> None:
        assert isinstance(hub_location, Location)
        self._hub_location = hub_location

    def set_power_plugs(self, plugs: UsbPlugs) -> None:
        connected_hub = util_octohub4.location_2_connected_hub(
            location=self._hub_location
        )
        for plug, on in plugs.items():
            p = connected_hub.get_plug(plug.number)
            p.set_power(on=on)

    def _get_power_plug(self, plug: UsbPlug) -> bool:
        connected_hub = util_octohub4.location_2_connected_hub(
            location=self._hub_location
        )
        return connected_hub.get_plug(plug.number).get_power()

    def set_power_plug(self, plug: UsbPlug, on: bool) -> None:
        connected_hub = util_octohub4.location_2_connected_hub(
            location=self._hub_location
        )
        connected_hub.get_plug(plug.number).set_power(on=on)

    def set_default_off(self) -> None:
        self.set_power_plugs(UsbPlugs.default_off())

    @property
    def infra(self) -> bool:
        return self._get_power_plug(UsbPlug.INFRA)

    @infra.setter
    def infra(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.INFRA, on)

    @property
    def infraboot(self) -> bool:
        return self._get_power_plug(UsbPlug.INFRABOOT)

    @infraboot.setter
    def infraboot(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.INFRABOOT, on)

    @property
    def dut(self) -> bool:
        """
        USB-Power for the DUT-MCU
        """
        return self._get_power_plug(UsbPlug.DUT)

    @dut.setter
    def dut(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.DUT, on)

    @property
    def error(self) -> bool:
        return self._get_power_plug(UsbPlug.ERROR)

    @error.setter
    def error(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.ERROR, on)
