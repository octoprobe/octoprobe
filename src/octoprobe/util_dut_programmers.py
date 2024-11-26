from __future__ import annotations

import abc
import dataclasses
import json
import logging
import pathlib
import shutil
import typing
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlretrieve

from usbhubctl.util_subprocess import subprocess_run

from octoprobe.util_mcu_pyboard import pyboard_udev_filter_boot_mode

from .util_baseclasses import PropertyString
from .util_constants import (
    DIRECTORY_OCTOPROBE_CACHE_FIRMWARE,
    TAG_BOARDS,
    TAG_PROGRAMMER,
)
from .util_mcu_esp import esptool_flash_micropython
from .util_mcu_rp2 import (
    Rp2UdevBootModeEvent,
    picotool_flash_micropython,
    rp2_udev_filter_boot_mode,
)
from .util_micropython_boards import BoardVariant, board_variants

if typing.TYPE_CHECKING:
    from octoprobe.lib_tentacle import Tentacle

    from .util_pyudev import UdevPoller


logger = logging.getLogger(__file__)

IDX_RELAYS_DUT_BOOT = 1


@dataclasses.dataclass(frozen=True, repr=True)
class FirmwareSpecBase(abc.ABC):
    board_variant: BoardVariant
    """
    Examples:
    PYBV11
    PYBV11-THREAD
    RPI_PICO
    """

    micropython_version_text: str | None
    """
    Example:
    >>> import sys
    >>> sys.version
    '3.4.0; MicroPython v1.20.0 on 2023-04-26'

    None: If not known
    """

    def __post_init__(self) -> None:
        assert isinstance(self.board_variant, BoardVariant)
        assert isinstance(self.micropython_version_text, str | None)

    @property
    @abc.abstractmethod
    def filename(self) -> pathlib.Path: ...

    def match_board(self, tentacle: Tentacle) -> bool:
        """
        Return True: If tentacles board matches the firmware_spec board.
        """
        # assert tentacle.tentacle_spec.tentacle_type.is_mcu
        boards = tentacle.get_tag_mandatory(TAG_BOARDS)
        for board_variant in board_variants(boards=boards):
            assert isinstance(board_variant, BoardVariant)
            if board_variant == self.board_variant:
                # We found a board variant which we may test
                return True
        return False


@dataclasses.dataclass(frozen=True, repr=True)
class FirmwareBuildSpec(FirmwareSpecBase):
    """
    The firmware is specified by an url pointing to a micropython git repo.
    This repo will then be cloned and the firmware compiled using mpbuild.
    """

    _filename: pathlib.Path | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        assert isinstance(self._filename, pathlib.Path | None)

    @property
    def filename(self) -> pathlib.Path:
        if self._filename is None:
            raise ValueError(
                f"Firmware for '{self.board_variant.name_normalized}': Firmware filename is not defined. Probably the firmware has not been compiled yet."
            )
        if not self._filename.is_file():
            raise ValueError(
                f"Firmware for '{self.board_variant.name_normalized}': Firmware does not exist: {self._filename}"
            )

        return self._filename


