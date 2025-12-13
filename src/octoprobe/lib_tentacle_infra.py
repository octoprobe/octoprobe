from __future__ import annotations

import contextlib
import logging
import pathlib
import time
import typing

from .lib_mpremote import MpRemote
from .usb_tentacle.usb_constants import (
    SwitchABC,
    TyperPowerCycle,
    TyperUsbPlug,
    UsbPlug,
    UsbPlugs,
    typerusbplug2usbplug,
)
from .usb_tentacle.usb_tentacle import UsbTentacle
from .util_baseclasses import VersionMismatchException
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

        self.label = label
        self.usb_tentacle = usb_tentacle
        self._mp_remote: MpRemote | None = None
        self.mcu_infra: InfraPico = InfraPico(self)
        self.switches = TentacleInfraSwitches(tentacle_infra=self)
        self.power = self.switches
        self.power.dut = False

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

    def power_dut_off_and_wait(self) -> None:
        """
        Use this instead of 'self.power.dut = False'
        """
        if self.power.dut:
            logger.debug("self.power.dut = False")
            self.power.dut = False
            time.sleep(0.5)

    def pico_test_mp_remote(self) -> None:
        assert self.usb_tentacle is not None
        unique_id = self.mcu_infra.unique_id
        assert self.usb_tentacle.serial == unique_id

        self.verify_micropython_version(self.get_firmware_spec())

    def connect_mpremote_if_needed(self) -> None:
        if self._mp_remote is not None:
            # We are already connected
            return

        serial_port = self.usb_tentacle.serial_port
        assert serial_port is not None
        self._mp_remote = MpRemote(tty=serial_port)

    def setup_infra(self, udev: UdevPoller) -> None:
        self.connect_mpremote_if_needed()
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
        self.power.infraboot = False
        time.sleep(0.1)

        with udev.guard as guard:
            # Power on Pico
            # print("Power on Pico")
            self.power.infra = True

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
            self.power.infraboot = True

        with udev.guard as guard:
            picotool_flash_micropython(
                event=event,
                directory_logs=directory_test,
                filename_firmware=filename_firmware,
            )

            # The Pico will reboot in application mode
            # and we wait for this event here
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
        assert event.tty is not None
        self._mp_remote = MpRemote(tty=event.tty)

    @contextlib.contextmanager
    def borrow_tty(self) -> typing.Generator[str]:
        assert self._mp_remote is not None
        with self._mp_remote.borrow_tty() as tty:
            yield tty

    def handle_typer_usb_plug(self, typer_usb_plug: TyperUsbPlug, on: bool) -> None:
        assert isinstance(typer_usb_plug, TyperUsbPlug)
        self.set_usb_plug(typerusbplug2usbplug(typer_usb_plug), on=on)

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for plug, on in plugs.ordered:
            self.set_usb_plug(usb_plug=plug, on=on)


