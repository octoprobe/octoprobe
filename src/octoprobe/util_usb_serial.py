"""
https://en.wikipedia.org/wiki/USB
https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst
"""

from __future__ import annotations

import dataclasses
import time

import serial
import usb.core
import usb.util
import usbhubctl
from serial.tools import list_ports
from usbhubctl import known_hubs, util_octohub4

from .util_power import PowerCycle, UsbPlug, UsbPlugs


class SerialNumberNotFoundException(Exception):
    pass


class QueryPySerial:
    """
    Do a query using the 'pyserial' package.

    Find all rp2 in application mode (serial)
    Find all rp2 in programming mode (pyusb)
    """

    def __init__(self) -> None:
        self.list_rp2_mode_application = self._query_rp2_application_mode()
        self.list_rp2_mode_boot = self._query_rp2_boot_mode()

    def _query_rp2_application_mode(self) -> list[serial.core.SysFs]:
        # pylint: disable=import-outside-toplevel
        from .util_mcu_rp2 import RPI_PICO_USB_ID

        result: list[serial.core.SysFs] = []

        for port in list_ports.comports():
            if port.vid != RPI_PICO_USB_ID.application.vendor_id:
                continue
            if port.pid != RPI_PICO_USB_ID.application.product_id:
                continue
            result.append(port)

        return result

    def _query_rp2_boot_mode(self) -> list[serial.core.SysFs]:
        # pylint: disable=import-outside-toplevel
        from .util_mcu_rp2 import RPI_PICO_USB_ID

        devices = usb.core.find(
            idVendor=RPI_PICO_USB_ID.boot.vendor_id,
            idProduct=RPI_PICO_USB_ID.boot.product_id,
            find_all=True,
        )
        return list(devices)


@dataclasses.dataclass
class QueryResultTentacle:
    """
    Usb has been scanned using 'pyusb' and 'usb' packages.
    This is the result of this scan.
    """

    hub_location: usbhubctl.Location
    """
    Example: bus=3, path=[1, 1]
    """
    rp2_serial_port: str | None = None
    """
    Example: /dev/ttyACM0
    """
    rp2_serial_number: str | None = None
    """
    Example: e463541647612835
    """
    rp2_boot_mode: bool = False
    """
    If set to true, the RP2 is in bootmode and the serial number may not be retrieved.
    """

    def __post_init__(self) -> None:
        assert isinstance(self.hub_location, usbhubctl.Location)
        assert isinstance(self.rp2_serial_port, str | None)
        assert isinstance(self.rp2_serial_number, str | None)
        assert isinstance(self.rp2_boot_mode, bool)

    @property
    def rp2_application_mode(self) -> bool:
        return self.rp2_serial_number is not None

    @property
    def rp2_detected(self) -> bool:
        """
        returns True if ether a RP2 in boot mode or application mode is detected on usb hub port 1.
        """
        return self.rp2_boot_mode or self.rp2_application_mode

    @property
    def short(self) -> str:
        if self.rp2_boot_mode:
            return f"tentacle {self.hub_location.short}: RP2 in boot (programming) mode"
        if self.rp2_application_mode:
            return f"tentacle {self.hub_location.short}: {self.rp2_serial_number} {self.rp2_serial_port}"
        return f"usb hub {self.hub_location.short}"

    @staticmethod
    def query(verbose: bool, use_topology_cache: bool = False) -> QueryResultTentacles:
        """
        Probably obsolete. Replaced by 'query_fast()".
        """
        result: QueryResultTentacles = QueryResultTentacles()
        if verbose:
            qs = QueryPySerial()

        def handle_all(hub: usbhubctl.ConnectedHub) -> QueryResultTentacle:
            hub_location = hub.root_path.location
            if verbose:
                for device in qs.list_rp2_mode_application:
                    device_location = usbhubctl.Location.factory(device=device)
                    if device_location.is_my_hub(hub_location):
                        return QueryResultTentacle(
                            hub_location=hub_location,
                            rp2_serial_port=device.device,
                            rp2_serial_number=device.serial_number,
                        )
                for device in qs.list_rp2_mode_boot:
                    device_location = usbhubctl.Location.factory(device=device)
                    if device_location.is_my_hub(hub_location):
                        return QueryResultTentacle(
                            hub_location=hub_location,
                            rp2_boot_mode=True,
                        )
            return QueryResultTentacle(hub_location=hub_location)

        if use_topology_cache:
            actual_usb_topology = None
        else:
            from usbhubctl import backend_query_lsusb  # pylint: disable=C0415

            actual_usb_topology = backend_query_lsusb.lsusb()
        dualhubs = known_hubs.octohub4.find_connected_dualhubs(
            actual_usb_topology=actual_usb_topology
        )
        for hub in dualhubs.hubs_usb2.hubs:
            result.append(handle_all(hub=hub))

        return result

    @staticmethod
    def query_fast() -> QueryResultTentacles:
        # pylint: disable=import-outside-toplevel
        from .util_mcu_rp2 import RPI_PICO_USB_ID

        hubs_port1: dict[str, usbhubctl.Location] = {}
        devices_octohub4 = util_octohub4.Octohubs.find_devices()
        for device in devices_octohub4:
            ports = ".".join([str(p) for p in device.port_numbers])
            location_port1 = f"{device.bus}-{ports}.1"
            hubs_port1[location_port1] = usbhubctl.Location.factory(device=device)

        tentacles = QueryResultTentacles()
        for port in list_ports.comports():
            if port.vid != RPI_PICO_USB_ID.application.vendor_id:
                continue
            if port.pid != RPI_PICO_USB_ID.application.product_id:
                continue
            location_full = port.location
            location, _, _ = location_full.partition(":")
            hub_location = hubs_port1.get(location, None)
            if hub_location is None:
                continue

            tentacles.append(
                QueryResultTentacle(
                    hub_location=hub_location,
                    rp2_serial_number=port.serial_number,
                    rp2_serial_port=port.device,
                )
            )

        return tentacles


