"""
Terms:

* rp2: A raspberry pi pico soldered on to the tentacle.
* hub4: A hub soldered on to the tentacle.
* plug: A hub has 4 plugs - we do NOT use the term 'port' as this term conflicts with serial port.
* port: A comport in the context of the python 'serial' package.
* port: A comport in the context of the python 'serial' package.
* usb_tentacle: Everything which is related to the USB on a tentacle.
* tentacle: A tentacle where the serial number is known - a tentacle which is in a state to be reay to be used in testing.

This module controls the tentacle via usb.

It allows to query for
* tentacles
* rp2 on the tentacle and there state:
  * unpowered
  * in boot mode
  * in application mode presenting its serial number

I the tentacles have been queried, this module allow to power on/off each power plub.

Implemenation - interfaces used:
* /sys/bus: Read/Write from /sys/bus to control the power of a usb plug.
"""

from __future__ import annotations

import dataclasses
import logging
import time

import usb.core
import usb.util
from serial.tools import list_ports, list_ports_linux
from usb.legacy import CLASS_HUB

from ..usb_tentacle.usb_baseclasses import Location
from ..usb_tentacle.usb_constants import TyperPowerCycle, UsbPlug, UsbPlugs

logger = logging.Logger(__file__)


# Specification of a raspberry pi pico soldered on to the tentacle
RP2_VENDOR = 0x2E8A
RP2_PRODUCT_BOOT_MODE = 0x0003
RP2_PRODUCT_APPLICATION_MODE = 0x0005

# Specification of a hub soldered on to a tentacle
HUB4_VENDOR = 0x0424
HUB4_PRODUCT = 0x2514


@dataclasses.dataclass(frozen=True, repr=True)
class UsbRp2:
    location: Location
    serial: str | None
    """
    None: rp2 is in boot mode and the serial is not known.
    """
    serial_port: str | None

    @property
    def application_mode(self) -> bool:
        return self.serial is not None

    @staticmethod
    def factory_sysfs(
        port: list_ports_linux.SysFS, serial: str, serial_port: str
    ) -> UsbRp2:
        return UsbRp2(
            location=Location.factory_sysfs(port=port),
            serial=serial,
            serial_port=serial_port,
        )

    @staticmethod
    def factory_device(device: usb.core.Device) -> UsbRp2:
        return UsbRp2(
            location=Location.factory_device(device=device),
            serial=None,
            serial_port=None,
        )


@dataclasses.dataclass(frozen=True, repr=True)
class UsbTentacle:
    """
    This class allows to set_power()/get_power() of on tentacle board.
    The state is cached - set_power()/get_power() will first check
    the _cache_on before accesing /sys/bus.
    """

    hub4_location: Location
    """
    The usb-location of the hub on the tentacle pcb.
    """

    rp2_infra: UsbRp2 | None
    """
    The usb-location of the rp2 on the tentacle pcb
    and the serial number if known.
    None: The rp2 is powered off.
    """

    _cache_on: dict[UsbPlug, bool] = dataclasses.field(default_factory=dict)

    def set_power(self, plug: UsbPlug, on: bool) -> bool:
        """
        return True: If the power changed
        return False: If the power was already correct
        """
        assert isinstance(plug, UsbPlug)
        assert isinstance(on, bool)

        plug_text = f"usbplug {plug.name} {self.hub4_location.short}"

        if on == self.get_power(plug=plug):
            logger.debug(f"{plug_text} is allready {on}")
            return False

        self._cache_on[plug] = on
        self.hub4_location.set_power(plug=plug, on=on)

        logger.debug(f"{plug_text} set({on})")
        return True

    def get_power(self, plug: UsbPlug) -> bool:
        assert isinstance(plug, UsbPlug)

        on = self._cache_on.get(plug, None)
        if on is not None:
            return on

        on = self.hub4_location.get_power(plug=plug)
        self._cache_on[plug] = on
        return on

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for plug, on in plugs.ordered:
            self.set_power(plug=plug, on=on)

    def powercycle(self, power_cycle: TyperPowerCycle) -> None:
        if power_cycle is TyperPowerCycle.INFRA:
            self.set_plugs(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True}))
            return

        if power_cycle is TyperPowerCycle.INFRBOOT:
            self.set_plugs(plugs=UsbPlugs.default_off())
            self.set_plugs(plugs=UsbPlugs({UsbPlug.INFRABOOT: False}))
            time.sleep(1.0)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True}))
            time.sleep(0.5)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.INFRABOOT: True}))
            return

        if power_cycle is TyperPowerCycle.DUT:
            self.set_plugs(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True, UsbPlug.DUT: True}))
            return

        if power_cycle is TyperPowerCycle.OFF:
            self.set_plugs(plugs=UsbPlugs.default_off())
            return

        raise NotImplementedError("Internal programming error")

    def __repr__(self) -> str:
        repr = f"UsbTentacle({self.hub4_location.short}"
        if self.rp2_infra is not None:
            repr += f"rp2(application_mode={self.rp2_infra.application_mode}"
            if self.rp2_infra.application_mode:
                repr += f",serial={self.rp2_infra.serial}"
                repr += f",serial_port={self.rp2_infra.serial_port}"
            repr += ")"
        repr += ")"
        return repr

    @property
    def short(self) -> str:
        if self.rp2_infra is None:
            return f"usb hub {self.hub4_location.short}"
        if self.rp2_infra.application_mode:
            return f"tentacle {self.hub4_location.short}: {self.rp2_infra.serial} {self.rp2_infra.serial_port}"
        return f"tentacle {self.hub4_location.short}: RP2 in boot (programming) mode"

    @property
    def serial(self) -> str:
        rp2_infra = self.rp2_infra
        assert rp2_infra is not None
        serial = rp2_infra.serial
        assert serial is not None
        return serial

    @property
    def serial_port(self) -> str:
        rp2_infra = self.rp2_infra
        assert rp2_infra is not None
        serial_port = rp2_infra.serial_port
        assert serial_port is not None
        return serial_port


