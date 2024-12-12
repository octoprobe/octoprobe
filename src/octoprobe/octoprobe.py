from __future__ import annotations

import enum
import pathlib
import time
import typing

from octoprobe import util_usb_serial

from .lib_tentacle import TentacleBase
from .util_baseclasses import OctoprobeAppExitException
from .util_power import UsbPlug, UsbPlugs
from .util_pyudev import UdevPoller
from .util_usb_serial import QueryResultTentacles

FULL_POWERCYCLE_ALL_TENTACLES = False


class NTestRun:
    """
    Why this class is called 'NTestRun':

        pytest collects all classes starting w'TestRun' would be collected by pytest: So we name it 'NTestRun'
    """

    def __init__(self, connected_tentacles: typing.Sequence[TentacleBase]) -> None:
        assert isinstance(connected_tentacles, list)

        self.connected_tentacles = connected_tentacles

    @staticmethod
    def session_powercycle_tentacles() -> QueryResultTentacles:
        """
        Powers all RP2 infra.
        Finds all tentacle by finding rp2_unique_id of the RP2 infra.
        """
        # We have to reset the power for all rp2-infra to become visible
        hubs = util_usb_serial.QueryResultTentacle.query_fast()
        hubs = hubs.select(serials=None)
        if FULL_POWERCYCLE_ALL_TENTACLES:
            # Powercycling ALL hubs
            hubs.power(plugs=UsbPlugs.default_off())
            time.sleep(0.2)  # success: 0.0
            hubs.power(plugs=UsbPlugs({UsbPlug.INFRA: True}))
            # Without hub inbetween: failed: 0.4, success: 0.5
            # With hub inbetween: failed: 0.7, success: 0.8
            # RSHTECH 7 port hub produced errors using 1.2s
            time.sleep(2.0)
        else:
            hubs.power(
                plugs=UsbPlugs(
                    {
                        UsbPlug.INFRA: True,
                        UsbPlug.INFRABOOT: True,
                        UsbPlug.DUT: False,
                        UsbPlug.ERROR: False,
                    }
                )
            )
            time.sleep(2.0)

        return util_usb_serial.QueryResultTentacle.query_fast()

    def session_teardown(self) -> None:
        pass

    def function_setup_infa_and_dut(
        self,
        udev_poller: UdevPoller,
        tentacle: TentacleBase,
        directory_logs: pathlib.Path,
    ) -> None:
        self.function_prepare_dut(tentacle=tentacle)
        self.function_setup_infra(udev_poller=udev_poller, tentacle=tentacle)
        self.function_setup_dut_flash(
            udev_poller=udev_poller,
            tentacle=tentacle,
            directory_logs=directory_logs,
        )

    def function_setup_infra(
        self, udev_poller: UdevPoller, tentacle: TentacleBase
    ) -> None:
        """
        Power off all other known usb power plugs.

        For each active tentacle:

        * Power on infa
        * Flash firmware
        * Get serial numbers and assert if it does not match the config
        * Return tty
        """

        # Instantiate poller BEFORE switching on power to avoid a race condition
        tentacle.infra.setup_infra(udev_poller)
        tentacle.infra.mcu_infra.active_led(on=False)

        if not FULL_POWERCYCLE_ALL_TENTACLES:
            # As the tentacle infra has NOT been powercycled, we
            # have to reset the relays
            tentacle.infra.mcu_infra.relays(
                relays_close=[],
                relays_open=[1, 2, 3, 4, 5, 6, 7],
            )

    def function_prepare_dut(self, tentacle: TentacleBase) -> None:
        tentacle.power.dut = False
        tentacle.infra.mp_remote_close()
        if tentacle.is_mcu:
            tentacle.dut.mp_remote_close()

    def function_setup_dut_flash(
        self,
        udev_poller: UdevPoller,
        tentacle: TentacleBase,
        directory_logs: pathlib.Path,
    ) -> None:
        # Flash the MCU
        tentacle.flash_dut(
            udev_poller=udev_poller,
            directory_logs=directory_logs,
            firmware_spec=tentacle.tentacle_state.firmware_spec,
        )

    def function_teardown(
        self, active_tentacles: typing.Sequence[TentacleBase]
    ) -> None:
        if False:
            for tentacle in active_tentacles:
                tentacle.power_dut_off_and_wait()

        for tentacle in active_tentacles:
            # Before we power off the DUT: free mp_remote
            tentacle.dut.mp_remote_close()
            # Before we can switch the relays: Connect to infra, power off and free mp_remote
            tentacle.infra.connect_mpremote_if_needed()
            try:
                tentacle.infra.mcu_infra.relays(
                    relays_open=tentacle.infra.LIST_ALL_RELAYS
                )
            except Exception as e:
                raise OctoprobeAppExitException(
                    f"{tentacle.infra.label}: Failed to control relays: {e!r}"
                ) from e
            tentacle.infra.power.dut = False
            tentacle.infra.mp_remote_close()

    def setup_relays(
        self, tentacles: typing.Sequence[TentacleBase], futs: tuple[enum.StrEnum]
    ) -> None:
        assert isinstance(tentacles, list | tuple)
        assert isinstance(futs, list | tuple)
        assert len(futs) == 1
        fut = futs[0]
        for tentacle in tentacles:
            tentacle.set_relays_by_FUT(fut=fut)