class QueryResultTentacles(list[QueryResultTentacle]):
    """
    Usb has been scanned using 'pyusb' and 'usb' packages.
    This is the result of this scan.
    """

    def get(self, serial_number: str) -> QueryResultTentacle:
        for result in self:
            if result.rp2_serial_number == serial_number:
                return result
        raise SerialNumberNotFoundException(serial_number)

    def select(self, serials: list[str] | None) -> QueryResultTentacles:
        """
        if serial is None: return all tentacles
        """
        if serials is None:
            return self

        def matches(qrt: QueryResultTentacle) -> bool:
            for _serial in serials:
                if qrt.rp2_serial_number is not None:
                    # 'serial' may be a substring of 'rp2_serial_number'
                    pos = qrt.rp2_serial_number.find(_serial)
                    if pos == 0:
                        # At the beginning
                        return True
                    if pos == len(qrt.rp2_serial_number) - len(_serial):
                        # At the end
                        return True
            return False

        return QueryResultTentacles(filter(matches, self))

    def power(self, plugs: UsbPlugs) -> None:
        for hub in self:
            plugs.power(hub_location=hub.hub_location)

    def powercycle(self, power_cycle: PowerCycle) -> None:
        if power_cycle is PowerCycle.INFRA:
            self.power(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.power(plugs=UsbPlugs({UsbPlug.INFRA: True}))
            return

        if power_cycle is PowerCycle.INFRBOOT:
            self.power(plugs=UsbPlugs.default_off())
            self.power(plugs=UsbPlugs(plugs={UsbPlug.INFRABOOT: False}))
            time.sleep(1.0)
            self.power(plugs=UsbPlugs({UsbPlug.INFRA: True}))
            time.sleep(0.5)
            self.power(plugs=UsbPlugs({UsbPlug.INFRABOOT: True}))
            return

        if power_cycle is PowerCycle.DUT:
            self.power(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.power(plugs=UsbPlugs({UsbPlug.INFRA: True, UsbPlug.DUT: True}))
            return

        if power_cycle is PowerCycle.OFF:
            self.power(plugs=UsbPlugs.default_off())
            return

        raise NotImplementedError("Internal programming error")
