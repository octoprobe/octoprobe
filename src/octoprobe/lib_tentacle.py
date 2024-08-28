from __future__ import annotations

import dataclasses
import enum  # pylint: disable=unused-import
import io
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from usbhubctl import DualConnectedHub, Hub

from . import util_power, util_usb_serial
from .lib_tentacle_dut import TentacleDut
from .lib_tentacle_infra import TentacleInfra
from .util_baseclasses import TentacleSpec
from .util_dut_mcu import TAG_MCU
from .util_dut_programmers import FirmwareSpec
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
    ) -> None:
        assert isinstance(tentacle_serial_number, str)
        assert isinstance(tentacle_spec, TentacleSpec)
        assert (
            tentacle_serial_number == tentacle_serial_number.lower()
        ), f"Must not contain upper case letters: {tentacle_serial_number}"

        def _label(dut_or_infra: str) -> str:
            return f"Tentacle {dut_or_infra} {tentacle_serial_number}({tentacle_spec.label})"

        self.label = _label(dut_or_infra="")
        self.tentacle_serial_number = tentacle_serial_number
        self.tentacle_spec = tentacle_spec
        self.infra = TentacleInfra(label=_label(dut_or_infra="INFRA "))

        def get_dut() -> TentacleDut | None:
            if tentacle_spec.mcu_config is None:
                return None
            return TentacleDut(
                label=_label(dut_or_infra="DUT "),
                tentacle_spec=tentacle_spec,
            )

        self.dut = get_dut()

    def flash_dut(self, udev_poller: UdevPoller, firmware_spec: FirmwareSpec) -> None:
        if self.dut is None:
            return

        # with self.active_led:
        self.dut.flash_dut(
            tentacle=self,
            udev=udev_poller,
            firmware_spec=firmware_spec,
        )

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
    def pytest_id(self) -> str:
        name = self.tentacle_spec.tentacle_type.name
        if name.startswith("TENTACLE_MCU"):
            name = self.tentacle_spec.get_property_mandatory(TAG_MCU)
        name = name.replace("TENTACLE_DEVICE_", "").replace("TENTACLE_", "")
        return name + "_" + self.tentacle_serial_number[-4:]

    def get_property(self, tag: str) -> str | None:
        return self.tentacle_spec.get_property(tag=tag)

    def get_property_mandatory(self, tag: str) -> str:
        return self.tentacle_spec.get_property_mandatory(tag=tag)

    @property
    @contextmanager
    def active_led(self) -> Iterator[None]:
        try:
            self.infra.mcu_infra.active_led(on=True)
            yield
        finally:
            self.infra.mcu_infra.active_led(on=False)


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
