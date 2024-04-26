from __future__ import annotations

import abc
import dataclasses
import json
import pathlib
import typing
from urllib.parse import urlparse
from urllib.request import urlretrieve

from usbhubctl.util_subprocess import subprocess_run

from .util_baseclasses import PropertyString
from .util_constants import DIRECTORY_CACHE_FIRMWARE, TAG_BOARD, TAG_PROGRAMMER
from .util_pyboard import UDEV_FILTER_PYBOARD_BOOT_MODE
from .util_rp2 import (
    UDEV_FILTER_RP2_BOOT_MODE,
    UdevBootModeEvent,
    rp2_flash_micropython,
)

if typing.TYPE_CHECKING:
    from octoprobe.lib_tentacle import Tentacle

    from .util_pyudev import UdevPoller


@dataclasses.dataclass
class FirmwareSpec:
    board: str
    """
    Examples: PYBV11, RPI_PICO
    """
    url: str
    """
    Example: https://micropython.org/resources/firmware/PYBV11-20240222-v1.22.2.dfu
    """

    micropython_version_text: str
    """
    Example:
    >>> import sys
    >>> sys.version
    '3.4.0; MicroPython v1.20.0 on 2023-04-26'
    """

    _filename: pathlib.Path | None = None
    """
    Example: Downloads/PYBV11-20230426-v1.20.0.dfu
    None: If not yet downloaded
    """

    def __post_init__(self) -> None:
        pass

    def download(self) -> pathlib.Path:
        return self.filename

    @property
    def filename(self) -> pathlib.Path:
        """
        Download firmware if not already there
        """
        parse_result = urlparse(self.url)
        _directory, _separator, _filename = parse_result.path.rpartition("/")

        filename = DIRECTORY_CACHE_FIRMWARE / _filename
        if filename.exists():
            return filename
        tmp_filename, _headers = urlretrieve(url=self.url)

        pathlib.Path(tmp_filename).rename(target=filename)
        return filename

    def match_board(self, tentacle: Tentacle) -> bool:
        """
        Return True: If tentacles board matches the firmware_spec board.
        """
        # assert tentacle.tentacle_spec.tentacle_type.is_mcu
        board = tentacle.get_property(TAG_BOARD)
        return board == self.board

    @staticmethod
    def factory(filename: str) -> FirmwareSpec:
        assert isinstance(filename, str)
        return FirmwareSpec.factory2(pathlib.Path(filename))

    @staticmethod
    def factory2(filename: pathlib.Path) -> FirmwareSpec:
        assert isinstance(filename, pathlib.Path)
        assert filename.is_file(), str(filename)

        with filename.open("r") as f:
            json_obj = json.load(f)
        return FirmwareSpec(**json_obj)


class DutProgrammer(abc.ABC):
    @abc.abstractmethod
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpec,
    ) -> str: ...


class DutProgrammerDfuUtil(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpec,
    ) -> str:
        """
        Example return: /dev/ttyACM1
        """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpec)
        assert tentacle.dut is not None

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[1])

        tentacle.power_dut_off_and_wait()

        with udev.guard as guard:
            tentacle.power.dut = True

            event = guard.expect_event(
                UDEV_FILTER_PYBOARD_BOOT_MODE,
                text_where=tentacle.dut.label,
                text_expect="Expect mcu to become visible on udev after power on",
                timeout_s=3.0,
            )

        print(f"EVENT PYBOARD: {event}")
        assert isinstance(event, UdevBootModeEvent)
        filename_dfu = firmware_spec.filename
        assert filename_dfu.is_file()
        args = [
            "dfu-util",
            "--serial",
            event.serial,
            "--download",
            str(filename_dfu),
        ]
        subprocess_run(args=args, timeout_s=60.0)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[1])

        return tentacle.dut.dut_mcu.application_mode_power_up(
            tentacle=tentacle, udev=udev
        )


class DutProgrammerPicotool(DutProgrammer):
    def flash(
        self,
        tentacle: Tentacle,
        udev: UdevPoller,
        firmware_spec: FirmwareSpec,
    ) -> str:
        """
        Example return: /dev/ttyACM1
        """
        assert tentacle.__class__.__qualname__ == "Tentacle"
        assert isinstance(firmware_spec, FirmwareSpec)
        assert tentacle.dut is not None

        tentacle.infra.power_dut_off_and_wait()

        # Press Boot Button
        tentacle.infra.mcu_infra.relays(relays_close=[1])

        with udev.guard as guard:
            tentacle.power.dut = True

            event = guard.expect_event(
                UDEV_FILTER_RP2_BOOT_MODE,
                text_where=tentacle.dut.label,
                text_expect="Expect RP2 to become visible on udev after power on",
                timeout_s=2.0,
            )

        assert isinstance(event, UdevBootModeEvent)

        # Release Boot Button
        tentacle.infra.mcu_infra.relays(relays_open=[1])

        rp2_flash_micropython(event=event, filename_uf2=firmware_spec.filename)

        return tentacle.dut.dut_mcu.application_mode_power_up(
            tentacle=tentacle, udev=udev
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
    raise ValueError(f"Unknown '{programmer}' in '{tags}'!")
