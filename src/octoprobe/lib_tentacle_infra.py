from __future__ import annotations

import contextlib
import logging
import pathlib
import time
import typing

from .lib_mpremote import MpRemote
from .usb_tentacle.usb_baseclasses import HubPortNumber
from .usb_tentacle.usb_constants import (
    HwVersion,
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
        self.power = TentaclePlugsPower(tentacle_infra=self)
        self._mp_remote: MpRemote | None = None
        self._power: TentaclePlugsPower | None = None
        self.mcu_infra: InfraPico = InfraPico(self)

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
        self.usb_tentacle.set_power(hub_port=HubPortNumber.PORT1_INFRA, on=False)
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
        self.handle_usb_plug(typerusbplug2usbplug(typer_usb_plug), on=on)

    def handle_usb_plug(self, usb_plug: UsbPlug, on: bool) -> None:
        assert isinstance(usb_plug, UsbPlug)
        if usb_plug.is_hub_plug:
            hub_port = {
                UsbPlug.PICO_INFRA: HubPortNumber.PORT1_INFRA,
                UsbPlug.PICO_INFRA_BOOT: HubPortNumber.PORT2_INFRABOOT,
            }[usb_plug]
            self.usb_tentacle.set_power(hub_port, on=on)
            return

        if self.usb_tentacle.serial is None:
            logger.warning(
                f"{self.usb_tentacle.hub4_location.short}: May not switch '{usb_plug}' as rp_infra is not visible."
            )
            return

        self.connect_mpremote_if_needed()
        if usb_plug.is_relay:
            kwargs = {"relays_close" if on else "relays_open": [usb_plug.relay_number]}
            self.mcu_infra.relays(**kwargs)
            return
        if usb_plug is UsbPlug.DUT:
            if self.mcu_infra.hw_version == HwVersion.V03:
                self.usb_tentacle.set_power(HubPortNumber.PORT3_DUT, on=on)
            else:
                self.mcu_infra.power_dut(on=on)
            return
        if usb_plug is UsbPlug.PICO_PROBE_RUN:
            self.mcu_infra.power_proberun(on=on)
            return
        if usb_plug is UsbPlug.PICO_PROBE_BOOT:
            self.mcu_infra.power_probeboot(on=on)
            return
        if usb_plug is UsbPlug.PICO_PROBE_RUN:
            self.mcu_infra.power_proberun(on=on)
            return
        if usb_plug is UsbPlug.LED_ACTIVE:
            self.mcu_infra.active_led(on=on)
            return
        if usb_plug is UsbPlug.LED_ERROR:
            if self.mcu_infra.hw_version == HwVersion.V03:
                self.usb_tentacle.set_power(HubPortNumber.PORT4_PROBE_LEDERROR, on=on)
            else:
                self.mcu_infra.error_led(on=on)
            return
        raise ValueError(f"{usb_plug=} not handled")

    def set_plugs(self, plugs: UsbPlugs) -> None:
        for plug, on in plugs.ordered:
            self.handle_usb_plug(usb_plug=plug, on=on)

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


class TentaclePlugsPower:
    def __init__(self, tentacle_infra: TentacleInfra) -> None:
        assert isinstance(tentacle_infra, TentacleInfra)
        self._tentacle_infra = tentacle_infra

    def set_power_plugs(self, plugs: UsbPlugs) -> None:
        self._tentacle_infra.set_plugs(plugs=plugs)

    def _get_power_plug(self, plug: UsbPlug) -> bool:
        return self._tentacle_infra.get_power(plug=plug)

    def set_power_plug(self, plug: UsbPlug, on: bool) -> None:
        self._tentacle_infra.usb_tentacle.set_power(HubPortNumber.PORT3_DUT, on=on)

    def set_default_off(self) -> None:
        self.set_power_plugs(UsbPlugs.default_off())

    def set_default_infra_on(self) -> None:
        self.set_power_plugs(UsbPlugs.default_infra_on())

    @property
    def infra(self) -> bool:
        return self._tentacle_infra.usb_tentacle.get_power_hub_port(
            HubPortNumber.PORT1_INFRA
        )

    @infra.setter
    def infra(self, on: bool) -> None:
        self._tentacle_infra.usb_tentacle.set_power(HubPortNumber.PORT1_INFRA, on=on)

    @property
    def infraboot(self) -> bool:
        return self._get_power_plug(UsbPlug.BOOT)

    @infraboot.setter
    def infraboot(self, on: bool) -> None:
        self._tentacle_infra.usb_tentacle.set_power(
            HubPortNumber.PORT2_INFRABOOT,
            on=on,
        )

    @property
    def dut(self) -> bool:
        """
        USB-Power for the DUT-MCU
        """
        return self._get_power_plug(UsbPlug.DUT)

    @dut.setter
    def dut(self, on: bool) -> None:
        # Tentacle v0.3
        self.set_power_plug(UsbPlug.DUT, on)
        # Tentacle >= v0.5
        self._tentacle_infra.set_plugs(plugs=UsbPlugs({UsbPlug.DUT: on}))

    @property
    def error(self) -> bool:
        return self._get_power_plug(UsbPlug.ERROR)

    @error.setter
    def error(self, on: bool) -> None:
        self._tentacle_infra.handle_usb_plug(UsbPlug.LED_ERROR, on)
