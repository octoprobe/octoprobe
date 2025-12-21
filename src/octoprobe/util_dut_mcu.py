from __future__ import annotations

import abc

from .lib_tentacle import TentacleBase
from .util_baseclasses import PropertyString
from .util_constants import TAG_MCU
from .util_mcu import UdevApplicationModeEvent, udev_filter_application_mode
from .util_pyudev import UdevPoller


class DutMcu(abc.ABC):
    @abc.abstractmethod
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """


class DutMicropythonSTM32(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is not None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=tentacle.tentacle_spec_base.mcu_usb_id.application,
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


class DutMicropythonPico(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is not None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect RP2 to become visible",
                timeout_s=5.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonEsp8266(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is None
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


class DutMicropythonEsp32(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of pybard
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            mcu_usb_id = tentacle.tentacle_spec_base.mcu_usb_id
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=None if mcu_usb_id is None else mcu_usb_id.application,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect ESP32/ESP32_C3/ESP32_S3 to become visible",
                timeout_s=6.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonNrf(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of nrf
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec_base.mcu_usb_id is not None
            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=tentacle.tentacle_spec_base.mcu_usb_id.application,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect NRF to become visible",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonMimxrt(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of nrf
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None
        assert tentacle.tentacle_spec_base.mcu_usb_id is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=tentacle.tentacle_spec_base.mcu_usb_id.application,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect Mimxrt to become visible",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        tty = event.tty
        assert isinstance(tty, str)
        return tty


class DutMicropythonSamd(DutMcu):
    def application_mode_power_up(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
    ) -> str:
        """
        Power up and wait for udev-event.
        Return tty of nrf
        """
        assert isinstance(tentacle, TentacleBase)
        assert tentacle.dut is not None
        assert tentacle.tentacle_spec_base.mcu_usb_id is not None

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            udev_filter = udev_filter_application_mode(
                usb_location=tentacle.infra.usb_location_dut,
                usb_id=tentacle.tentacle_spec_base.mcu_usb_id.application,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect Samd to become visible",
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
        return DutMicropythonPico()
    if mcu == "esp8266":
        return DutMicropythonEsp8266()
    if mcu == "esp32":
        return DutMicropythonEsp32()
    if mcu == "nrf":
        return DutMicropythonNrf()
    if mcu == "mimxrt":
        return DutMicropythonMimxrt()
    if mcu == "samd":
        return DutMicropythonSamd()
    raise ValueError(f"Unknown '{mcu}' in '{tags}'!")
