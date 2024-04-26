from __future__ import annotations

import dataclasses
from typing import Any

import serial  # type: ignore
import usb.core  # type: ignore
import usb.util  # type: ignore
import usbhubctl
import usbhubctl.known_hubs
from serial.tools import list_ports  # type: ignore

RP2_VENDOR = 0x2E8A
RP2_PRODUCT_BOOT_MODE = 0x0003
RP2_PRODUCT_APPLICATION_MODE = 0x0005


@dataclasses.dataclass
class ConnectedRP2:
    rp2_unique_id: str
    uart: str
    usb_path: usbhubctl.Path


class QuerySerial:
    """
    Algorithm:
      * Query
        * list_rp2_mode_application
        * list_rp2_mode_boot
        * list_octohub
      * Given: serials of required tentacles
        * find in list_rp2_mode_application
        * verify if hub is there
        * if serials are missing
          Message:
           * list_rp2_mode_boot
           * Hubs which are not powered as needed
      * Result
        * For every serial number a location for rp2 and hub

      * Fixing:
        * [x] Allow to power the hubs
        * [x] Allow to restart rp2 on hub port 1

    Modules
      * Query list_rp2_mode_application
      * Query list_rp2_mode_boot
      * list_octohub

      * Power all Hubs: Plug1 on, Plug2 on, Plug3 off, Plug4 off
    """

    def __init__(self):
        self.list_rp2_mode_application = self._query_rp2_application_mode()
        self.list_rp2_mode_boot = self._query_rp2_boot_mode()

    def _query_rp2_application_mode(self) -> list[serial.core.SysFs]:
        def inner():
            for port in list_ports.comports():
                if port.vid != RP2_VENDOR:
                    continue
                if port.pid != RP2_PRODUCT_APPLICATION_MODE:
                    continue
                yield port

        return list(inner())

    def _query_rp2_boot_mode(self) -> list[Any]:
        devices = usb.core.find(
            idVendor=RP2_VENDOR, idProduct=RP2_PRODUCT_BOOT_MODE, find_all=True
        )
        return list(devices)

    def print_rp2_application_mode(self) -> None:
        for rp2 in self.list_rp2_mode_application:
            print(f"Application Mode: {rp2.device} {rp2.location} {rp2.serial_number}")

    def print_rp2_boot_mode(self) -> None:
        for rp2 in self.list_rp2_mode_boot:
            print(f"Boot Mode: {rp2.bus}-{rp2.port_numbers}")
            hub = rp2.parent
            if (hub.idVendor != usbhubctl.known_hubs.OCTOHUB4_PRODUCT_ID.vendor) or (
                hub.idProduct != usbhubctl.known_hubs.OCTOHUB4_PRODUCT_ID.product
            ):
                # Not connected to octohub
                print("  Not connected to octohub!")
                continue

    def find(self, tentacle_serial_number: str) -> ConnectedRP2:
        for rp2 in self.list_rp2_mode_application:
            if rp2.serial_number.upper() == tentacle_serial_number:
                # def location_2_path(location: str) -> usbhubctl.Path:
                #     # Example rp2.location: '3-1.4.1.1:1.0'
                #     location, _, _ = location.partition(":")
                #     bus_str, _, path_str = location.partition("-")
                #     bus = int(bus_str)
                #     path = [int(p) for p in path_str.split(".")]
                #     return usbhubctl.Path(
                #         product_id=usbhubctl.known_hubs.OCTOHUB4_PRODUCT_ID,
                #         bus=bus,
                #         path=path,
                #     )

                # location_2_path(location=rp2.location)
                # usb_path = usbhubctl.Path(
                #     product_id=usbhubctl.known_hubs.OCTOHUB4_PRODUCT_ID, bus=x, path=x
                # )
                usb_path = usbhubctl.Path.serial_factory(location=rp2.location)
                return ConnectedRP2(
                    rp2_unique_id=tentacle_serial_number,
                    uart=rp2.device,
                    usb_path=usb_path,
                )
        raise IndexError(
            f"Tentacle with rp2_unique_id={tentacle_serial_number} not found!"
        )