class TentacleInfraSwitch(SwitchABC):
    def __init__(
        self,
        usb_plug: UsbPlug,
        tentacle_infra: TentacleInfra,
    ) -> None:
        assert isinstance(usb_plug, UsbPlug)
        assert isinstance(tentacle_infra, TentacleInfra)

        self._usb_plug = usb_plug
        self._tentacle_infra = tentacle_infra

    @property
    def usb_plug(self) -> UsbPlug:
        return self._usb_plug

    def set(self, on: bool) -> bool:
        return self._get_set_usb_plug(on=on, getter=False)

    def get(self) -> bool:
        return self._get_set_usb_plug(getter=True)

    def _get_set_usb_plug(self, getter: bool, on: bool) -> bool:
        # TODO(hans): Move method
        """
        Getter (if get is True) and setter (if get is False).
        If Getter: return True if on.
        If Setter: return False
        """
        # if self.usb_plug.is_hub_plug:
        #     hub_port = {
        #         UsbPlug.PICO_INFRA: HubPortNumber.PORT1_INFRA,
        #         UsbPlug.PICO_INFRA_BOOT: HubPortNumber.PORT2_INFRABOOT,
        #     }[self.usb_plug]
        #     if getter:
        #         return self.usb_tentacle.get_power(hub_port=hub_port)
        #     else:
        #         self.usb_tentacle.set_power(hub_port=hub_port, on=on)
        #     return

        if self._tentacle_infra.usb_tentacle.serial is None:
            logger.warning(
                f"{self._tentacle_infra.usb_tentacle.hub4_location.short}: May not switch '{self.usb_plug}' as rp_infra is not visible."
            )
            return False

        self._tentacle_infra.connect_mpremote_if_needed()
        changed = self._tentacle_infra.mcu_infra._set_pin(
            f"pin_{self.usb_plug.name}", on=on
        )
        return changed
        # if self.usb_plug.is_relay:
        #     if getter:
        #         pass
        #         self.mcu_infra.relays
        #         1 / 0
        #     else:
        #         kwargs = {
        #             "relays_close" if on else "relays_open": [
        #                 self.usb_plug.relay_number
        #             ]
        #         }
        #         self.mcu_infra.relays(**kwargs)
        #     return
        # if self.usb_plug is UsbPlug.DUT:
        #     if self.mcu_infra.hw_version == HwVersion.V03:
        #         if getter:
        #             return self.usb_tentacle.get_power(hub_port=HubPortNumber.PORT3_DUT)
        #         else:
        #             self.usb_tentacle.set_power(hub_port=HubPortNumber.PORT3_DUT, on=on)
        #             return
        #     if getter:
        #         return self.mcu_infra.get_power_dut()
        #     self.mcu_infra.power_dut(on=on)
        #     return
        # if self.usb_plug is UsbPlug.PICO_PROBE_RUN:
        #     if getter:
        #         return self.mcu_infra.get_power_proberun()
        #     self.mcu_infra.power_proberun(on=on)
        #     return
        # if self.usb_plug is UsbPlug.PICO_PROBE_BOOT:
        #     if getter:
        #         return self.mcu_infra.get_power_probeboot()
        #     self.mcu_infra.power_probeboot(on=on)
        #     return
        # if self.usb_plug is UsbPlug.LED_ACTIVE:
        #     if getter:
        #         return self.mcu_infra.get_active_led()
        #     self.mcu_infra.active_led(on=on)
        #     return
        # if self.usb_plug is UsbPlug.LED_ERROR:
        #     if self.mcu_infra.hw_version == HwVersion.V03:
        #         if getter:
        #             return self.usb_tentacle.get_power(
        #                 HubPortNumber.PORT4_PROBE_LEDERROR
        #             )

        #         self.usb_tentacle.set_power(HubPortNumber.PORT4_PROBE_LEDERROR, on=on)
        #         return
        #     if getter:
        #         return self.mcu_infra.get_error_led()
        #     self.mcu_infra.error_led(on=on)
        #     return
        raise ValueError(f"{self. usb_plug=} not handled")


class TentacleInfraSwitchDUT(TentacleInfraSwitch):
    def set(self, on: bool) -> bool:
        # Tentacle v0.3
        self._tentacle_infra.usb_tentacle.switches[self.usb_plug].set(on=on)
        # Tentacle >= v0.5
        return super().set(on=on)

    def get(self) -> bool:
        return self._tentacle_infra.usb_tentacle.switches[self.usb_plug].get()


class TentacleInfraSwitchRelays(TentacleInfraSwitch):
    def set(self, on: bool) -> bool:
        relays_close = []
        relays_open = []

        if on:
            relays_close = [self.usb_plug.relay_number]
        else:
            relays_open = [self.usb_plug.relay_number]

        return self.relays(
            tentacle_infra=self._tentacle_infra,
            relays_close=relays_close,
            relays_open=relays_open,
        )

    def get(self) -> bool:
        self._tentacle_infra.mcu_infra.load_base_code()
        closed = self._tentacle_infra.mp_remote.exec_bool(
            cmd=f"print(get_relays({self.usb_plug.relay_number}))"
        )
        return closed

        return self._tentacle_infra.usb_tentacle.switches[self.usb_plug].get()

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

        tentacle_infra.mcu_infra.load_base_code()
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
        return self._tentacle_infra.usb_tentacle.switches[self.usb_plug].set(on=on)

    def get(self) -> bool:
        return self._tentacle_infra.usb_tentacle.switches[self.usb_plug].get()