@dataclasses.dataclass(frozen=True, repr=True)
class FirmwareDownloadSpec(FirmwareSpecBase):
    """
    The firmware is specified by an url where it may be downloaded.
    """

    url: str
    """
    Example: https://micropython.org/resources/firmware/PYBV11-20240222-v1.22.2.dfu
    """

    _filename: pathlib.Path | None = None
    """
    Example: Downloads/PYBV11-20230426-v1.20.0.dfu
    None: If not yet downloaded
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        assert isinstance(self.url, str)
        assert isinstance(self._filename, pathlib.Path | None)

    def download(self) -> pathlib.Path:
        return self.filename

    @property
    def filename(self) -> pathlib.Path:
        """
        Download firmware if not already there
        """
        parse_result = urlparse(self.url)
        _directory, _separator, _filename = parse_result.path.rpartition("/")

        filename = DIRECTORY_OCTOPROBE_CACHE_FIRMWARE / _filename
        if filename.exists():
            return filename
        try:
            tmp_filename, _headers = urlretrieve(url=self.url)
        except HTTPError as e:
            raise ValueError(f"{self.url}: {e}") from e

        shutil.move(src=tmp_filename, dst=filename)
        return filename

    @staticmethod
    def factory(filename: str) -> FirmwareDownloadSpec:
        assert isinstance(filename, str)
        return FirmwareDownloadSpec.factory2(pathlib.Path(filename))

    @staticmethod
    def factory2(filename: pathlib.Path) -> FirmwareDownloadSpec:
        assert isinstance(filename, pathlib.Path)
        assert filename.is_file(), str(filename)

        try:
            with filename.open("r") as f:
                json_obj = json.load(f)
            return FirmwareDownloadSpec.factory_json(json_obj=json_obj)
        except Exception as e:
            raise ValueError(f"{filename}: Failed to read: {e!r}") from e

    @staticmethod
    def factory_json(json_obj: dict[str, typing.Any]) -> FirmwareDownloadSpec:
        assert isinstance(json_obj, dict)

        json_obj["board_variant"] = BoardVariant.factory(json_obj["board_variant"])
        return FirmwareDownloadSpec(**json_obj)


class DutProgrammer(abc.ABC):
    @abc.abstractmethod
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None: ...


class DutProgrammerDfuUtil(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareBuildSpec)
        assert len(tentacle.tentacle_spec.programmer_args) == 0, "Not yet supported"
        assert tentacle.dut is not None

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX_RELAYS_DUT_BOOT])

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = pyboard_udev_filter_boot_mode(
                tentacle.tentacle_spec.mcu_usb_id.boot
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after power on",
                timeout_s=3.0,
            )

        assert isinstance(event, Rp2UdevBootModeEvent)
        filename_dfu = firmware_spec.filename
        args = [
            "dfu-util",
            "--serial",
            event.serial,
            "--download",
            str(filename_dfu),
        ]
        subprocess_run(args=args, timeout_s=60.0)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX_RELAYS_DUT_BOOT])


class DutProgrammerPicotool(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """ """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpecBase)
        assert len(tentacle.tentacle_spec.programmer_args) == 0, "Not yet supported"
        assert tentacle.dut is not None

        tentacle.infra.power_dut_off_and_wait()

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[IDX_RELAYS_DUT_BOOT])

        with udev.guard as guard:
            tentacle.power.dut = True

            assert tentacle.tentacle_spec.mcu_usb_id is not None
            udev_filter = rp2_udev_filter_boot_mode(
                tentacle.tentacle_spec.mcu_usb_id.boot
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=tentacle.dut.label,
                text_expect="Expect RP2 to become visible on udev after power on",
                timeout_s=2.0,
            )

        assert isinstance(event, Rp2UdevBootModeEvent)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[IDX_RELAYS_DUT_BOOT])

        picotool_flash_micropython(
            event=event, filename_firmware=firmware_spec.filename
        )


class DutProgrammerEsptool(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpecBase,
    ) -> None:
        """
        The exp8622 does not require to be booted into boot(programming) mode.
        So we can reuse the port name from mp_remote
        """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpecBase)

        assert tentacle.dut is not None
        assert tentacle.dut.mp_remote is not None
        tty = tentacle.dut.mp_remote.close()
        assert tty is not None

        esptool_flash_micropython(
            tty=tty,
            filename_firmware=firmware_spec.filename,
            programmer_args=tentacle.tentacle_spec.programmer_args,
        )


def dut_programmer_factory(tags: str) -> DutProgrammer:
    """
    Example 'tags': programmer=picotool,xy=5
    """
    programmer = PropertyString(tags).get_tag_mandatory(TAG_PROGRAMMER)
    if programmer == "picotool":
        return DutProgrammerPicotool()
    if programmer == "dfu-util":
        return DutProgrammerDfuUtil()
    if programmer == "esptool":
        return DutProgrammerEsptool()
    raise ValueError(f"Unknown '{programmer}' in '{tags}'!")
