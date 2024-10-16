from __future__ import annotations

import enum
import time

from octoprobe import util_usb_serial
from octoprobe.util_power import UsbPlug, UsbPlugs
from octoprobe.util_usb_serial import SerialNumberNotFoundException

from .lib_tentacle import Tentacle
from .lib_testbed import Testbed
from .util_pyudev import UdevPoller


class NTestRun:
    """
    Why this class is called 'NTestRun':

        pytest collects all classes starting w'TestRun' would be collected by pytest: So we name it 'NTestRun'
    """

    def __init__(self, testbed: Testbed) -> None:
        assert isinstance(testbed, Testbed)
        self.testbed = testbed
        self._udev_poller: UdevPoller | None = None

    @property
    def udev_poller(self) -> UdevPoller:
        if self._udev_poller is None:
            self._udev_poller = UdevPoller()
        return self._udev_poller

    def session_powercycle_tentacles(self) -> None:
        """
        Powers all RP2 infra.
        Finds all tentacle by finding rp2_unique_id of the RP2 infra.
        """
        # We have to reset the power for all rp2-infra to become visible
        hubs = util_usb_serial.QueryResultTentacle.query(verbose=False)
        hubs = hubs.select(serials=None)
        hubs.power(plugs=UsbPlugs.default_off())
        time.sleep(0.2)  # success: 0.0
        hubs.power(plugs=UsbPlugs({UsbPlug.INFRA: True}))
        # Without hub inbetween: failed: 0.4, success: 0.5
        # With hub inbetween: failed: 0.7, success: 0.8
        time.sleep(1.2)

        hubs = util_usb_serial.QueryResultTentacle.query(verbose=True)
        for tentacle in self.testbed.tentacles:
            try:
                query_result_tentacle = hubs.get(
                    serial_number=tentacle.tentacle_serial_number
                )
            except SerialNumberNotFoundException as e:
                raise SerialNumberNotFoundException(tentacle.label) from e
            tentacle.assign_connected_hub(query_result_tentacle=query_result_tentacle)

    def function_setup_infra(self) -> None:
        """
        Power off all other known usb power plugs.

        For each active tentacle:

        * Power on infa
        * Flash firmware
        * Get serial numbers and assert if it does not match the config
        * Return tty
        """

        # Instantiate poller BEFORE switching on power to avoid a race condition
        for tentacle in self.testbed.tentacles:
            tentacle.infra.setup_infra(self.udev_poller)

    def session_teardown(self) -> None:
        if self._udev_poller is not None:
            self._udev_poller.close()
            self._udev_poller = None

    def function_prepare_dut(self) -> None:
        for tentacle in self.testbed.tentacles:
            tentacle.power.dut = False
            tentacle.infra.mp_remote_close()
            if tentacle.dut is not None:
                tentacle.dut.mp_remote_close()

    def function_setup_dut(self, active_tentacles: list[Tentacle]) -> None:
        # Flash the MCU(s)
        for tentacle in active_tentacles:
            if tentacle.is_mcu:
                tentacle.infra.mcu_infra.active_led(on=True)
                tentacle.flash_dut(
                    udev_poller=self.udev_poller,
                    firmware_spec=tentacle.firmware_spec,
                )

        for tentacle in active_tentacles:
            tentacle.infra.mcu_infra.active_led(on=True)

    def function_teardown(self, active_tentacles: list[Tentacle]) -> None:
        if False:
            for tentacle in active_tentacles:
                tentacle.power_dut_off_and_wait()

        for tentacle in active_tentacles:
            tentacle.infra.mcu_infra.relays(relays_open=tentacle.infra.LIST_ALL_RELAYS)

    def setup_relays(
        self, tentacles: list[Tentacle], futs: tuple[enum.StrEnum]
    ) -> None:
        assert isinstance(tentacles, list | tuple)
        assert isinstance(futs, list | tuple)
        assert len(futs) == 1
        fut = futs[0]
        for tentacle in tentacles:
            tentacle.set_relays_by_FUT(fut=fut)
