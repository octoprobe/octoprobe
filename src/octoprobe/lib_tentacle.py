from __future__ import annotations

import abc
import contextlib
import enum  # pylint: disable=unused-import
import io
import logging
import pathlib
import textwrap
import typing

from .lib_tentacle_dut import TentacleDut
from .lib_tentacle_infra import TentacleInfra
from .usb_tentacle.usb_tentacle import (
    SERIALNUMBER_SHORT,
    TentaclePlugsPower,
    UsbTentacle,
)
from .util_baseclasses import TentacleInstance, TentacleSpecBase
from .util_constants import DELIMITER_SERIAL_BOARD
from .util_firmware_spec import FirmwareSpecBase
from .util_pyudev import UdevPoller

logger = logging.getLogger(__file__)


class TentacleState:
    """
    The USB hub connected.
    The firmware to be flashed.
    If the firmware was already flashed or not.
    The last firmware which was flashed.
    ...
    """

    def __init__(self) -> None:
        self.flash_skip = False
        """
        Never flash
        """

        self.flash_force = False
        """
        First time: force flash even if the correct firmware is installed.
        """

        self.last_firmware_flashed: FirmwareSpecBase | None = None
        """
        Will be update everytime after flashing.
        This may be used to calculate the priority of a testrun.
        """

        self._firmware_spec: FirmwareSpecBase | None = None
        """
        Specifies the firmware to be flashed for the next test.
        If None: Use firmware already on the DUT.
        """

        self.variants_required: list[str] | None = None
        """
        If None: All variants have to be build and tested.
        If, in case of RPI_PICO2, variants_required=["RISCV"]: Only "RISCV" will be build and tested.
        """

    def set_variants_required(self, variants: list[str]) -> None:
        assert isinstance(variants, list)
        assert self.variants_required is None
        self.variants_required = variants

    @property
    def firmware_spec(self) -> FirmwareSpecBase:
        """
        This is only valid for tentacles.is_mcu!
        """
        # assert self.is_mcu, "firmware_spec only makes sense for 'is_mcu' tentacles."
        assert self._firmware_spec is not None
        return self._firmware_spec

    @firmware_spec.setter
    def firmware_spec(self, spec: FirmwareSpecBase) -> None:
        # assert self.is_mcu, "firmware_spec only makes sense for 'is_mcu' tentacles."
        assert isinstance(spec, FirmwareSpecBase)
        self._firmware_spec = spec

    def do_not_flash_firmware(self) -> None:
        self._firmware_spec = None

    @property
    def has_firmware_spec(self) -> bool:
        return self._firmware_spec is not None


