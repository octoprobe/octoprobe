from __future__ import annotations

import abc
import typing

from octoprobe.util_baseclasses import PropertyString
from octoprobe.util_constants import TAG_MCU
from octoprobe.util_mcu import UdevApplicationModeEvent, udev_filter_application_mode

if typing.TYPE_CHECKING:
    from octoprobe.lib_tentacle import Tentacle
    from octoprobe.util_pyudev import UdevPoller


class DutMcu(abc.ABC):
    @abc.abstractmethod
    def application_mode_power_up(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """


class DutMicropythonSTM32(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=tentacle.tentacle_spec.mcu_usb_id.application,
            )
            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after DfuUtil programming",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonRP2(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert tentacle.dut is not None
        assert tentacle.__class__.__qualname__ == "Tentacle"

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect RP2 to become visible",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonEsp8266(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert tentacle.dut is not None
        assert tentacle.__class__.__qualname__ == "Tentacle"

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect ESP8266 to become visible",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonEsp32C3(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert tentacle.dut is not None
        assert tentacle.__class__.__qualname__ == "Tentacle"

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect ESP32C3 to become visible",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


def dut_mcu_factory(tags: str) -> DutMcu:
    """
    Example 'tags': mcu=stm32,programmer=picotool,xy=5
    """
    mcu = PropertyString(tags).get_tag_mandatory(TAG_MCU)
    if mcu == "stm32":
        return DutMicropythonSTM32()
    if mcu == "rp2":
        return DutMicropythonRP2()
    if mcu == "esp8266":
        return DutMicropythonEsp8266()
    if mcu == "esp32":
        return DutMicropythonEsp32C3()
    raise ValueError(f"Unknown '{mcu}' in '{tags}'!")