class TentacleInfraSwitchProperty(property):
    """
    A custom property descriptor that hides the switch on/off logic.
    """

    def __init__(self, usb_plug: UsbPlug):
        self._usb_plug = usb_plug
        super().__init__()

    def __get__(self, tentacle_infra_switches, owner) -> None:
        assert isinstance(tentacle_infra_switches, TentacleInfraSwitches)
        return tentacle_infra_switches[self._usb_plug].get()

    def __set__(self, tentacle_infra_switches, on: bool) -> None:
        assert isinstance(tentacle_infra_switches, TentacleInfraSwitches)
        tentacle_infra_switches[self._usb_plug].set(on=on)


class TentacleInfraSwitches(dict[UsbPlug, TentacleInfraSwitch]):
    infra = TentacleInfraSwitchProperty(usb_plug=UsbPlug.PICO_INFRA)
    infraboot = TentacleInfraSwitchProperty(usb_plug=UsbPlug.PICO_INFRA_BOOT)
    proberun = TentacleInfraSwitchProperty(usb_plug=UsbPlug.PICO_PROBE_RUN)
    probeboot = TentacleInfraSwitchProperty(usb_plug=UsbPlug.PICO_PROBE_BOOT)
    dut = TentacleInfraSwitchProperty(usb_plug=UsbPlug.DUT)
    led_error = TentacleInfraSwitchProperty(usb_plug=UsbPlug.LED_ERROR)
    led_active = TentacleInfraSwitchProperty(usb_plug=UsbPlug.LED_ACTIVE)
    relay1 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY1)
    relay2 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY2)
    relay3 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY3)
    relay4 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY4)
    relay5 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY5)
    relay6 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY6)
    relay7 = TentacleInfraSwitchProperty(usb_plug=UsbPlug.RELAY7)

    def __init__(self, tentacle_infra: TentacleInfra) -> None:
        self._tentacle_infra = tentacle_infra

        def add(tentacle_infra_switch: TentacleInfraSwitch) -> None:
            self[tentacle_infra_switch.usb_plug] = tentacle_infra_switch

        for usb_plug_generic in (
            UsbPlug.LED_ACTIVE,
            UsbPlug.PICO_PROBE_RUN,
            UsbPlug.PICO_PROBE_BOOT,
        ):
            add(
                TentacleInfraSwitch(
                    usb_plug=usb_plug_generic,
                    tentacle_infra=tentacle_infra,
                )
            )

        for usb_plug_relay in UsbPlug.RELAYS():
            add(
                TentacleInfraSwitchRelays(
                    usb_plug=usb_plug_relay,
                    tentacle_infra=tentacle_infra,
                )
            )

        add(
            TentacleInfraSwitchDUT(
                usb_plug=UsbPlug.DUT,
                tentacle_infra=tentacle_infra,
            )
        )
        add(
            TentacleInfraSwitchLED_ERROR(
                usb_plug=UsbPlug.LED_ERROR,
                tentacle_infra=tentacle_infra,
            )
        )

        for usb_plug_delegate in (UsbPlug.PICO_INFRA, UsbPlug.PICO_INFRA_BOOT):
            add(
                TentacleInfraSwitchDelegate(
                    usb_plug=usb_plug_delegate,
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

    def set_plugs(self, plugs: UsbPlugs) -> None:
        assert isinstance(plugs, UsbPlugs)
        for plug, on in plugs.items():
            self[plug].set(on=on)

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