class TentacleBase(abc.ABC):
    """
    The interface to a Tentacle:
    Both 'Infrastructure' and 'DUT'.

    The livetime of the tentacles starts after the USB query and
    ends when the testrunner terminates.

    All tentacle information is read only.
    However, the 'dut' will have stateinformation that will change.
    """

    def __init__(
        self,
        tentacle_instance: TentacleInstance,
        tentacle_serial_number: str,
        usb_tentacle: UsbTentacle,
    ) -> None:
        assert isinstance(tentacle_instance, TentacleInstance)
        assert isinstance(tentacle_serial_number, str)
        assert tentacle_serial_number == tentacle_serial_number.lower(), (
            f"Must not contain upper case letters: {tentacle_serial_number}"
        )
        assert isinstance(usb_tentacle, UsbTentacle)
        self.tentacle_state = TentacleState()
        self.tentacle_serial_number = tentacle_serial_number
        self.tentacle_instance = tentacle_instance

        def _label(dut_or_infra: str) -> str:
            # return f"Tentacle {dut_or_infra}{tentacle_serial_number}({tentacle_spec.label})"
            return f"Tentacle {dut_or_infra}{self.label_short}"

        self.label = _label(dut_or_infra="")
        self.infra = TentacleInfra(
            label=_label(dut_or_infra="INFRA "),
            usb_tentacle=usb_tentacle,
        )

        def get_dut() -> TentacleDut | None:
            if self.is_mcu:
                return TentacleDut(label=_label(dut_or_infra="DUT "), tentacle=self)
            return None

        self._dut = get_dut()

    def __repr__(self) -> str:
        return self.label

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TentacleBase):
            return NotImplemented
        return self.tentacle_serial_number < other.tentacle_serial_number

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TentacleBase):
            return NotImplemented
        return self.tentacle_serial_number == other.tentacle_serial_number

    def __hash__(self) -> int:
        return hash(self.tentacle_serial_number)

    def flash_dut(
        self,
        udev_poller: UdevPoller,
        firmware_spec: FirmwareSpecBase,
        directory_logs: pathlib.Path,
    ) -> None:
        if self.dut is None:
            return

        self.dut.flash_dut(
            tentacle=self,
            udev=udev_poller,
            directory_logs=directory_logs,
            firmware_spec=firmware_spec,
        )

    @property
    def tentacle_spec_base(self) -> TentacleSpecBase:
        return self.tentacle_instance.tentacle_spec

    @property
    def dut(self) -> TentacleDut:
        assert self._dut is not None, f"{self.label}: self._dut is None!"
        return self._dut

    @property
    def is_mcu(self) -> bool:
        return self.tentacle_spec_base.is_mcu

    @property
    def power(self) -> TentaclePlugsPower:
        return self.infra.power

    @property
    def description_short(self) -> str:
        f = io.StringIO()
        f.write(f"Label {self.tentacle_spec_base.tentacle_tag}\n")
        f.write(f"  tentacle_serial_number {self.tentacle_serial_number}\n")

        return f.getvalue()

    def power_dut_off_and_wait(self) -> None:
        if self.dut is None:
            return
        self.infra.power_dut_off_and_wait()
        self.dut.mp_remote_close()

    @property
    def label_short(self) -> str:
        """
        Example: 1831-RPI_PICO
        Example: 1331-DAQ
        """
        return (
            self.tentacle_serial_number[-SERIALNUMBER_SHORT:]
            + DELIMITER_SERIAL_BOARD
            + self.tentacle_spec_base.tentacle_tag
        )

    @property
    @abc.abstractmethod
    def pytest_id(self) -> str:
        """
        Example: 1831-pico2(RPI_PICO2-RISCV)
        Example: 1331-daq
        """

    def get_tag(self, tag: str) -> str | None:
        return self.tentacle_spec_base.get_tag(tag=tag)

    def get_tag_mandatory(self, tag: str) -> str:
        return self.tentacle_spec_base.get_tag_mandatory(tag=tag)

    @property
    @contextlib.contextmanager
    def active_led_on(self) -> typing.Iterator[typing.Any]:
        try:
            self.infra.mcu_infra.active_led(on=True)
            yield
        finally:
            self.infra.mcu_infra.active_led(on=False)

    def set_relays_by_FUT(self, fut: enum.StrEnum, open_others: bool = False) -> None:
        assert isinstance(fut, enum.StrEnum)
        assert isinstance(open_others, bool)

        relays_open = self.infra.list_all_relays if open_others else []
        try:
            list_relays = self.tentacle_spec_base.relays_closed[fut]
        except KeyError as e:
            try:
                # Fallback to the default value given by the key 'None'.
                list_relays = self.tentacle_spec_base.relays_closed[None]
            except KeyError:
                raise KeyError(
                    f"{self.description_short}: Does not specify: tentacle_spec.relays_closed[{fut.name}]"
                ) from e
        self.infra.mcu_infra.relays(relays_close=list_relays, relays_open=relays_open)

    def dut_boot_and_init_mp_remote(self, udev: UdevPoller) -> None:
        assert isinstance(udev, UdevPoller)

        assert self.dut is not None
        self.dut.boot_and_init_mp_remote_dut(tentacle=self, udev=udev)

    @staticmethod
    def tentacles_description_short(tentacles: typing.Sequence[TentacleBase]) -> str:
        f = io.StringIO()
        f.write("TENTACLES\n")
        for tentacle in tentacles:
            f.write(textwrap.indent(tentacle.description_short, prefix="  "))

        return f.getvalue()
