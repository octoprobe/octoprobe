from __future__ import annotations

import dataclasses
import enum  # pylint: disable=unused-import
import io
import logging
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager

from usbhubctl import DualConnectedHub, Hub

from . import util_power, util_usb_serial
from .lib_tentacle_dut import TentacleDut
from .lib_tentacle_infra import TentacleInfra
from .util_baseclasses import TentacleSpec
from .util_dut_programmers import FirmwareSpecBase
from .util_pyudev import UdevPoller

logger = logging.getLogger(__file__)


class Tentacle[TTentacleSpec, TTentacleType: enum.StrEnum, TEnumFut: enum.StrEnum]:
    """
    The interface to a Tentacle:
    Both 'Infrastructure' and 'DUT'.
    """

    def __init__(
        self,
        tentacle_serial_number: str,
        tentacle_spec: TentacleSpec[TTentacleSpec, TTentacleType, TEnumFut],
        hw_version: str,
    ) -> None:
        assert isinstance(tentacle_serial_number, str)
        assert isinstance(tentacle_spec, TentacleSpec)
        assert isinstance(hw_version, str)
        assert (
            tentacle_serial_number == tentacle_serial_number.lower()
        ), f"Must not contain upper case letters: {tentacle_serial_number}"

        self.tentacle_serial_number = tentacle_serial_number
        self.tentacle_spec = tentacle_spec

        def _label(dut_or_infra: str) -> str:
            # return f"Tentacle {dut_or_infra}{tentacle_serial_number}({tentacle_spec.label})"
            return f"Tentacle {dut_or_infra}{self.label_short}"

        self.label = _label(dut_or_infra="")
        self.infra = TentacleInfra(label=_label(dut_or_infra="INFRA "))

        def get_dut() -> TentacleDut | None:
            if tentacle_spec.mcu_config is None:
                return None
            return TentacleDut(
                label=_label(dut_or_infra="DUT "),
                tentacle_spec=tentacle_spec,
            )

        self._dut = get_dut()
        self._firmware_spec: FirmwareSpecBase | None = None
        """
        Specifies the firmware.
        This will be updated for EVERY testfunction!
        If None: Use firmware already on the DUT.
        """

    def __repr__(self) -> str:
        return self.label

    def flash_dut(
        self, udev_poller: UdevPoller, firmware_spec: FirmwareSpecBase
    ) -> None:
        if self.dut is None:
            return

        self.dut.flash_dut(
            tentacle=self,
            udev=udev_poller,
            firmware_spec=firmware_spec,
        )

    @property
    def dut(self) -> TentacleDut:
        assert self._dut is not None
        return self._dut

    @property
    def is_mcu(self) -> bool:
        return self.tentacle_spec.is_mcu

    def do_not_flash_firmware(self) -> None:
        self._firmware_spec = None

    @property
    def has_firmware_spec(self) -> bool:
        return self._firmware_spec is not None

    @property
    def firmware_spec(self) -> FirmwareSpecBase:
        """
        This is only valid for tentacles.is_mcu!
        """
        assert self.is_mcu, "firmware_spec only makes sense for 'is_mcu' tentacles."
        assert self._firmware_spec is not None
        return self._firmware_spec

    @firmware_spec.setter
    def firmware_spec(self, spec: FirmwareSpecBase) -> None:
        assert self.is_mcu, "firmware_spec only makes sense for 'is_mcu' tentacles."
        assert isinstance(spec, FirmwareSpecBase)
        self._firmware_spec = spec

    @property
    def power(self) -> util_power.TentaclePlugsPower:
        return self.infra.power

    @property
    def description_short(self) -> str:
        f = io.StringIO()
        f.write(f"Label {self.tentacle_spec.label}\n")
        f.write(f"  tentacle_serial_number {self.tentacle_serial_number}\n")

        return f.getvalue()

    def power_dut_off_and_wait(self) -> None:
        if self.dut is None:
            return
        self.infra.power_dut_off_and_wait()
        self.dut.mp_remote_close()

    def assign_connected_hub(
        self, query_result_tentacle: util_usb_serial.QueryResultTentacle
    ) -> None:
        self.infra.assign_connected_hub(query_result_tentacle=query_result_tentacle)

    @property
    def label_short(self) -> str:
        """
        Example: 1831pico2
        Example: 1331daq
        """
        return self.tentacle_serial_number[-4:] + self.tentacle_spec.label

    @property
    def pytest_id(self) -> str:
        """
        Example: 1831pico2(RPI_PICO2-RISCV)
        Example: 1331daq
        """
        name = self.label_short
        if self.is_mcu:
            if self.firmware_spec is None:
                name += "(no-flashing)"
            else:
                name += f"({self.firmware_spec.board_variant.name_normalized})"
        return name

    def get_tag(self, tag: str) -> str | None:
        return self.tentacle_spec.get_tag(tag=tag)

    def get_tag_mandatory(self, tag: str) -> str:
        return self.tentacle_spec.get_tag_mandatory(tag=tag)

    @property
    @contextmanager
    def active_led(self) -> Iterator[None]:
        try:
            self.infra.mcu_infra.active_led(on=True)
            yield
        finally:
            self.infra.mcu_infra.active_led(on=False)

    def set_relays_by_FUT(self, fut: TEnumFut, open_others: bool = False) -> None:
        assert isinstance(fut, enum.StrEnum)
        assert isinstance(open_others, bool)

        relays_open = self.infra.LIST_ALL_RELAYS if open_others else []
        try:
            list_relays = self.tentacle_spec.relays_closed[fut]
        except KeyError as e:
            raise KeyError(
                f"{self.description_short}: Does not specify: tentacle_spec.relays_closed[{fut.name}]"
            ) from e
        self.infra.mcu_infra.relays(relays_close=list_relays, relays_open=relays_open)

    def dut_boot_and_init_mp_remote(self, udev: UdevPoller) -> None:
        assert isinstance(udev, UdevPoller)

        assert self.dut is not None
        self.dut.boot_and_init_mp_remote_dut(tentacle=self, udev=udev)

    @staticmethod
    def tentacles_description_short(tentacles: list[Tentacle]) -> str:
        f = io.StringIO()
        f.write("TENTACLES\n")
        for tentacle in tentacles:
            f.write(textwrap.indent(tentacle.description_short, prefix="  "))

        return f.getvalue()


@dataclasses.dataclass
class UsbHub:
    label: str
    model: Hub
    connected_hub: None | DualConnectedHub = None

    def get_plug(self, plug_number: int) -> UsbPlug:
        assert (
            1 <= plug_number <= self.model.plug_count
        ), f"{self.model.model}: Plug {plug_number} does not exit! Valid plugs [0..{self.model.plug_count}]."
        return UsbPlug(usb_hub=self, plug_number=plug_number)

    def setup(self) -> None:
        connected_hubs = self.model.find_connected_dualhubs()
        self.connected_hub = connected_hubs.expect_one()

    def teardown(self) -> None:
        pass

    @property
    def description_short(self) -> str:
        f = io.StringIO()
        f.write(f"Label {self.label}\n")
        f.write(f"  Model {self.model.model}\n")
        return f.getvalue()


@dataclasses.dataclass
class UsbPlug:
    usb_hub: UsbHub
    plug_number: int

    @property
    def description_short(self) -> str:
        return f"plug {self.plug_number} on '{self.usb_hub.label}' ({self.usb_hub.model.model})"

    @property
    def power(self) -> bool:
        raise NotImplementedError()

    @power.setter
    def power(self, on: bool) -> None:
        c = self.usb_hub.connected_hub
        assert c is not None
        c.get_plug(plug_number=self.plug_number).power(on=on)