class Rp2NoSerialException(Exception):
    def __init__(self, hub4_location: Location):
        self.hub4_location = hub4_location
        msg = f"Can not get the tentacles serial number: Expected rp2 on {hub4_location.short} to be in application mode!"
        super().__init__(msg)


def _query_hubs() -> list[Location]:
    """
    Return all connected tentacle hubs.
    """
    return [
        Location.factory_device(device=device)
        for device in usb.core.find(
            find_all=True,
            bDeviceClass=CLASS_HUB,
            idVendor=HUB4_VENDOR,
            idProduct=HUB4_PRODUCT,
        )
    ]


def _query_rp2_boot_mode() -> list[UsbRp2]:
    """
    Query all rp2 in boot mode.
    This will return also rp2 which are not soldered on the tentacles.
    """
    return [
        UsbRp2.factory_device(device=device)
        for device in usb.core.find(idVendor=RP2_VENDOR, find_all=True)
        if device.idProduct == RP2_PRODUCT_BOOT_MODE
    ]


def _query_rp2_serial() -> list[UsbRp2]:
    """
    Query all rp2 in application mode which provide the serial number.
    This will return also rp2 which are not soldered on the tentacles.
    """
    return [
        UsbRp2.factory_sysfs(
            port=port, serial=port.serial_number, serial_port=port.device
        )
        for port in list_ports.comports()
        if (RP2_VENDOR == port.vid) and (RP2_PRODUCT_APPLICATION_MODE == port.pid)
    ]


def _combine_hubs_and_rp2(
    hub4_locations, list_rp2, require_serial: bool
) -> UsbTentacles:
    """
    Now we combine 'hubs' and 'list_rp2'
    """

    def get_rp2_infra(hub4_location: Location) -> UsbRp2 | None:
        """
        There might be rp2 connected, but we are only intersted in the rp2 infra!
        """
        for rp2 in list_rp2:
            if rp2.location.is_my_hub(hub4_location):
                # This is a rp2 infra
                return rp2
        # This might be a third party hub using the same chip as the tentacle
        # This might be a tentacle which a broken rp2.
        if require_serial:
            raise Rp2NoSerialException(hub4_location=hub4_location)
        return None

    tentacles = UsbTentacles()
    for hub4_location in hub4_locations:
        rp2_infra = get_rp2_infra(hub4_location)
        tentacles.append(
            UsbTentacle(
                hub4_location=hub4_location,
                rp2_infra=rp2_infra,
            )
        )
    return tentacles


