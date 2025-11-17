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

logger = logging.getLogger(__file__)


class HubPortNumber(enum.IntEnum):
    """
    Every tentacle has a 4 port USB hub.
    This enum is the number for every port.
    """

    PORT1_INFRA = 1
    """
    USB: rp_infra
    POWER: rp_infra (v0.3)
    POWER: rp_infra and rp_probe (v0.5+)
    """
    PORT2_INFRABOOT = 2
    """
    USB: none.
    POWER: rp_infra-boot
    """
    PORT3_DUT = 3
    """
    USB: DUT
    POWER: DUT (v0.3)
    POWER: not connected (v0.5+)
    """
    PORT4_PROBE_LEDERROR = 4
    """
    USB: not connected (v0.3)
    USB: rp_probe (v0.5+)
    POWER: LED_ERROR (v0.3)
    POWER: not connected (v0.5+)
    """


class UsbLocationDoesNotExistException(Exception):
    """
    Thrown if we can not retrieve a USB location.
    """


@dataclasses.dataclass(frozen=True, repr=True)
class UsbPort:
    """
    A board which is connected to a USB plug.
    The 'usb_location' may change when powercycling the hub.
    However, the serial port may change when powercycling the board.
    """

    usb_location: str

    def __post_init__(self) -> None:
        pass

    @property
    def device_sysfs(self) -> list_ports_linux.SysFS | None:
        return UsbPort.find_device_sysfs_by_usb_location(
            usb_location_short=self.usb_location
        )

    @property
    def device_text(self) -> str:
        device_sysfs = self.device_sysfs
        if device_sysfs is None:
            return "-"

        return str(device_sysfs)

    @property
    def usb_text(self) -> str:
        device_usb = UsbPort.find_usb_device_usb_location(self.usb_location)
        if device_usb is None:
            return "-"

        return f"{device_usb.idVendor:04X}:{device_usb.idProduct:04X}, dev {device_usb.address}, {device_usb.manufacturer}, {device_usb.product}, {device_usb.serial_number}"

    @staticmethod
    def find_device_sysfs_by_usb_location(
        usb_location_short: str,
    ) -> list_ports_linux.SysFS | None:
        """
        Given a usb location, for example "1-3.4.1", finds is corresponding port.
        Return None, if no port is assigned or the connected board is powered off.
        """
        for port in list_ports_linux.comports():
            try:
                location = Location.factory_sysfs(port=port)
            except UsbLocationDoesNotExistException:
                continue
            if location.short == usb_location_short:
                assert isinstance(port, list_ports_linux.SysFS)
                return port

        return None

    @staticmethod
    def find_usb_device_usb_location(
        usb_location_short: str,
    ) -> usb.core.Device:
        devices = usb.core.find(find_all=True)

        for device in devices:
            # Check if port_numbers is available
            if device.port_numbers is None:
                continue

            device_usb_location = (
                f"{device.bus}-{'.'.join(map(str, device.port_numbers))}"
            )
            if usb_location_short == device_usb_location:
                assert isinstance(device, usb.core.Device)
                return device
        return None


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

    def __repr__(self) -> str:
        return self.short

    @staticmethod
    def factory_sysfs(port: list_ports_linux.SysFS) -> Location:
        """
        Example location: '3-1.4.1.1:1.0'
        This is returnemd from the 'location' property of the 'Device' object of the 'serial' library.
        """
        assert isinstance(port, list_ports_linux.SysFS)
        # This is a Pico in application mode.
        # Returned from package 'list_ports', method 'serial.list_ports'
        if port.location is None:
            raise UsbLocationDoesNotExistException(port.device)

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
