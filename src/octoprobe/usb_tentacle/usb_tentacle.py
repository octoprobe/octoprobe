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
import re
import time

import usb.core
import usb.util
from serial.tools import list_ports, list_ports_linux
from usb.legacy import CLASS_HUB

from ..usb_tentacle.usb_baseclasses import (
    HubPortNumber,
    Location,
    TENTACLE_VERSION_V03,
    TENTACLE_VERSION_V04,
    TentacleVersion,
)
from ..usb_tentacle.usb_constants import TyperPowerCycle, UsbPlug, UsbPlugs

logger = logging.Logger(__file__)

SERIALNUMBER_SHORT = 4
SERIALNUMBER_DELIMITER = "-"

REGEX_SERIAL_DELIMITED = re.compile(r"^\w{12}-\w{4}$")
REGEX_SERIAL = re.compile(r"^\w{16}$")


def serial_delimited(serial: str) -> str:
    return (
        serial[:-SERIALNUMBER_SHORT]
        + SERIALNUMBER_DELIMITER
        + serial[-SERIALNUMBER_SHORT:]
    )


def is_serial_valid(serial: str) -> bool:
    return REGEX_SERIAL.match(serial) is not None


def is_serialdelimtied_valid(serial_delimited: str) -> bool:
    return REGEX_SERIAL_DELIMITED.match(serial_delimited) is not None


def assert_serial_valid(serial: str) -> None:
    if not is_serial_valid(serial=serial):
        raise ValueError(
            f"Serial '{serial}' is not valid. Expected: {REGEX_SERIAL.pattern}"
        )


def assert_serialdelimtied_valid(serial_delimited: str) -> None:
    if not is_serialdelimtied_valid(serial_delimited=serial_delimited):
        raise ValueError(
            f"Serial '{serial_delimited}' is not valid. Expected: {REGEX_SERIAL_DELIMITED.pattern}"
        )


# Specification of a raspberry pi pico soldered on to the tentacle
RP2_VENDOR = 0x2E8A
RP2_PRODUCT_BOOT_MODE = 0x0003
RP2_PRODUCT_APPLICATION_MODE = 0x0005

# Specification of a hub soldered on to a tentacle
HUB4_VENDOR = 0x0424
HUB4_PRODUCT = 0x2514


