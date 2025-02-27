from __future__ import annotations

import dataclasses
import enum
import logging
import pathlib

import usb.core
from serial.tools import list_ports_linux

from .usb_constants import UsbPlug, UsbPlugs

logger = logging.Logger(__file__)


class HubPort(enum.IntEnum):
    PORT_1 = 1
    PORT_2 = 2
    PORT_3 = 3
    """
    DUT
    """
    PORT_4 = 4


@dataclasses.dataclass
class TentacleVersion:
    port_rp2_infra: HubPort
    port_rp2_probe: HubPort | None
    port_rp2_boot: HubPort
    port_rp2_dut: HubPort
    port_rp2_error: HubPort | None
    ports: set[int]


TENTACLE_VERSION_V03 = TentacleVersion(
    port_rp2_infra=HubPort.PORT_1,
    port_rp2_boot=HubPort.PORT_2,
    port_rp2_dut=HubPort.PORT_3,
    port_rp2_error=HubPort.PORT_4,
    port_rp2_probe=None,
    ports={HubPort.PORT_1},
)
TENTACLE_VERSION_V04 = TentacleVersion(
    port_rp2_probe=HubPort.PORT_1,
    port_rp2_infra=HubPort.PORT_2,
    port_rp2_dut=HubPort.PORT_3,
    port_rp2_boot=HubPort.PORT_4,
    port_rp2_error=None,
    ports={HubPort.PORT_1, HubPort.PORT_2},
)


class Location:
    def __init__(self, bus: int, path: list[int]) -> None:
        self.bus = bus
        self.path = path
        path_text = ".".join(map(str, self.path))
        self.short = f"{self.bus}-{path_text}"
        """
        Tentacle v0.3:
          rp2_infra on hub_port 1
        Tentacle v0.4:
          rp2_infra on hub_port 2
          rp2_probe on hub_port 1
        """
        self.tentacle_version: TentacleVersion | None = None

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
