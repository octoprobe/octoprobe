from __future__ import annotations

import logging
import pathlib
import time

from . import util_power, util_usb_serial
from .lib_mpremote import MpRemote
from .util_baseclasses import VersionMismatchException
from .util_firmware_spec import FirmwareDownloadSpec, FirmwareSpecBase
from .util_mcu import UdevApplicationModeEvent, udev_filter_application_mode
from .util_pyudev import UdevPoller

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent

logger = logging.getLogger(__file__)


class TentacleInfra:
    """
    The Infrastructure side of a tentacle PCB.

    * Allows to program the RP2
    * Allows to run micropython code on the RP2.
    """

    RELAY_COUNT = 7
    LIST_ALL_RELAYS = list(range(1, RELAY_COUNT + 1))

    @staticmethod
    def is_valid_relay_index(i: int) -> bool:
        return 1 <= i <= TentacleInfra.RELAY_COUNT

    @staticmethod
    def get_firmware_spec() -> FirmwareDownloadSpec:
        json_filename = DIRECTORY_OF_THIS_FILE / "util_tentacle_infra_firmware.json"
        return FirmwareDownloadSpec.factory2(filename=json_filename)

    def __init__(self, label: str, hub: util_usb_serial.QueryResultTentacle) -> None:
        assert isinstance(label, str)

        # pylint: disable=import-outside-toplevel
        from .lib_tentacle_infra_rp2 import InfraRP2

        self.label = label
        self.hub = hub
        self._mp_remote: MpRemote | None = None
        self._power: util_power.TentaclePlugsPower | None = None
        self.mcu_infra: InfraRP2 = InfraRP2(self)

    @property
    def usb_location_infra(self) -> str:
        return f"{self.hub.hub_location.short}.{util_power.UsbPlug.INFRA.number}"

    @property
    def usb_location_dut(self) -> str:
        return f"{self.hub.hub_location.short}.{util_power.UsbPlug.DUT.number}"

    def mp_remote_close(self) -> str | None:
        """
        Return the serial port which was closed.
        """
        if self._mp_remote is None:
            return None
        serial_port = self._mp_remote.close()
        self._mp_remote = None
        return serial_port

    @property
    def mp_remote(self) -> MpRemote:
        assert self._mp_remote is not None
        return self._mp_remote

    @property
    def power(self) -> util_power.TentaclePlugsPower:
        assert self.hub is not None
        if self._power is None:
            self._power = util_power.TentaclePlugsPower(
                hub_location=self.hub.hub_location
            )
        return self._power

    def power_dut_off_and_wait(self) -> None:
        """
        Use this instead of 'self.power.dut = False'
        """
        if self.power.dut:
            self.power.dut = False
            time.sleep(0.5)

    def rp2_test_mp_remote(self) -> None:
        assert self.hub is not None
        unique_id = self.mcu_infra.get_unique_id()
        assert self.hub.rp2_serial_number == unique_id

        self.verify_micropython_version(self.get_firmware_spec())

    def connect_mpremote_if_needed(self) -> None:
        if self._mp_remote is not None:
            # We are already connected
            return

        assert self.hub is not None
        assert self.hub.rp2_serial_port is not None
        self._mp_remote = MpRemote(tty=self.hub.rp2_serial_port)

    def setup_infra(self, udev: UdevPoller) -> None:
        self.connect_mpremote_if_needed()
        self.rp2_test_mp_remote()

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
        Flashed the RP2.

        Attach self._mp_remote to the serial port of this RP2
        """
        # pylint: disable=import-outside-toplevel
        from .util_mcu_rp2 import (
            RPI_PICO_USB_ID,
            picotool_flash_micropython,
            rp2_udev_filter_boot_mode,
        )

        # Power off everything and release boot button
        # print("Power off everything and release boot button")
        self.power.set_default_off()
        time.sleep(0.3)
        # Press Boot Button
        # print("Press Boot Button")
        self.power.infraboot = False
        time.sleep(0.1)

        with udev.guard as guard:
            # Power on RP2
            # print("Power on RP2")
            self.power.infra = True

            udev_filter = rp2_udev_filter_boot_mode(
                RPI_PICO_USB_ID.boot,
                usb_location=usb_location,
            )
            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=self.label,
                text_expect="Expect RP2 in programming mode to become visible on udev after power on",
                timeout_s=2.0,
            )

            # Release Boot Button
            # print("Release Boot Button")
            self.power.infraboot = True

        with udev.guard as guard:
            # This will flash the RP2
            # print("Flash")
            picotool_flash_micropython(
                event=event,
                directory_logs=directory_test,
                filename_firmware=filename_firmware,
            )

            # The RP2 will reboot in application mode
            # and we wait for this event here
            udev_filter = udev_filter_application_mode(
                usb_id=RPI_PICO_USB_ID.application,
                usb_location=usb_location,
            )
            event = udev.expect_event(
                udev_filter=udev_filter,
                text_where=self.label,
                text_expect="Expect RP2 in application mode to become visible on udev after programming ",
                timeout_s=3.0,
            )

        assert isinstance(event, UdevApplicationModeEvent)
        self._mp_remote = MpRemote(tty=event.tty)
