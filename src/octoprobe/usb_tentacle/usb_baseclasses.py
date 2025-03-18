"""
This module describes the USB related aspects of the tentacles.
The USB ports differ between tentacle versions.
This module also defines the GPIO assignements.
"""

from __future__ import annotations

import dataclasses
import enum
import logging
import pathlib

import usb.core
from serial.tools import list_ports_linux

from .usb_constants import UsbPlug

logger = logging.Logger(__file__)


class HubPortNumber(enum.IntEnum):
    """
    Every tentacle has a 4 port USB hub.
    This enum is the number for every port.
    """

    IDX1_1 = 1
    IDX1_2 = 2
    IDX1_3 = 3
    IDX1_4 = 4


@dataclasses.dataclass(frozen=True)
class MicropythonJina:
    """
    GPIOx used, See KiCad schematics.
    Different Tentacles version used different GPIO.
    """

    gpio_relays: list[int]
    """
    See KiCad schematics: RELAYS_1 .. RELAYS_7
    """
    gpio_led_active: int
    """
    See KiCad schematics: LED_ACTIVE
    """
    gpio_led_error: int
    """
    See KiCad schematics: LED_ERROR
    """

    @property
    def list_all_relays(self) -> list[int]:
        """
        relays [1, 2, 3, 4, 5, 6, 7]
        """
        return list(range(1, len(self.gpio_relays) + 1))


@dataclasses.dataclass(frozen=True)
class TentacleVersion:
    portnumber_pico_infra: HubPortNumber
    portnumber_pico_probe: HubPortNumber | None
    portnumber_infraboot: HubPortNumber
    portnumber_dut: HubPortNumber
    portnumber_error: HubPortNumber | None
    micropython_jina: MicropythonJina
    version: str

    def get_hub_port(self, plug: UsbPlug) -> HubPortNumber | None:
        """
        UsbPlug is the generic naming.
        This code converts it into the tentacle version specific number.
        """

        if plug == UsbPlug.PICO_INFRA:
            return self.portnumber_pico_infra
        if plug == UsbPlug.PICO_PROBE:
            return self.portnumber_pico_probe
        if plug == UsbPlug.DUT:
            return self.portnumber_dut
        if plug == UsbPlug.ERROR:
            return self.portnumber_error
        if plug == UsbPlug.BOOT:
            return self.portnumber_infraboot
        return None


TENTACLE_VERSION_V03 = TentacleVersion(
    portnumber_pico_infra=HubPortNumber.IDX1_1,
    portnumber_infraboot=HubPortNumber.IDX1_2,
    portnumber_dut=HubPortNumber.IDX1_3,
    portnumber_error=HubPortNumber.IDX1_4,
    portnumber_pico_probe=None,
    micropython_jina=MicropythonJina(
        gpio_relays=[1, 2, 3, 4, 5, 6, 7],
        gpio_led_active=24,
        gpio_led_error=25,  # GPIO25 is NOT used!
    ),
    version="v0.3",
)
TENTACLE_VERSION_V04 = TentacleVersion(
    portnumber_pico_probe=HubPortNumber.IDX1_1,
    portnumber_pico_infra=HubPortNumber.IDX1_2,
    portnumber_dut=HubPortNumber.IDX1_3,
    portnumber_infraboot=HubPortNumber.IDX1_4,
    portnumber_error=None,
    micropython_jina=MicropythonJina(
        gpio_relays=[8, 9, 10, 11, 12, 13, 14],
        gpio_led_active=24,
        gpio_led_error=15,
    ),
    version="v0.4",
)


class Location:
    def __init__(self, bus: int, path: list[int]) -> None:
        self.bus = bus
        self.path = path
        path_text = ".".join(map(str, self.path))
        self.short = f"{self.bus}-{path_text}"
        """
        Tentacle v0.3:
          pico_infra on hub_port 1
        Tentacle v0.4:
          pico_infra on hub_port 2
          pico_probe on hub_port 1
            pico_probe just controls USB communication, NOT USB power.
            pico_infra powers pico_infra AND pico_probe!
        """
        self.tentacle_version: TentacleVersion | None = None

    @staticmethod
    def factory_sysfs(port: list_ports_linux.SysFS) -> Location:
        """
        Example location: '3-1.4.1.1:1.0'
        This is returnemd from the 'location' property of the 'Device' object of the 'serial' library.
        """
        assert isinstance(port, list_ports_linux.SysFS)
        # This is a Pico in application mode.
        # Returned from package 'list_ports', method 'serial.list_ports'
        location, _, _ = port.location.partition(":")
        bus_str, _, path_str = location.partition("-")
        bus = int(bus_str)
        path = [int(p) for p in path_str.split(".")]
        return Location(bus=bus, path=path)

    @staticmethod
    def factory_device(device: usb.core.Device) -> Location:
        assert isinstance(device, usb.core.Device)
        # This is a Pico in boot mode.
        return Location(bus=device.bus, path=list(device.port_numbers))

    def sysfs_path(self, hub_port: HubPortNumber) -> pathlib.Path:
        """
        The path to the sysfs filesystem
        """
        return pathlib.Path(
            f"/sys/bus/usb/devices/{self.short}:1.0/{self.short}-port{hub_port.value}/disable"
        )

    def set_power(self, hub_port: HubPortNumber, on: bool) -> None:
        assert isinstance(hub_port, HubPortNumber)

        path = self.sysfs_path(hub_port=hub_port)
        value = "0" if on else "1"
        path.write_text(value)

    def get_power(self, hub_port: HubPortNumber) -> bool:
        assert isinstance(hub_port, HubPortNumber)
        path = self.sysfs_path(hub_port=hub_port)
        value = path.read_text().strip()
        assert value in ("0", "1")
        return value == "0"
