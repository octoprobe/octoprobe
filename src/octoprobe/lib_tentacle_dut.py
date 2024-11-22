from __future__ import annotations

import logging
import typing

from octoprobe.util_constants import TAG_BOARDS, TAG_PROGRAMMER

from .lib_mpremote import MpRemote
from .util_baseclasses import TentacleSpec
from .util_dut_mcu import TAG_MCU, dut_mcu_factory
from .util_dut_programmers import FirmwareSpecBase, dut_programmer_factory
from .util_pyudev import UdevPoller

logger = logging.getLogger(__file__)

if typing.TYPE_CHECKING:
    from .lib_tentacle import Tentacle


class TentacleDut:
    """
    The DUT side of a tentacle PCB.
    Only valid if the DUT contains a MCU.

    * Allows to program the MCU
    * Allows to run micropython code on the MCU.
    """

    def __init__(self, label: str, tentacle_spec: TentacleSpec) -> None:
        assert isinstance(label, str)
        assert isinstance(tentacle_spec, TentacleSpec)

        # Validate consistency
        for tag in TAG_MCU, TAG_BOARDS, TAG_PROGRAMMER:
            tentacle_spec.get_tag_mandatory(tag)

        self.label = label
        self._tentacle_spec = tentacle_spec
        self._mp_remote: MpRemote | None = None
        self.dut_mcu = dut_mcu_factory(tags=tentacle_spec.tags)
        self.dut_programmer = dut_programmer_factory(tags=tentacle_spec.tags)

    @property
    def tentacle_spec(self) -> TentacleSpec:
        return self._tentacle_spec

    @property
    def mp_remote(self) -> MpRemote:
        assert self._mp_remote is not None
        return self._mp_remote

    def get_tty(self) -> str:
        """
        Returns the tty (/dev/ttyACM1).
        Frees the tty by calling: self.mp_remote_close()
        """
        assert self._mp_remote is not None
        tty = self.mp_remote.state.transport.device_name
        self.mp_remote_close()
        return tty

    def mp_remote_close(self) -> str | None:
        """
        Return the serial port which was closed.
        """
        if self._mp_remote is None:
            return None
        serial_port = self._mp_remote.close()
        self._mp_remote = None
        return serial_port

    def boot_and_init_mp_remote_dut(self, tentacle: Tentacle, udev: UdevPoller) -> None:
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert self._mp_remote is None
        tty = self.dut_mcu.application_mode_power_up(tentacle=tentacle, udev=udev)
        self._mp_remote = MpRemote(tty=tty)

    def dut_installed_firmware_version(self) -> str:
        """
        Example:
        >>> import sys
        >>> sys.version
        '3.4.0; MicroPython v1.20.0 on 2023-04-26'
        """
        assert self.mp_remote is not None
        version = self.mp_remote.exec_raw("import sys; print(sys.version)")
        return version.strip()

    def is_dut_required_firmware_already_installed(
        self,
        firmware_spec: FirmwareSpecBase,
        exception_text: str | None = None,
    ) -> bool:
        assert isinstance(firmware_spec, FirmwareSpecBase)

        installed_version = self.dut_installed_firmware_version()
        logger.info(f"{self.label}: Micropython Version installed: {installed_version}")
        if firmware_spec.micropython_version_text is None:
            # There is not expected version give.
            return True
        versions_equal = firmware_spec.micropython_version_text == installed_version
        if exception_text is not None:
            if not versions_equal:
                raise ValueError(
                    f"{exception_text}: Version installed: {installed_version}\n  but expected: '{firmware_spec.micropython_version_text}'!"
                )
        return versions_equal

    def flash_dut(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(udev, UdevPoller)
        assert isinstance(firmware_spec, FirmwareSpecBase)

        try:
            self.boot_and_init_mp_remote_dut(tentacle=tentacle, udev=udev)
            if firmware_spec.micropython_version_text is None:
                logger.info(
                    f"No micropython_version_text provided for '{firmware_spec.board_variant.name_normalized}'! We could not verify if the firmware was correctly flashed!"
                )
            else:
                if self.is_dut_required_firmware_already_installed(
                    firmware_spec=firmware_spec
                ):
                    logger.info(f"{self.label}: firmware is already installed")
                    return

        except TimeoutError as e:
            logger.debug(f"DUT seems not to have firmware installed: {e!r}")

        tty = self.dut_programmer.flash(
            tentacle=tentacle,
            udev=udev,
            firmware_spec=firmware_spec,
        )
        self._mp_remote = MpRemote(tty=tty)

        self.is_dut_required_firmware_already_installed(
            firmware_spec=firmware_spec,
            exception_text=f"DUT: After installing {firmware_spec.filename}",
        )

    def inspection_exit(self) -> typing.NoReturn:
        import os

        print(
            f"Exiting without cleanup. You may now take over the MCU on port="
            + self.mp_remote.state.transport.serial.port
        )
        os._exit(42)
