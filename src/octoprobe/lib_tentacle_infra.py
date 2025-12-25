from __future__ import annotations

import contextlib
import logging
import pathlib
import time
import typing

from .lib_mpremote import MpRemote
from .usb_tentacle.usb_constants import (
    Switch,
    SwitchABC,
    TyperPowerCycle,
)
from .usb_tentacle.usb_tentacle import UsbTentacle
from .util_baseclasses import OctoprobeAppExitException, VersionMismatchException
from .util_firmware_spec import FirmwareDownloadSpec, FirmwareSpecBase
from .util_mcu import UdevApplicationModeEvent, udev_filter_application_mode
from .util_pyudev import UdevPoller

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent

logger = logging.getLogger(__file__)


class TentacleInfra:
    """
    The Infrastructure side of a tentacle PCB.

    * Allows to program the Pico
    * Allows to run micropython code on the Pico.
    """

    @staticmethod
    def get_firmware_spec() -> FirmwareDownloadSpec:
        json_filename = DIRECTORY_OF_THIS_FILE / "util_tentacle_infra_firmware.json"
        return FirmwareDownloadSpec.factory2(filename=json_filename)

    def __init__(self, label: str, usb_tentacle: UsbTentacle) -> None:
        assert isinstance(label, str)
        assert isinstance(usb_tentacle, UsbTentacle)

        # pylint: disable=import-outside-toplevel
        from .lib_tentacle_infra_pico import InfraPico

        self._mpremote_connected_counter = -1
        self.label = label
        self.usb_tentacle = usb_tentacle
        self._mp_remote: MpRemote | None = None
        self.mcu_infra: InfraPico = InfraPico(self)
        self.switches = TentacleInfraSwitches(tentacle_infra=self)

    def is_valid_relay_index(self, i: int) -> bool:
        return i in self.list_all_relays

    @staticmethod
    def factory_usb_tentacle(usb_tentacle: UsbTentacle) -> TentacleInfra:
        """
        Create a temporary TentacleInfra
        """
        assert isinstance(usb_tentacle, UsbTentacle)
        label = "tentacle"
        if usb_tentacle.serial is not None:
            label = f"tentacle_{usb_tentacle.serial_delimited}"
        return TentacleInfra(label=label, usb_tentacle=usb_tentacle)

    @property
    def list_all_relays(self) -> list[int]:
        return [1, 2, 3, 4, 5, 6, 7]

    @property
    def usb_location_infra(self) -> str:
        return self.usb_tentacle.usb_port_infra.usb_location

    @property
    def usb_location_probe(self) -> str:
        return self.usb_tentacle.usb_port_probe.usb_location

    @property
    def usb_location_dut(self) -> str:
        return self.usb_tentacle.usb_port_dut.usb_location

    def mp_remote_close(self) -> str | None:
        """
        Return the serial port which was closed.
        """
        if self._mp_remote is None:
            return None
        self._mp_remote.close()
        self._mp_remote = None
        self.mcu_infra.base_code_lost()
        return self.usb_tentacle.serial_port

    @property
    def mp_remote(self) -> MpRemote:
        assert self._mp_remote is not None
        return self._mp_remote

    @property
    def msg_PICO_INFRA_unpowered(self) -> str:
        return f"{self.label}: Could not connect to PICO_INFRA. Might be PICO_INFRA is unpowerered or in programming mode. Recover with: op query --poweron"

    def power_dut_off_and_wait(self) -> None:
        """
        Use this instead of 'self.power.dut = False'
        """
        changed = self.switches[Switch.DUT].set(on=False)
        if changed:
            logger.debug("self.power.dut = False")
            time.sleep(0.5)

    def pico_test_mp_remote(self) -> None:
        assert self.usb_tentacle is not None
        unique_id = self.mcu_infra.unique_id
        assert self.usb_tentacle.serial == unique_id

        self.verify_micropython_version(self.get_firmware_spec())

    def load_base_code_if_needed(self) -> None:
        self.connect_mpremote_if_needed()
        self.mcu_infra.load_base_code()

    def connect_mpremote_if_needed(self) -> None:
        changed_counter = self.usb_tentacle.switches[Switch.PICO_INFRA].changed_counter

        if self._mp_remote is not None:
            # We are already connected
            if changed_counter == self._mpremote_connected_counter:
                # We have not been powercycled, so the connection should be still ok
                return

        # We have been powercycled, so reconnect!
        self._mpremote_connected_counter = changed_counter

        serial_port = self.usb_tentacle.serial_port
        if serial_port is None:
            msg = self.msg_PICO_INFRA_unpowered
            logger.error(msg)
            raise OctoprobeAppExitException(msg)

        self._mp_remote = MpRemote(tty=serial_port)

    def setup_infra(self, udev: UdevPoller) -> None:
        self.load_base_code_if_needed()
        try:
            self.pico_test_mp_remote()
        except VersionMismatchException as e:
            logger.info(f"Flashing MicroPython due to VersionMismatchException: {e}")
            self.flash(
                udev=udev,
                filename_firmware=self.get_firmware_spec().filename,
                directory_test=pathlib.Path("/tmp"),
                usb_location=self.usb_location_infra,
            )
            self.pico_test_mp_remote()

    def verify_micropython_version(self, firmware_spec: FirmwareSpecBase) -> None:
        assert isinstance(firmware_spec, FirmwareSpecBase)

        installed_version = self.mcu_infra.get_micropython_version()
        versions_equal = (
            firmware_spec.micropython_full_version_text == installed_version
        )
        if not versions_equal:
            raise VersionMismatchException(
                msg=f"Tentacle '{self.label}'",
                version_installed=installed_version,
                version_expected=firmware_spec.micropython_full_version_text,
            )

    def wait_power_up_PICO_INFRA(
        self,
        udev: UdevPoller,
        usb_location: str,
    ) -> UdevApplicationModeEvent:
        # pylint: disable=import-outside-toplevel
        from .util_mcu_pico import RPI_PICO_USB_ID

        udev_filter = udev_filter_application_mode(
            usb_id=RPI_PICO_USB_ID.application,
            usb_location=usb_location,
        )
        event = udev.expect_event(
            udev_filter=udev_filter,
            text_where=self.label,
            text_expect="Expect Pico in application mode to become visible on udev after programming ",
            timeout_s=3.0,
        )
        assert isinstance(event, UdevApplicationModeEvent)
        return event

    def flash(
        self,
        udev: UdevPoller,
        filename_firmware: pathlib.Path,
        usb_location: str,
        directory_test: pathlib.Path,
    ) -> None:
        """
        Flashed the Pico.

        Attach self._mp_remote to the serial port of this Pico
        """
        # pylint: disable=import-outside-toplevel
        from .util_mcu_pico import (
            RPI_PICO_USB_ID,
            pico_udev_filter_boot_mode,
            picotool_flash_micropython,
        )

        # Power off PICO_INFRA and press Boot Button
        self.usb_tentacle.switches.infra = False
        self.switches.infraboot = False
        time.sleep(0.1)

        with udev.guard as guard:
            # Power on Pico
            # print("Power on Pico")
            self.switches.infra = True

            udev_filter = pico_udev_filter_boot_mode(
                RPI_PICO_USB_ID.boot,
                usb_location=usb_location,
            )
            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=self.label,
                text_expect="Expect Pico in programming mode to become visible on udev after power on",
                timeout_s=2.0,
            )

            # Release Boot Button
            self.switches.infraboot = True

        with udev.guard as guard:
            picotool_flash_micropython(
                event=event,
                directory_logs=directory_test,
                filename_firmware=filename_firmware,
            )

            # The Pico will reboot in application mode
            # and we wait for this event here
            event = self.wait_power_up_PICO_INFRA(udev=udev, usb_location=usb_location)

        assert isinstance(event, UdevApplicationModeEvent)
        assert event.tty is not None
        self._mp_remote = MpRemote(tty=event.tty)

    @contextlib.contextmanager
    def borrow_tty(self) -> typing.Generator[str]:
        assert self._mp_remote is not None
        with self._mp_remote.borrow_tty() as tty:
            yield tty

    def power_usb_switch(self, switch: Switch, on: bool) -> None:
        assert isinstance(switch, Switch)
        self.switches[switch].set(on=on)