@dataclasses.dataclass(frozen=True, repr=True)
class UsbPico:
    location: Location
    serial: str | None
    """
    None: rp2 is in boot mode and the serial is not known.
    """
    serial_port: str | None

    @property
    def application_mode(self) -> bool:
        return self.serial is not None

    @property
    def serial_delimited(self) -> str | None:
        if self.serial is None:
            return None
        return serial_delimited(serial=self.serial)

    @staticmethod
    def factory_sysfs(
        port: list_ports_linux.SysFS,
        serial: str,
        serial_port: str,
    ) -> UsbPico:
        return UsbPico(
            location=Location.factory_sysfs(port=port),
            serial=serial,
            serial_port=serial_port,
        )

    @staticmethod
    def factory_device(device: usb.core.Device) -> UsbPico:
        return UsbPico(
            location=Location.factory_device(device=device),
            serial=None,
            serial_port=None,
        )

    @property
    def as_pico_probe(self) -> UsbPico:
        """
        Return this UsbRp2, but with the port number of the pico_probe.
        """
        assert TENTACLE_VERSION_V04.portnumber_pico_probe is not None
        path = [
            *self.location.path[:-1],
            TENTACLE_VERSION_V04.portnumber_pico_probe.value,
        ]
        return UsbPico(
            location=Location(bus=self.location.bus, path=path),
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

    tentacle_version: TentacleVersion

    pico_infra: UsbPico
    """
    The usb-location of the rp2 on the tentacle pcb
    and the serial number if known.
    None: The rp2 is powered off.
    """
    pico_probe: UsbPico | None = None

    # TODO: Obsolete?
    _cache_on: dict[UsbPlug, bool] = dataclasses.field(default_factory=dict)

    def set_power(self, plug: UsbPlug, on: bool) -> bool:
        """
        return True: If the power changed
        return False: If the power was already correct
        """
        assert isinstance(plug, UsbPlug)
        assert isinstance(on, bool)

        hub_port = self.get_hub_port(plug=plug)
        plug_text = f"usbplug {plug.name} {self.hub4_location.short} port {hub_port} ({self.tentacle_version.version})"

        if on == self.get_power(plug=plug):
            logger.debug(f"{plug_text} is allready {on}")
            return False

        self._cache_on[plug] = on
        if hub_port is None:
            # TODO: Handle correctly
            return False

        self.hub4_location.set_power(hub_port=hub_port, on=on)

        logger.debug(f"{plug_text} set({on})")
        return True

    def get_power(self, plug: UsbPlug) -> bool:
        assert isinstance(plug, UsbPlug)

        on = self._cache_on.get(plug, None)
        if on is not None:
            return on

        hub_port = self.get_hub_port(plug=plug)
        if hub_port is None:
            # TODO: Handle correctly
            return False
        on = self.hub4_location.get_power(hub_port=hub_port)
        self._cache_on[plug] = on
        return on

    def get_hub_port(self, plug: UsbPlug) -> HubPortNumber | None:
        hub_port = self.tentacle_version.get_hub_port(plug=plug)
        if hub_port is None:
            # TODO: Handle this error.
            msg = f"'{plug}' does not match any usb port"
            if plug in (UsbPlug.ERROR, UsbPlug.PICO_PROBE):
                logger.debug(msg)
            else:
                logger.error(msg)
            return None

        return hub_port

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for plug, on in plugs.ordered:
            self.set_power(plug=plug, on=on)

    def powercycle(self, power_cycle: TyperPowerCycle) -> None:
        if power_cycle is TyperPowerCycle.INFRA:
            self.set_plugs(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.PICO_INFRA: True}))
            return

        if power_cycle is TyperPowerCycle.INFRBOOT:
            self.set_plugs(plugs=UsbPlugs.default_off())
            self.set_plugs(plugs=UsbPlugs({UsbPlug.BOOT: False}))
            time.sleep(1.0)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.PICO_INFRA: True}))
            time.sleep(0.5)
            self.set_plugs(plugs=UsbPlugs({UsbPlug.BOOT: True}))
            return

        if power_cycle is TyperPowerCycle.DUT:
            self.set_plugs(plugs=UsbPlugs.default_off())
            time.sleep(1.0)
            self.set_plugs(
                plugs=UsbPlugs({UsbPlug.PICO_INFRA: True, UsbPlug.DUT: True})
            )
            return

        if power_cycle is TyperPowerCycle.OFF:
            self.set_plugs(plugs=UsbPlugs.default_off())
            return

        raise NotImplementedError("Internal programming error")

    def __repr__(self) -> str:
        repr = f"UsbTentacle({self.hub4_location.short}"
        if self.pico_infra is not None:
            repr += f"rp2(application_mode={self.pico_infra.application_mode}"
            if self.pico_infra.application_mode:
                repr += f",serial={self.pico_infra.serial}"
                repr += f",serial_port={self.pico_infra.serial_port}"
            repr += ")"
        repr += ")"
        return repr

    @property
    def short(self) -> str:
        """
        Example:
        tentacle 3-1.4: v0.3 e46340474b4c-3f31 /dev/ttyACM2
        tentacle 3-1.3: v0.3 e46340474b4c-1331 /dev/ttyACM0
        tentacle 3-1.2: v0.4 de646cc20b92-5425 /dev/ttyACM1
        """
        if self.pico_infra is None:
            return f"usb hub {self.hub4_location.short}"

        words = [
            "tentacle",
            self.hub4_location.short + ":",
            self.tentacle_version.version,
        ]
        if self.pico_infra.application_mode:
            words.append(str(self.pico_infra.serial))
            words.append(str(self.pico_infra.serial_port))
        else:
            words.append("RP2 in boot (programming) mode.")
        return " ".join(words)

    @property
    def serial(self) -> str | None:
        pico_infra = self.pico_infra
        if pico_infra is None:
            return None
        serial = pico_infra.serial
        if serial is None:
            return None
        return serial

    @property
    def serial_short(self) -> str:
        assert self.serial is not None
        return self.serial[-SERIALNUMBER_SHORT:]

    @property
    def serial_delimited(self) -> str:
        assert self.serial is not None
        return serial_delimited(serial=self.serial)

    @property
    def label_long(self) -> str:
        words = ["Tentacle"]
        if self.pico_infra.serial is not None:
            words.append(self.serial_delimited)
        else:
            words.append("in boot mode")
        words.append(self.tentacle_version.version)
        words.append(f"on USB {self.hub4_location.short}")
        if self.serial_port is not None:
            words.append(self.serial_port)
        return " ".join(words)

    @property
    def serial_port(self) -> str | None:
        pico_infra = self.pico_infra
        if pico_infra is None:
            return None
        serial_port = pico_infra.serial_port
        if serial_port is None:
            return None
        return serial_port


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


