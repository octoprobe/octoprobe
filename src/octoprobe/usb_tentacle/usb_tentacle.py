"""
Terms:

* pico: A raspberry pi pico soldered on to the tentacle.
* hub4: A hub soldered on to the tentacle.
* plug: A hub has 4 plugs - we do NOT use the term 'port' as this term conflicts with serial port.
* port: A comport in the context of the python 'serial' package.
* port: A comport in the context of the python 'serial' package.
* usb_tentacle: Everything which is related to the USB on a tentacle.
* tentacle: A tentacle where the serial number is known - a tentacle which is in a state to be reay to be used in testing.

This module controls the tentacle via usb.

It allows to query for
* tentacles
* pico on the tentacle and there state:
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
from serial.tools import list_ports, list_ports_linux
from usb.legacy import CLASS_HUB

from ..usb_tentacle.usb_baseclasses import HubPortNumber, Location, UsbPort
from ..usb_tentacle.usb_constants import TyperPowerCycle, UsbPlug, UsbPlugs

logger = logging.getLogger(__file__)

SERIALNUMBER_LONG = 16
"""
Example: e46340474b551722
"""
SERIALNUMBER_DELIMITED = SERIALNUMBER_LONG + 1
"""
Example: e46340474b55-1722
"""
SERIALNUMBER_SHORT = 4
"""
Example: 2731
"""
SERIALNUMBER_DELIMITER = "-"
"""
Example: e46340474b4c-2731
"""
REGEX_SERIAL_DELIMITED = re.compile(r"^\w{12}-\w{4}$")
REGEX_SERIAL = re.compile(r"^\w{16}$")
"""
Example: e46340474b4c2731
"""


def serial_delimited(serial: str) -> str:
    """
    Example
    serial: e46340474b551722
    return: e46340474b55-1722
    """
    assert isinstance(serial, str)
    assert len(serial) == SERIALNUMBER_LONG, (
        f"Expect len {SERIALNUMBER_LONG} but got {len(serial)}: {serial}"
    )
    return (
        serial[:-SERIALNUMBER_SHORT]
        + SERIALNUMBER_DELIMITER
        + serial[-SERIALNUMBER_SHORT:]
    )


def serial_short_from_delimited(serial: str) -> str:
    """
    Example
    serial: e46340474b551722 or e46340474b55-1722
    return: 1722
    """
    assert isinstance(serial, str)
    assert len(serial) in (SERIALNUMBER_LONG, SERIALNUMBER_DELIMITED), (
        f"Expect len {SERIALNUMBER_LONG} or {SERIALNUMBER_LONG} but got {len(serial)}: {serial}"
    )
    return serial[-SERIALNUMBER_SHORT:]


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
PICO_VENDOR = 0x2E8A
PICO_PRODUCT_BOOT_MODE = 0x0003
PICO_PRODUCT_APPLICATION_MODE = 0x0005

# Specification of a hub soldered on to a tentacle
HUB4_VENDOR = 0x0424
HUB4_PRODUCT = 0x2514


@dataclasses.dataclass(frozen=True, repr=True)
class UsbPico:
    location: Location
    serial: str | None
    """
    None: pico is in boot mode and the serial is not known.
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
        path = [
            *self.location.path[:-1],
            HubPortNumber.PORT4_PROBE_LEDERROR.value,
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
    """

    hub4_location: Location
    """
    The usb-location of the hub on the tentacle pcb.
    """

    pico_infra: UsbPico

    def __post_init__(self) -> None:
        pass

    @property
    def pico_probe(self) -> UsbPico:
        return self.pico_infra.as_pico_probe

    def set_power(self, hub_port: HubPortNumber, on: bool) -> bool:
        """
        return True: If the power changed
        return False: If the power was already correct
        """
        assert isinstance(hub_port, HubPortNumber)
        assert isinstance(on, bool)

        # hub_port = self.get_hub_port(plug=plug)
        plug_text = (
            f"usbplug {hub_port.name} {self.hub4_location.short} port {hub_port}"
        )

        if on == self.get_power_hub_port(hub_port=hub_port):
            logger.debug(f"{plug_text} is already {on}")
            return False

        if hub_port is None:
            # TODO: Handle correctly
            return False

        self.hub4_location.set_power(hub_port=hub_port, on=on)

        logger.debug(f"{plug_text} set({on})")
        return True

    # TODO(hans): obsolete
    def get_power(self, plug: UsbPlug) -> bool:
        assert isinstance(plug, UsbPlug)

        hub_port = self.get_hub_port(plug=plug)
        if hub_port is None:
            # TODO: Handle correctly
            return False
        on = self.hub4_location.get_power(hub_port=hub_port)
        return on

    def get_power_hub_port(self, hub_port: HubPortNumber) -> bool:
        assert isinstance(hub_port, HubPortNumber)
        on = self.hub4_location.get_power(hub_port=hub_port)
        return on

    def tentacle_version_get_hub_port_to_be_refactored(
        self, plug: UsbPlug
    ) -> HubPortNumber | None:
        """
        UsbPlug is the generic naming.
        This code converts it into the tentacle version specific number.
        """

        if plug == UsbPlug.PICO_INFRA:
            return HubPortNumber.PORT1_INFRA
        if plug == UsbPlug.PICO_PROBE_OBSOLETE:
            return HubPortNumber.PORT4_PROBE_LEDERROR
        if plug == UsbPlug.DUT:
            return HubPortNumber.PORT3_DUT
        if plug == UsbPlug.ERROR:
            return HubPortNumber.PORT4_PROBE_LEDERROR
        if plug == UsbPlug.BOOT:
            1 / 0
            return self.portnumber_infraboot
        return None

    def get_hub_port(self, plug: UsbPlug) -> HubPortNumber | None:
        hub_port = self.tentacle_version_get_hub_port_to_be_refactored(plug=plug)
        if hub_port is None:
            # TODO: Handle this error.
            msg = f"'{plug}' does not match any usb port"
            if plug in (UsbPlug.ERROR, UsbPlug.PICO_PROBE_OBSOLETE):
                logger.debug(msg)
            else:
                logger.error(msg)
            return None

        return hub_port

    def __repr__(self) -> str:
        repr = f"UsbTentacle({self.hub4_location.short}"
        if self.pico_infra is not None:
            repr += f"pico(application_mode={self.pico_infra.application_mode}"
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
            words.append(" in boot (programming) mode.")
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

    @property
    def usb_port_infra(self) -> UsbPort:
        return UsbPort(
            usb_location=f"{self.hub4_location.short}.{HubPortNumber.PORT1_INFRA}"
        )

    @property
    def usb_port_probe(self) -> UsbPort:
        return UsbPort(
            usb_location=f"{self.hub4_location.short}.{HubPortNumber.PORT4_PROBE_LEDERROR}"
        )

    @property
    def usb_port_dut(self) -> UsbPort:
        return UsbPort(
            usb_location=f"{self.hub4_location.short}.{HubPortNumber.PORT3_DUT}"
        )


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
    Query all pico in boot mode.
    This will return also pico which are not soldered on the tentacles.
    """
    return [
        UsbPico.factory_device(device=device)
        for device in usb.core.find(idVendor=PICO_VENDOR, find_all=True)
        if device.idProduct == PICO_PRODUCT_BOOT_MODE
    ]


def _query_pico_serial() -> list[UsbPico]:
    """
    Query all pico in application mode which provide the serial number.
    This will return also pico which are not soldered on the tentacles.
    """
    return [
        UsbPico.factory_sysfs(
            port=port, serial=port.serial_number, serial_port=port.device
        )
        for port in list_ports.comports()
        if (PICO_VENDOR == port.vid) and (PICO_PRODUCT_APPLICATION_MODE == port.pid)
    ]


def _combine_hubs_and_pico(
    hub4_locations: list[Location],
    list_pico: list[UsbPico],
) -> tuple[UsbTentacles, list[Location]]:
    """
    Now we combine 'hubs' and 'list_pico'
    """

    def get_valid_tentacle(hub4_location: Location) -> UsbTentacle | None:
        """
        There might be pico connected, but we are only intersted in the pico infra!
        """

        dict_usb_pico: dict[int, UsbPico] = {}
        for pico in list_pico:
            if pico.location.bus != hub4_location.bus:
                return None
            if pico.location.path[:-1] != hub4_location.path:
                continue
            hub_port = pico.location.path[-1]
            if hub_port == HubPortNumber.PORT2_INFRABOOT:
                # This might be rp_infra on a Tentacle v0.4
                logger.warning(
                    f"Usb location '{pico.location.short}' with serial '{pico.serial_delimited}': This seems to be a Tentacle v0.4 which is not supported anymore!"
                )
                continue
            if hub_port == HubPortNumber.PORT3_DUT:
                # The DUT might be a pico, we ignore it
                continue
            if hub_port == HubPortNumber.PORT4_PROBE_LEDERROR:
                # The PROBE might be a pico, we ignore it
                continue
            dict_usb_pico[hub_port] = pico

        if len(dict_usb_pico) == 0:
            return None

        return UsbTentacle(
            hub4_location=hub4_location,
            pico_infra=dict_usb_pico[HubPortNumber.PORT1_INFRA],
        )

    tentacles = UsbTentacles()
    unresolved_hub4_locations: list[Location] = []
    for hub4_location in hub4_locations:
        usb_tentacle = get_valid_tentacle(hub4_location)
        if usb_tentacle is None:
            unresolved_hub4_locations.append(hub4_location)
        else:
            tentacles.append(usb_tentacle)
    return tentacles, unresolved_hub4_locations


class UsbTentacles(list[UsbTentacle]):
    TIMEOUT_PICO_BOOT = 2.0

    def set_power(self, hub_port: HubPortNumber, on: bool) -> None:
        for usb_tentacle in self:
            usb_tentacle.set_power(hub_port=hub_port, on=on)

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
        Some pico may not present a serial number as they are not powered.

        poweron == True: Switch on all unpowered pico and wait till the serial numbers appear.
          If a hub does not find a corresponding pico serial number: An exception is thrown.
          This is typically used for testing.

        poweron == False: Just query without changing any power states.
          This is typically used for code completion.

        # Manual testing of this class: poweron == True:
        Rationale: A exception should be throw if there is tentacle is 'not in order'.
        If a tentacle pico is not powered, the query should power it on and wait till the pico appears.
        Throw an exception if after some timeout:
        * A tentacle pico is still in boot mode
        * A tentacle pico is still not powered


        # Manual testing of this class: poweron == False:
        Rationale: The query should return fast without changing the power state.
        All tentacles should be visible:
        * Tentacle with serial
        * Tentacle with pico in boot mode
        * Tentacle with pico powered off
        """

        #
        # Identify all tentalces by getting a list of all hubs.
        # Power on all pico infra to be able to read the serial numbers.
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
            set_power(HubPortNumber.PORT2_INFRABOOT, on=True)
            # set_power(TENTACLE_VERSION_V04.portnumber_error, on=False)
            # Power OFF pico_infra and pico_probe
            set_power(HubPortNumber.PORT1_INFRA, on=False)
            set_power(HubPortNumber.PORT4_PROBE_LEDERROR, on=False)
            time.sleep(0.2)

            # Power ON pico_infra and pico_probe
            set_power(HubPortNumber.PORT1_INFRA, on=True)
            set_power(HubPortNumber.PORT4_PROBE_LEDERROR, on=True)
            timeout_poweron_s = 1.5  # 0.8: failed, 1.0: ok

        begin_s = time.monotonic()
        #
        # We loop till all pico present there serial numbers.
        #
        while True:
            list_pico = _query_pico_serial()
            # if not poweron:
            #     # if poweron == False: We also query pico in boot mode
            #     list_pico.extend(_query_pico_boot_mode())
            list_pico.extend(_query_pico_boot_mode())

            usb_tentacles, unresolved_hub4_locations = _combine_hubs_and_pico(
                hub4_locations=hub4_locations,
                list_pico=list_pico,
            )
            duration_s = time.monotonic() - begin_s
            if duration_s > timeout_poweron_s:
                if len(unresolved_hub4_locations) > 0:
                    hubs_text = ", ".join([x.short for x in unresolved_hub4_locations])
                    logging.info(
                        f"These hubs could not be accociated with a tentacle: {hubs_text}! "
                        "If there are tentacles with unpowered picos, this will fix the problem: op query --poweron"
                    )
                return usb_tentacles

            if len(usb_tentacles) == len(hub4_locations):
                # We found all tentacles
                return usb_tentacles

            time.sleep(0.2)


def main() -> None:
    time_start_s = time.monotonic()

    usb_tentacles = UsbTentacles.query(poweron=True)

    print(f"{time.monotonic() - time_start_s:0.3f}s")

    for usb_tentacle in usb_tentacles:
        print(repr(usb_tentacle))


if __name__ == "__main__":
    main()