class TentacleInfraSwitch(SwitchABC):
    def __init__(
        self,
        switch: Switch,
        tentacle_infra: TentacleInfra,
    ) -> None:
        assert isinstance(switch, Switch)
        assert isinstance(tentacle_infra, TentacleInfra)

        self._switch = switch
        self._tentacle_infra = tentacle_infra

    @property
    def switch(self) -> Switch:
        return self._switch

    @property
    def micropython_pin(self) -> str:
        return f"pin_{self.switch.name}"

    def set(self, on: bool) -> bool:
        assert isinstance(on, bool)
        # self._tentacle_infra.pico_infra_load_base_code()
        # if self._tentacle_infra.usb_tentacle.serial is None:
        #     logger.warning(
        #         f"{self._tentacle_infra.usb_tentacle.hub4_location.short}: May not switch '{self.switch}' as rp_infra is not visible."
        #     )
        #     return False

        # self._tentacle_infra.load_base_code_if_needed()

        self._tentacle_infra.mcu_infra.assert_base_code_loaded()

        changed = self._tentacle_infra.mp_remote.exec_bool(
            cmd=f"print(set_switch({self.micropython_pin}, on={int(on)}))"
        )
        return changed

    def get(self) -> bool:
        self._tentacle_infra.mcu_infra.assert_base_code_loaded()

        # if self._tentacle_infra.usb_tentacle.serial is None:
        #     logger.warning(
        #         f"{self._tentacle_infra.usb_tentacle.hub4_location.short}: May not switch '{self.switch}' as rp_infra is not visible."
        #     )
        #     return False

        # self._tentacle_infra.load_base_code_if_needed()

        changed = self._tentacle_infra.mp_remote.exec_bool(
            cmd=f"print({self.micropython_pin}.value())"
        )
        return changed