def _query_pico_boot_mode() -> list[UsbPico]:
    """
    Query all rp2 in boot mode.
    This will return also rp2 which are not soldered on the tentacles.
    """
    return [
        UsbPico.factory_device(device=device)
        for device in usb.core.find(idVendor=RP2_VENDOR, find_all=True)
        if device.idProduct == RP2_PRODUCT_BOOT_MODE
    ]


def _query_pico_serial() -> list[UsbPico]:
    """
    Query all rp2 in application mode which provide the serial number.
    This will return also rp2 which are not soldered on the tentacles.
    """
    return [
        UsbPico.factory_sysfs(
            port=port, serial=port.serial_number, serial_port=port.device
        )
        for port in list_ports.comports()
        if (RP2_VENDOR == port.vid) and (RP2_PRODUCT_APPLICATION_MODE == port.pid)
    ]


def _combine_hubs_and_rp2(
    hub4_locations: list[Location],
    list_rp2: list[UsbPico],
) -> UsbTentacles:
    """
    Now we combine 'hubs' and 'list_rp2'
    """

    def get_tentacle_version(hub4_location: Location) -> UsbTentacle | None:
        """
        There might be rp2 connected, but we are only intersted in the rp2 infra!
        """

        dict_usb_rp2: dict[int, UsbPico] = {}
        for rp2 in list_rp2:
            if rp2.location.bus != hub4_location.bus:
                return None
            if rp2.location.path[:-1] != hub4_location.path:
                continue
            hub_port = rp2.location.path[-1]
            if hub_port == HubPortNumber.IDX1_3:
                # The DUT might be a rp2, we ignore it
                continue
            dict_usb_rp2[hub_port] = rp2

        if len(dict_usb_rp2) == 0:
            return None

        if TENTACLE_VERSION_V04.portnumber_pico_infra in dict_usb_rp2:
            assert TENTACLE_VERSION_V04.portnumber_pico_probe is not None
            pico_infra = dict_usb_rp2[TENTACLE_VERSION_V04.portnumber_pico_infra]
            return UsbTentacle(
                hub4_location=hub4_location,
                tentacle_version=TENTACLE_VERSION_V04,
                pico_infra=pico_infra,
                pico_probe=pico_infra.as_pico_probe,
            )
        if TENTACLE_VERSION_V03.portnumber_pico_infra in dict_usb_rp2:
            return UsbTentacle(
                hub4_location=hub4_location,
                tentacle_version=TENTACLE_VERSION_V03,
                pico_infra=dict_usb_rp2[TENTACLE_VERSION_V03.portnumber_pico_infra],
            )
        raise ValueError(
            f"The rp2 infra is always connected on port {TENTACLE_VERSION_V03.portnumber_pico_infra} or {TENTACLE_VERSION_V04.portnumber_pico_infra}, but found rp2 on ports {sorted(dict_usb_rp2)}!"
        )

    tentacles = UsbTentacles()
    for hub4_location in hub4_locations:
        usb_tentacle = get_tentacle_version(hub4_location)
        if usb_tentacle is not None:
            tentacles.append(usb_tentacle)
    return tentacles