class UsbTentacles(list[UsbTentacle]):
    TIMEOUT_RP2_BOOT = 2.0

    def set_power(self, plug: UsbPlug, on: bool) -> None:
        for usb_tentacle in self:
            usb_tentacle.set_power(plug=plug, on=on)

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for usb_tentacle in self:
            usb_tentacle.set_plugs(plugs=plugs)

    def powercycle(self, power_cycle: TyperPowerCycle) -> None:
        for usb_tentacle in self:
            usb_tentacle.powercycle(power_cycle=power_cycle)

    def select(self, serials: list[str] | None) -> UsbTentacles:
        """
        if serial is None: return all tentacles
        """
        if serials is None:
            return self

        def matches(usb_tentacle: UsbTentacle) -> bool:
            for _serial in serials:
                if usb_tentacle.rp2_infra is None:
                    continue
                serial = usb_tentacle.rp2_infra.serial
                if serial is None:
                    continue
                # 'serial' may be a substring of 'rp2_serial_number'
                pos = serial.find(_serial)
                if pos == 0:
                    # At the beginning
                    return True
                if pos == len(serial) - len(_serial):
                    # At the end
                    return True
            return False

        return UsbTentacles(filter(matches, self))

    @classmethod
    def query(cls, require_serial: bool) -> UsbTentacles:
        """
        Some rp2 may not present a serial number as they are not powered.

        require_serial == True: Switch on all unpowered rp2 and wait till the serial numbers appear.
          If a hub does not find a corresponding rp2 serial number: An exception is thrown.
          This is typically used for testing.

        require_serial == False: Just query without changing any power states.
          This is typically used for code completion.

        # Manual testing of this class: require_serial == True:
        Rationale: A exception should be throw if there is tentacle is 'not in order'.
        If a tentacle rp2 is not powered, the query should power it on and wait till the rp2 appears.
        Throw an exception if after some timeout:
        * A tentacle rp2 is still in boot mode
        * A tentacle rp2 is still not powered


        # Manual testing of this class: require_serial == False:
        Rationale: The query should return fast without changing the power state.
        All tentacles should be visible:
        * Tentacle with serial
        * Tentacle with rp2 in boot mode
        * Tentacle with rp2 powered off
        """
        #
        # Identify all tentalces by getting a list of all hubs.
        # Power on all rp2 infra to be able to read the serial numbers.
        #
        hub4_locations = _query_hubs()
        if require_serial:
            for hub4_location in hub4_locations:
                hub4_location.set_power(UsbPlug.INFRA, on=True)
                hub4_location.set_power(UsbPlug.ERROR, on=False)

        begin_s = time.monotonic()
        #
        # We loop till all rp2 present there serial numbers.
        #
        while True:
            list_rp2 = _query_rp2_serial()
            if not require_serial:
                # if require_serial == False: We also query rp2 in boot mode
                list_rp2.extend(_query_rp2_boot_mode())

            try:
                tentacles = _combine_hubs_and_rp2(
                    hub4_locations=hub4_locations,
                    list_rp2=list_rp2,
                    require_serial=require_serial,
                )
                # if require_serial == False: We return immedately
                return tentacles
            except Rp2NoSerialException as e:
                # Give some time for the rp2 to start up
                duration_s = time.monotonic() - begin_s
                if duration_s > cls.TIMEOUT_RP2_BOOT:
                    # Switch the error LED on
                    e.hub4_location.set_power(UsbPlug.ERROR, on=True)
                    raise e from e
                time.sleep(0.2)


class TentaclePlugsPower:
    def __init__(self, hub_location: Location) -> None:
        assert isinstance(hub_location, Location)
        self._hub_location = hub_location

    def set_power_plugs(self, plugs: UsbPlugs) -> None:
        self._hub_location.set_plugs(plugs=plugs)

    def _get_power_plug(self, plug: UsbPlug) -> bool:
        return self._hub_location.get_power(plug=plug)

    def set_power_plug(self, plug: UsbPlug, on: bool) -> None:
        self._hub_location.set_power(plug=plug, on=on)

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


def main() -> None:
    time_start_s = time.monotonic()

    usb_tentacles = UsbTentacles.query(require_serial=True)

    print(f"{time.monotonic()-time_start_s:0.3f}s")

    for usb_tentacle in usb_tentacles:
        print(repr(usb_tentacle))


if __name__ == "__main__":
    main()