class TentacleInfraSwitchDUT(TentacleInfraSwitch):
    def set(self, on: bool) -> bool:
        # Tentacle v0.3
        self._tentacle_infra.usb_tentacle.switches[self.switch].set(on=on)
        # Tentacle >= v0.5
        return super().set(on=on)

    def get(self) -> bool:
        return self._tentacle_infra.usb_tentacle.switches[self.switch].get()


class TentacleInfraSwitchRelays(TentacleInfraSwitch):
    def set(self, on: bool) -> bool:
        self._tentacle_infra.mcu_infra.assert_base_code_loaded()

        relays_close = []
        relays_open = []

        if on:
            relays_close = [self.switch.relay_number]
        else:
            relays_open = [self.switch.relay_number]

        return self.relays(
            tentacle_infra=self._tentacle_infra,
            relays_close=relays_close,
            relays_open=relays_open,
        )

    def get(self) -> bool:
        self._tentacle_infra.mcu_infra.assert_base_code_loaded()
        closed = self._tentacle_infra.mp_remote.exec_bool(
            cmd=f"print(get_relays({self.switch.relay_number}))"
        )
        return closed

        return self._tentacle_infra.usb_tentacle.switches[self.switch].get()

    @staticmethod
    def relays(
        tentacle_infra: TentacleInfra,
        relays_close: list[int] | None = None,
        relays_open: list[int] | None = None,
    ) -> bool:
        """
        If the same relays appears in 'relays_open' and 'relays_close': The relay will be CLOSED.
        If a relays is missing in the list, it will not be changed.
        """
        assert isinstance(tentacle_infra, TentacleInfra)
        assert isinstance(relays_close, list | None)
        assert isinstance(relays_open, list | None)

        if relays_close is None:
            relays_close = []
        if relays_open is None:
            relays_open = []

        assert isinstance(relays_close, list)
        assert isinstance(relays_open, list)

        for i in relays_close + relays_open:
            assert tentacle_infra.is_valid_relay_index(i)

        dict_relays = {}
        for i in relays_open:
            dict_relays[i] = False
        for i in relays_close:
            dict_relays[i] = True
        list_relays = list(dict_relays.items())

        tentacle_infra.mcu_infra.assert_base_code_loaded()
        changed = tentacle_infra.mp_remote.exec_bool(
            cmd=f"print(set_relays({list_relays}))"
        )
        return changed


class TentacleInfraSwitchLED_ERROR(TentacleInfraSwitchDUT):
    pass


class TentacleInfraSwitchDelegate(TentacleInfraSwitch):
    """
    Delegate the switch functionality to the 'usb_tentacle'.
    """

    def set(self, on: bool) -> bool:
        return self._tentacle_infra.usb_tentacle.switches[self.switch].set(on=on)

    def get(self) -> bool:
        return self._tentacle_infra.usb_tentacle.switches[self.switch].get()


class TentacleInfraSwitchProperty(property):
    """
    A custom property descriptor that hides the switch on/off logic.
    """

    def __init__(self, switch: Switch):
        self._switch = switch
        super().__init__()

    def __get__(
        self,
        tentacle_infra_switches: typing.Any,
        owner: type | None = None,
    ) -> typing.Any:
        assert isinstance(tentacle_infra_switches, TentacleInfraSwitches)
        tentacle_infra_switches[self._switch].get()

    def __set__(self, tentacle_infra_switches: typing.Any, on: bool) -> None:
        assert isinstance(tentacle_infra_switches, TentacleInfraSwitches)
        tentacle_infra_switches[self._switch].set(on=on)


