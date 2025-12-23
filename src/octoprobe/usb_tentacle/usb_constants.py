"""
This module defines the different USB functions like pico_infra or dut.
The different version are hidden so for one function, for exaple pico_infra, different
USB hub ports may be assigned depending of the version of the tentacle.
"""

from __future__ import annotations

import abc
import enum


class HwVersion(enum.StrEnum):
    V03 = "v0.3"
    V05 = "v0.5"
    V06 = "v0.6"

    @staticmethod
    def is_V05or_newer(version: str) -> bool:
        return HwVersion.factory(version) >= HwVersion.V05

    @staticmethod
    def factory(version: str) -> HwVersion:
        assert isinstance(version, str)
        if isinstance(version, HwVersion):
            return version

        try:
            return HwVersion(version)
        except ValueError as e:
            raise ValueError(
                f"Unknown HwVersion '{version}'! Valid values are {', '.join([v.value for v in HwVersion])}."
            ) from e


class TyperPowerCycle(str, enum.Enum):
    """
    Used as command line argument (Typer)
    """

    INFRA = "infra"
    """
    infra=off, sleep(1), infra=on (PICO_INFRA will be left in application mode)
    """
    INFRABOOT = "infraboot"
    """
    infra=off, infraboot=programming_mode, sleep(1), infra=on (PICO_INFRA will be left in programming mode)
    """
    PROBE = "probe"  # Only v0.6
    """
    probe=off, sleep(1), probe=on (PICO_PROBE will be left in application mode)
    """
    PROBEBOOT = "probeboot"
    """
    probe=off, probeboot=programming_mode, sleep(1), infra=on (PICO_PROBE will be left in programming mode)
    """
    DUT = "dut"
    """
    dut=off, sleep(1), dut=on
    """
    OFF = "off"
    """
    All off, even PICO_INFA
    """


class Switch(str, enum.Enum):
    """
    Items which may be switched:
    * Relay: False: open, True: closed
    * LED:   False: off, True: on
    * Power: False: unpowered, True: powered
    * Boot:  False: LED on - boot in programming mode, True: LED off - boot in application mode
    """

    PICO_INFRA = "infra"
    """True: rp_infra is powered"""
    PICO_INFRA_BOOT = "infraboot"
    """False: rp_infra boot button pressed"""
    PICO_PROBE_RUN = "proberun"  # >= v0.6
    """True: rp_probe run (reset released)"""
    PICO_PROBE_BOOT = "probeboot"  # >= v0.6
    """False: rp_probe boot button pressed"""

    DUT = "dut"
    """True: DUT is powerered"""
    LED_ERROR = "led_error"
    """True: LED_ERROR is on bright"""
    LED_ACTIVE = "led_active"
    """True: LED_ACTIVE is on bright"""

    RELAY1 = "relay1"
    """True: RELAYx is closed"""
    RELAY2 = "relay2"
    RELAY3 = "relay3"
    RELAY4 = "relay4"
    RELAY5 = "relay5"
    RELAY6 = "relay6"
    RELAY7 = "relay7"

    @property
    def text(self) -> str:
        return self.name.lower()

    @property
    def is_hub_plug(self) -> bool:
        """
        Return true if control is (on all hardware versions of the tentacles) via USB plugs
        """
        return self in (Switch.PICO_INFRA, Switch.PICO_INFRA_BOOT)

    @staticmethod
    def RELAYS() -> list[Switch]:
        return [
            Switch.RELAY1,
            Switch.RELAY2,
            Switch.RELAY3,
            Switch.RELAY4,
            Switch.RELAY5,
            Switch.RELAY6,
            Switch.RELAY7,
        ]

    @property
    def is_relay(self) -> bool:
        return Switch.RELAY1 <= self <= Switch.RELAY7

    @property
    def relay_number(self) -> int:
        """
        Returns 5 for RELAY5
        """
        assert Switch.RELAY1 <= self <= Switch.RELAY7
        return int(self.name[5])


def switches_typer_names() -> list[str]:
    return [switch.name.lower() for switch in Switch]


class SwitchABC(abc.ABC):
    @property
    @abc.abstractmethod
    def switch(self) -> Switch: ...

    @abc.abstractmethod
    def set(self, on: bool) -> bool:
        """
        return True if the value changed.
        return True if the value did not change
        """

    @abc.abstractmethod
    def get(self) -> bool:
        """
        return True: LED on, Power on, Relays closed
        return False: LED off, Power off, Relays open
        """
