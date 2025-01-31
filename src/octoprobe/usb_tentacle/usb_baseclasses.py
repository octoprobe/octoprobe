from __future__ import annotations

import logging
import pathlib

import usb.core
from serial.tools import list_ports_linux

from .usb_constants import UsbPlug, UsbPlugs

logger = logging.Logger(__file__)


class Location:
    def __init__(self, bus: int, path: list[int]) -> None:
        self.bus = bus
        self.path = path
        path_text = ".".join(map(str, self.path))
        self.short = f"{self.bus}-{path_text}"

    @staticmethod
    def factory_sysfs(port: list_ports_linux.SysFS) -> Location:
        """
        Example location: '3-1.4.1.1:1.0'
        This is returnemd from the 'location' property of the 'Device' object of the 'serial' library.
        """
        assert isinstance(port, list_ports_linux.SysFS)
        # This is a RP2 in application mode.
        # Returned from package 'list_ports', method 'serial.list_ports'
        location, _, _ = port.location.partition(":")
        bus_str, _, path_str = location.partition("-")
        bus = int(bus_str)
        path = [int(p) for p in path_str.split(".")]
        return Location(bus=bus, path=path)

    @staticmethod
    def factory_device(device: usb.core.Device) -> Location:
        assert isinstance(device, usb.core.Device)
        # This is a RP2 in boot mode.
        return Location(bus=device.bus, path=list(device.port_numbers))

    def is_my_hub(self, hub4_location: Location) -> bool:
        """
        Expected:
          'this' is the location of the rp2 on the tentacle
          'hub4_location' is the location of the hub on the same tentacle
        """
        if self.bus != hub4_location.bus:
            return False
        if self.path[:-1] == hub4_location.path:
            assert (
                self.path[-1] == 1
            ), f"The rp2 is always connected on port 1, but not {self.short}!"
            return True
        return False

    def sysfs_path(self, plug: UsbPlug) -> pathlib.Path:
        """
        The path to the sysfs filesystem
        """
        return pathlib.Path(
            f"/sys/bus/usb/devices/{self.short}:1.0/{self.short}-port{plug.number}/disable"
        )

    def set_power(self, plug: UsbPlug, on: bool) -> None:
        assert isinstance(plug, UsbPlug)

        path = self.sysfs_path(plug=plug)
        value = "0" if on else "1"
        path.write_text(value)

    def get_power(self, plug: UsbPlug) -> bool:
        assert isinstance(plug, UsbPlug)
        path = self.sysfs_path(plug=plug)
        value = path.read_text().strip()
        assert value in ("0", "1")
        return value == "0"

    def set_plugs(self, plugs: UsbPlugs) -> None:
        """
        Important: This call does NOT update the caching in UsbTentacle!
        """
        for plug, on in plugs.ordered:
            self.set_power(plug=plug, on=on)
