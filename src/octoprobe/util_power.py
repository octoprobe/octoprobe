from __future__ import annotations

import dataclasses
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
    def nummer(self) -> int:
        """
        Return the plug/port number from 1 to 4
        """
        return {
            UsbPlug.INFRA: 1,
            UsbPlug.INFRABOOT: 2,
            UsbPlug.DUT: 3,
            UsbPlug.ERROR: 4,
        }[self]


@dataclasses.dataclass
class UsbPlugs:
    plugs: dict[UsbPlug, bool] = dataclasses.field(default_factory=dict)

    _DICT_DEFAULT_OFF = {
        UsbPlug.INFRA: False,
        UsbPlug.INFRABOOT: True,
        UsbPlug.DUT: False,
        UsbPlug.ERROR: False,
    }

    def __post_init__(self) -> None:
        assert isinstance(self.plugs, dict)

    def set_default_off(self) -> None:
        self.plugs = self._DICT_DEFAULT_OFF

    def copy_from(self, plugs: UsbPlugs) -> None:
        self.plugs = plugs.plugs.copy()

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
        v = self.plugs[up]
        sign = "+" if v else "-"
        return sign + up.value

    def power(self, hub_location: Location) -> None:
        assert isinstance(hub_location, Location)
        connected_hub = util_octohub4.location_2_connected_hub(location=hub_location)
        for plug, on in self.plugs.items():
            p = connected_hub.get_plug(plug.nummer)
            p.power(on=on)

    @staticmethod
    def all_on() -> UsbPlugs:
        return UsbPlugs(plugs={p: True for p in UsbPlug})

    @staticmethod
    def all_off() -> UsbPlugs:
        return UsbPlugs(plugs={p: False for p in UsbPlug})

    @classmethod
    def default_off(cls) -> UsbPlugs:
        return UsbPlugs(plugs=cls._DICT_DEFAULT_OFF)


class TentaclePlugsPower:
    """
    We do not know the power state for each usb plug from the usb subsystem.
    But this class caches the state writtein in 'self._plugs'.
    So we can create proberties to retrieve the power state.
    """

    def __init__(self, hub_location: Location) -> None:
        self._hub_location = hub_location
        self._plugs = UsbPlugs()

    def set_default_off(self) -> bool:
        plugs = UsbPlugs.default_off()
        plugs.power(self._hub_location)
        self._plugs.copy_from(plugs)

    @property
    def infra(self) -> bool:
        return self._plugs.plugs[UsbPlug.INFRA]

    @infra.setter
    def infra(self, on: bool) -> None:
        self._power(UsbPlug.INFRA, on)

    @property
    def infraboot(self) -> bool:
        return self._plugs.plugs[UsbPlug.INFRABOOT]

    @infraboot.setter
    def infraboot(self, on: bool) -> None:
        self._power(UsbPlug.INFRABOOT, on)

    @property
    def dut(self) -> bool:
        return self._plugs.plugs[UsbPlug.DUT]

    @dut.setter
    def dut(self, on: bool) -> None:
        self._power(UsbPlug.DUT, on)

    @property
    def error(self) -> bool:
        return self._plugs.plugs[UsbPlug.ERROR]

    @error.setter
    def error(self, on: bool) -> None:
        self._power(UsbPlug.ERROR, on)

    def _power(self, plug: UsbPlug, on: bool) -> None:
        plugs = UsbPlugs(plugs={plug: on})
        plugs.power(self._hub_location)
        self._plugs.plugs[plug] = on