class TentacleInfraSwitches(dict[Switch, TentacleInfraSwitch]):
    infra = TentacleInfraSwitchProperty(switch=Switch.PICO_INFRA)
    infraboot = TentacleInfraSwitchProperty(switch=Switch.PICO_INFRA_BOOT)
    proberun = TentacleInfraSwitchProperty(switch=Switch.PICO_PROBE_RUN)
    probeboot = TentacleInfraSwitchProperty(switch=Switch.PICO_PROBE_BOOT)
    dut = TentacleInfraSwitchProperty(switch=Switch.DUT)
    led_error = TentacleInfraSwitchProperty(switch=Switch.LED_ERROR)
    led_active = TentacleInfraSwitchProperty(switch=Switch.LED_ACTIVE)
    relay1 = TentacleInfraSwitchProperty(switch=Switch.RELAY1)
    relay2 = TentacleInfraSwitchProperty(switch=Switch.RELAY2)
    relay3 = TentacleInfraSwitchProperty(switch=Switch.RELAY3)
    relay4 = TentacleInfraSwitchProperty(switch=Switch.RELAY4)
    relay5 = TentacleInfraSwitchProperty(switch=Switch.RELAY5)
    relay6 = TentacleInfraSwitchProperty(switch=Switch.RELAY6)
    relay7 = TentacleInfraSwitchProperty(switch=Switch.RELAY7)

    def __init__(self, tentacle_infra: TentacleInfra) -> None:
        self._tentacle_infra = tentacle_infra

        def add(tentacle_infra_switch: TentacleInfraSwitch) -> None:
            self[tentacle_infra_switch.switch] = tentacle_infra_switch

        for switch in (
            Switch.LED_ACTIVE,
            Switch.PICO_PROBE_RUN,
            Switch.PICO_PROBE_BOOT,
        ):
            add(
                TentacleInfraSwitch(
                    switch=switch,
                    tentacle_infra=tentacle_infra,
                )
            )

        for switch_relay in Switch.RELAYS():
            add(
                TentacleInfraSwitchRelays(
                    switch=switch_relay,
                    tentacle_infra=tentacle_infra,
                )
            )

        add(
            TentacleInfraSwitchDUT(
                switch=Switch.DUT,
                tentacle_infra=tentacle_infra,
            )
        )
        add(
            TentacleInfraSwitchLED_ERROR(
                switch=Switch.LED_ERROR,
                tentacle_infra=tentacle_infra,
            )
        )

        for switch_delegate in (Switch.PICO_INFRA, Switch.PICO_INFRA_BOOT):
            add(
                TentacleInfraSwitchDelegate(
                    switch=switch_delegate,
                    tentacle_infra=tentacle_infra,
                )
            )

    def relays(
        self,
        relays_close: list[int] | None = None,
        relays_open: list[int] | None = None,
    ) -> bool:
        return TentacleInfraSwitchRelays.relays(
            self._tentacle_infra,
            relays_close=relays_close,
            relays_open=relays_open,
        )

    def default_off(self) -> None:
        # First PICO_INFRA controlled switches
        # self.probeboot = True
        # self.dut = False
        # self.led_error = False
        # Now USB controlled switches
        self._tentacle_infra.usb_tentacle.switches.default_off()

    def default_off_infra_on(self) -> None:
        # First USB controlled switches
        self._tentacle_infra.usb_tentacle.switches.default_off_infra_on()
        # Second PICO_INFRA controlled switches
        self.probeboot = True
        self.proberun = False
        self.dut = False
        self.led_error = False

    def powercycle(self, power_cycle: TyperPowerCycle) -> None:
        switches = self._tentacle_infra.switches

        if power_cycle is TyperPowerCycle.INFRA:
            self.default_off()
            time.sleep(1.0)
            self.infra = True
            return

        if power_cycle is TyperPowerCycle.INFRABOOT:
            self.infra = False
            self.infraboot = False
            time.sleep(1.0)
            self.infra = True
            time.sleep(0.5)
            self.infraboot = True
            return

        if power_cycle is TyperPowerCycle.PROBE:
            switches.probeboot = True
            switches.proberun = False
            time.sleep(1.0)
            switches.proberun = True
            return

        if power_cycle is TyperPowerCycle.PROBEBOOT:
            switches.probeboot = False
            switches.proberun = False
            time.sleep(1.0)
            switches.proberun = True
            return

        if power_cycle is TyperPowerCycle.DUT:
            switches.dut = False
            time.sleep(1.0)
            switches.dut = True
            return

        if power_cycle is TyperPowerCycle.OFF:
            self.default_off()
            return

        raise NotImplementedError("Internal programming error")
