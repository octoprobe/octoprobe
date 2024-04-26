from __future__ import annotations

import logging
import pathlib
import time

from octoprobe.util_dut_programmers import FirmwareSpec

from . import util_power, util_usb_serial
from .lib_mpremote import MpRemote
from .lib_tentacle_infra_rp2 import InfraRP2
from .util_pyudev import UdevPoller
from .util_rp2 import (
    UDEV_FILTER_RP2_APPLICATION_MODE,
    UDEV_FILTER_RP2_BOOT_MODE,
    rp2_flash_micropython,
)

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent

logger = logging.getLogger(__file__)


class VersionMismatchException(Exception):
    pass


class TentacleInfra:
    """
    The Infrastructure side of a tentacle PCB.

    * Allows to program the RP2
    * Allows to run micropython code on the RP2.
    """

    RELAY_COUNT = 5
    LIST_ALL_RELAYS = list(range(1, RELAY_COUNT + 1))

    @staticmethod
    def is_valid_relay_index(i: int) -> bool:
        return 1 <= i <= TentacleInfra.RELAY_COUNT

    @staticmethod
    def get_firmware_spec() -> FirmwareSpec:
        json_filename = DIRECTORY_OF_THIS_FILE / "util_tentacle_infra_firmware.json"
        return FirmwareSpec.factory2(filename=json_filename)

    def __init__(self, label: str) -> None:
        assert isinstance(label, str)
        self.label = label
        self.hub: util_usb_serial.QueryResultTentacle | None = None
        self._mp_remote: MpRemote | None = None
        self._power: util_power.TentaclePlugsPower | None = None
        self.mcu_infra: InfraRP2 = InfraRP2(self)

    def assign_connected_hub(
        self,
        query_result_tentacle: util_usb_serial.QueryResultTentacle,
    ) -> None:
        assert isinstance(query_result_tentacle, util_usb_serial.QueryResultTentacle)
        self.hub = query_result_tentacle

    def mp_remote_close(self) -> None:
        if self._mp_remote is None:
            return
        self._mp_remote.close()
        self._mp_remote = None

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
        unique_id = self.mcu_infra.get_unique_id()
        assert self.hub.rp2_serial_number == unique_id

        self.verify_micropython_version(self.get_firmware_spec())

    def setup_infra(self, udev: UdevPoller) -> None:
        assert self.hub is not None
        assert self.hub.rp2_serial_port is not None
        self._mp_remote = MpRemote(tty=self.hub.rp2_serial_port)
        self.rp2_test_mp_remote()

    def verify_micropython_version(self, firmware_spec: FirmwareSpec) -> None:
        assert isinstance(firmware_spec, FirmwareSpec)

        installed_version = self.mcu_infra.get_micropython_version()
        versions_equal = firmware_spec.micropython_version_text == installed_version
        if not versions_equal:
            raise VersionMismatchException(
                f"Tentacle '{self.label}': Version installed '{installed_version}', but expected '{firmware_spec.micropython_version_text}'!"
            )

    def flash(
        self,
        udev: UdevPoller,
        filename_uf2: pathlib.Path,
    ) -> None:
        """
        Flashed the RP2.

        Attach self._mp_remote to the serial port of this RP2
        """

        # Power off everything and release boot button
        self.power.set_default_off()
        time.sleep(0.3)
        # Press Boot Button
        self.power.infraboot = False
        time.sleep(0.1)

        with udev.guard as guard:
            # Power of RP2
            self.power.infra = True

            event = guard.expect_event(
                UDEV_FILTER_RP2_BOOT_MODE,
                text_where=self.label,
                text_expect="Expect RP2 in programming mode to become visible on udev after power on",
                timeout_s=2.0,
            )

            # Release Boot Button
            self.power.infraboot = True

        with udev.guard as guard:
            # This will flash the RP2
            rp2_flash_micropython(event, filename_uf2)

            # The RP2 will reboot in application mode
            # and we wait for this event here
            event = udev.expect_event(
                UDEV_FILTER_RP2_APPLICATION_MODE,
                text_where=self.label,
                text_expect="Expect RP2 in application mode to become visible on udev after programming ",
                timeout_s=3.0,
            )

        self._mp_remote = MpRemote(tty=event.tty)
