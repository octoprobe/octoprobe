from __future__ import annotations

import logging
import os
import pathlib
import typing

from mpremote.transport_serial import TransportError  # type: ignore

from .lib_mpremote import MpRemote
from .util_baseclasses import OctoprobeTestException, VersionMismatchException
from .util_constants import TAG_PROGRAMMER
from .util_dut_programmers import dut_programmer_factory
from .util_firmware_spec import FirmwareSpecBase
from .util_pyudev import UdevPoller, UdevTimoutException

logger = logging.getLogger(__file__)

if typing.TYPE_CHECKING:
    from .lib_tentacle import TentacleBase

VERSION_IMPLEMENTATION_SEPARATOR = ";"


class TentacleDut:
    """
    The DUT side of a tentacle PCB.
    Only valid if the DUT contains a MCU.

    * Allows to program the MCU
    * Allows to run micropython code on the MCU.
    """

    def __init__(self, label: str, tentacle: TentacleBase) -> None:
        # pylint: disable=import-outside-toplevel
        from .lib_tentacle import TentacleBase
        from .util_dut_mcu import TAG_MCU, dut_mcu_factory

        assert isinstance(label, str)
        assert isinstance(tentacle, TentacleBase)

        self._tentacle = tentacle

        self.label = label
        self._mp_remote: MpRemote | None = None
        self.dut_mcu = dut_mcu_factory(tags=tentacle.tentacle_spec_base.tags)
        self.dut_programmer = dut_programmer_factory(
            tags=tentacle.tentacle_spec_base.tags
        )
        self.dut_flashed_variant_normalized: str = "not flashed yet"

        # Validate consistency
        # for tag in TAG_MCU, TAG_BOARDS, TAG_PROGRAMMER:
        for tag in TAG_MCU, TAG_PROGRAMMER:
            tentacle.tentacle_spec_base.get_tag_mandatory(tag)

    @property
    def mp_remote(self) -> MpRemote:
        assert self._mp_remote is not None
        return self._mp_remote

    @property
    def mp_remote_is_initialized(self) -> bool:
        return self._mp_remote is not None

    def get_tty(self) -> str:
        """
        Returns the tty (/dev/ttyACM1).
        Frees the tty by calling: self.mp_remote_close()
        """
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

    def boot_and_init_mp_remote_dut(
        self, tentacle: TentacleBase, udev: UdevPoller
    ) -> None:
        """
        Eventually, self._mp_remote will be initialized
        """
        # pylint: disable=import-outside-toplevel
        from .lib_tentacle import TentacleBase

        assert isinstance(tentacle, TentacleBase)
        assert self._mp_remote is None
        tty = self.dut_mcu.application_mode_power_up(tentacle=tentacle, udev=udev)
        self._mp_remote = MpRemote(tty=tty)

    def dut_installed_firmware_full_version_text(self) -> str:
        """
        Example:
        >>> import sys
        >>> sys.version
        '3.4.0; MicroPython v1.20.0 on 2023-04-26'
        >>> sys.implementation[2]
        'Raspberry Pi Pico2 with RP2350-RISCV'

        Will return both strings with a ',' inbetween.
        """
        assert self.mp_remote is not None
        cmd = f"""
import sys
l = []
try:
    l.append(sys.implementation._build)
except AttributeError:
    pass
l.append(sys.version)
l.append(sys.implementation[2])
print('{VERSION_IMPLEMENTATION_SEPARATOR}'.join(l))
        """
        version_implementation = self.mp_remote.exec_raw(cmd=cmd, timeout=2)
        return version_implementation.strip()

    def is_dut_required_firmware_already_installed(
        self,
        firmware_spec: FirmwareSpecBase,
        exception_text: str | None = None,
    ) -> bool:
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert isinstance(exception_text, str | None)

        if firmware_spec.requires_flashing:
            return False

        installed_full_version = self.dut_installed_firmware_full_version_text()
        logger.info(f"{self.label}: Version installed: {installed_full_version}")
        versions_equal = (
            firmware_spec.micropython_full_version_text == installed_full_version
        )
        if exception_text is not None:
            if not versions_equal:
                raise VersionMismatchException(
                    msg=exception_text,
                    version_expected=firmware_spec.micropython_full_version_text,
                    version_installed=installed_full_version,
                )
        return versions_equal

    def flash_dut(
        self,
        tentacle: TentacleBase,
        udev: UdevPoller,
        directory_logs: pathlib.Path,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """
        Will flash the firmware if it is not already flashed.

        Eventually self._mp_remote will be initialized
        """
        # pylint: disable=import-outside-toplevel
        from .lib_tentacle import TentacleBase

        assert isinstance(tentacle, TentacleBase)
        assert isinstance(udev, UdevPoller)
        assert isinstance(directory_logs, pathlib.Path)
        assert isinstance(firmware_spec, FirmwareSpecBase)

        try:
            self.boot_and_init_mp_remote_dut(tentacle=tentacle, udev=udev)
            if not firmware_spec.do_flash:
                return

            if tentacle.tentacle_state.flash_force:
                tentacle.tentacle_state.flash_force = False
                logger.info(
                    f"{self.label}: '--flash-force' was choosen so we require flashing!"
                )
            else:
                if firmware_spec.requires_flashing:
                    logger.info(
                        f"{self.label}: Firmware spec requires flashing '{firmware_spec.board_variant.name_normalized}'!"
                    )
                else:
                    if self.is_dut_required_firmware_already_installed(
                        firmware_spec=firmware_spec
                    ):
                        logger.info(f"{self.label}: Firmware is already installed")
                        return

        except (UdevTimoutException, TransportError) as e:
            logger.warning(f"{self.label}: Seems not to have firmware installed: {e!r}")

        with tentacle.active_led_on:  # type: ignore[attr-defined]
            logger.info(
                f"{self.label}: About to flash '{firmware_spec.board_variant.name_normalized}'!"
            )
            try:
                self.dut_programmer.flash(
                    tentacle=tentacle,
                    udev=udev,
                    directory_logs=directory_logs,
                    firmware_spec=firmware_spec,
                )
                tentacle.tentacle_state.last_firmware_flashed = firmware_spec
            except UdevTimoutException as e:
                msg = f"Failed to flash the firmware. Is USB connected? {e!r}"
                logger.warning(f"{self.label}: {msg}")
                raise OctoprobeTestException(msg) from e

            tty = self.dut_mcu.application_mode_power_up(
                tentacle=tentacle,
                udev=udev,
            )
            self._mp_remote = MpRemote(tty=tty)
            self.is_dut_required_firmware_already_installed(
                firmware_spec=firmware_spec,
                exception_text=f"{self.label}: After installing {firmware_spec.filename}",
            )
            self.dut_flashed_variant_normalized = (
                firmware_spec.board_variant.name_normalized
            )

    def inspection_exit(self) -> typing.NoReturn:
        msg = "Exiting without cleanup. "
        if (self._mp_remote is None) or (self._mp_remote.state.transport is None):
            msg += "mp_remote is not initialized and the serial port not known"
        else:
            msg += (
                "You may now take over the MCU on port="
                + self.mp_remote.state.transport.serial.port
            )

        logger.warning(msg)
        os._exit(42)
