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

from .util_constants import (
    DIRECTORY_OCTOPROBE_CACHE_FIRMWARE,
    TAG_BOARDS,
)
from .util_micropython_boards import BoardVariant, board_variants

if typing.TYPE_CHECKING:
    from .lib_tentacle import TentacleBase

logger = logging.getLogger(__file__)

FIRMWARE_DOWNLOAD_EXTENSION = ".json"
MICROPYTHON_FULL_VERSION_TEXT_FORCE = "requires_firmware_flashing"


@dataclasses.dataclass(frozen=True, repr=True)
class FirmwareSpecBase(abc.ABC):
    board_variant: BoardVariant
    """
    Examples:
    PYBV11
    PYBV11-THREAD
    RPI_PICO
    """

    micropython_full_version_text: str = MICROPYTHON_FULL_VERSION_TEXT_FORCE
    """
    Example:
    >>> import sys
    >>> sys.version
    '3.4.0; MicroPython v1.20.0 on 2023-04-26'
    >>> sys.implementation
    'Raspberry Pi Pico2 with RP2350-RISCV'

    'full_version_text' will be:
      3.4.0; MicroPython v1.20.0 on 2023-04-26, Raspberry Pi Pico2 with RP2350-RISCV

    None: If not known
    """

    @property
    def requires_flashing(self) -> bool:
        return self.micropython_full_version_text == MICROPYTHON_FULL_VERSION_TEXT_FORCE

    def __post_init__(self) -> None:
        assert isinstance(self.board_variant, BoardVariant)
        assert isinstance(self.micropython_full_version_text, str)

    @property
    def do_flash(self) -> bool:
        return True

    @property
    @abc.abstractmethod
    def filename(self) -> pathlib.Path: ...

    def match_board(self, tentacle: TentacleBase) -> bool:
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
class FirmwareNoFlashingSpec(FirmwareSpecBase):
    @property
    def filename(self) -> pathlib.Path:
        raise NotImplementedError()

    def match_board(self, tentacle: TentacleBase) -> bool:
        """
        Return True: If tentacles board matches the firmware_spec board.
        """
        return True

    @property
    def do_flash(self) -> bool:
        return False

    @staticmethod
    def factory() -> FirmwareNoFlashingSpec:
        return FirmwareNoFlashingSpec(
            board_variant=BoardVariant(board="NoFlashing", variant="")
        )


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

    @property
    def text(self) -> str:
        lines = (
            f"board_variant={self.board_variant.name_normalized}",
            f"micropython_full_version_text={self.micropython_full_version_text}",
            f"requires_flashing={self.requires_flashing}",
            f"filename={self._filename}",
        )
        return "\n".join(lines)


@dataclasses.dataclass(frozen=True, repr=True)
class FirmwareDownloadSpec(FirmwareSpecBase):
    """
    The firmware is specified by an url where it may be downloaded.
    """

    url: str = "???"
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


class FirmwaresBuilt(dict[str, FirmwareBuildSpec]):
    pass