class UsbTentacles(list[UsbTentacle]):
    TIMEOUT_RP2_BOOT = 2.0

    def set_power(self, plug: UsbPlug, on: bool) -> None:
        for usb_tentacle in self:
            usb_tentacle.set_power(plug=plug, on=on)

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for usb_tentacle in self:
            usb_tentacle.set_plugs(plugs=plugs)

    def select(self, serials: list[str] | None) -> UsbTentacles:
        """
        if serial is None: return all tentacles
        """
        if serials is None:
            return self

        def matches(usb_tentacle: UsbTentacle) -> bool:
            for _serial in serials:
                if usb_tentacle.pico_infra is None:
                    continue
                serial = usb_tentacle.pico_infra.serial
                if serial is None:
                    continue
                # 'serial' may be a substring of 'pico-serial_number'
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
    def query(cls, poweron: bool) -> UsbTentacles:
        """
        Some rp2 may not present a serial number as they are not powered.

        poweron == True: Switch on all unpowered rp2 and wait till the serial numbers appear.
          If a hub does not find a corresponding rp2 serial number: An exception is thrown.
          This is typically used for testing.

        poweron == False: Just query without changing any power states.
          This is typically used for code completion.

        # Manual testing of this class: poweron == True:
        Rationale: A exception should be throw if there is tentacle is 'not in order'.
        If a tentacle rp2 is not powered, the query should power it on and wait till the rp2 appears.
        Throw an exception if after some timeout:
        * A tentacle rp2 is still in boot mode
        * A tentacle rp2 is still not powered


        # Manual testing of this class: poweron == False:
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

        def set_power(hub_port: HubPortNumber | None, on: bool):
            if hub_port is None:
                return
            for hub4_location in hub4_locations:
                hub4_location.set_power(hub_port=hub_port, on=on)

        timeout_poweron_s = 0.0
        if poweron:
            # Release Boot Button
            set_power(TENTACLE_VERSION_V04.portnumber_infraboot, on=True)
            set_power(TENTACLE_VERSION_V04.portnumber_error, on=False)
            # Power OFF pico_infra and pico_probe
            set_power(TENTACLE_VERSION_V04.portnumber_pico_infra, on=False)
            set_power(TENTACLE_VERSION_V04.portnumber_pico_probe, on=False)
            time.sleep(0.2)

            # Power ON pico_infra and pico_probe
            set_power(TENTACLE_VERSION_V04.portnumber_pico_infra, on=True)
            set_power(TENTACLE_VERSION_V04.portnumber_pico_probe, on=True)
            timeout_poweron_s = 1.5  # 0.8: failed, 1.0: ok

        begin_s = time.monotonic()
        #
        # We loop till all rp2 present there serial numbers.
        #
        while True:
            list_rp2 = _query_pico_serial()
            # if not poweron:
            #     # if poweron == False: We also query rp2 in boot mode
            #     list_rp2.extend(_query_pico_boot_mode())
            list_rp2.extend(_query_pico_boot_mode())

            usb_tentacles = _combine_hubs_and_rp2(
                hub4_locations=hub4_locations,
                list_rp2=list_rp2,
            )
            duration_s = time.monotonic() - begin_s
            if duration_s > timeout_poweron_s:
                undetected_tentacles = len(hub4_locations) - len(usb_tentacles)
                if undetected_tentacles > 0:
                    logging.warning(
                        f"WARNING: {len(hub4_locations)} hubs have been detected but only {len(usb_tentacles)} pico_infra! It seems that {undetected_tentacles} pico_infra are not powered/responding. This might fix the problem: op query --poweron"
                    )
                return usb_tentacles

            if len(usb_tentacles) == len(hub4_locations):
                # We found all tentacles
                return usb_tentacles

            time.sleep(0.2)


class TentaclePlugsPower:
    def __init__(self, usb_tentacle: UsbTentacle) -> None:
        assert isinstance(usb_tentacle, UsbTentacle)
        self._usb_tentacle = usb_tentacle

    def set_power_plugs(self, plugs: UsbPlugs) -> None:
        self._usb_tentacle.set_plugs(plugs=plugs)

    def _get_power_plug(self, plug: UsbPlug) -> bool:
        return self._usb_tentacle.get_power(plug=plug)

    def set_power_plug(self, plug: UsbPlug, on: bool) -> None:
        self._usb_tentacle.set_power(plug=plug, on=on)

    def set_default_off(self) -> None:
        self.set_power_plugs(UsbPlugs.default_off())

    @property
    def infra(self) -> bool:
        return self._get_power_plug(UsbPlug.PICO_INFRA)

    @infra.setter
    def infra(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.PICO_INFRA, on)

    @property
    def infraboot(self) -> bool:
        return self._get_power_plug(UsbPlug.BOOT)

    @infraboot.setter
    def infraboot(self, on: bool) -> None:
        self.set_power_plug(UsbPlug.BOOT, on)

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

    usb_tentacles = UsbTentacles.query(poweron=True)

    print(f"{time.monotonic() - time_start_s:0.3f}s")

    for usb_tentacle in usb_tentacles:
        print(repr(usb_tentacle))


if __name__ == "__main__":
    main()
