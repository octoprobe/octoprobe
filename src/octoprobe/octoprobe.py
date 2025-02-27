from __future__ import annotations

import enum
import pathlib
import typing

from .lib_tentacle import TentacleBase
from .usb_tentacle.usb_tentacle import UsbTentacles
from .util_baseclasses import OctoprobeAppExitException
from .util_pyudev import UdevPoller

FULL_POWERCYCLE_ALL_TENTACLES = False


class CtxTestRun:
    """
    The context of a test run
    """

    def __init__(self, connected_tentacles: typing.Sequence[TentacleBase]) -> None:
        assert isinstance(connected_tentacles, list)

        self.connected_tentacles = connected_tentacles

    @staticmethod
    def session_powercycle_tentacles() -> UsbTentacles:
        """
        Powers all RP2 infra.
        Finds all tentacle by finding pico_unique_id of the RP2 infra.
        """
        # We have to reset the power for all rp2-infra to become visible
        return UsbTentacles.query(poweron=FULL_POWERCYCLE_ALL_TENTACLES)

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
        self,
        udev_poller: UdevPoller,
        tentacle: TentacleBase,
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
        if not tentacle.is_mcu:
            return

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
            if not tentacle.is_mcu:
                continue
            tentacle.dut.mp_remote_close()
            # Before we can switch the relays: Connect to infra, power off and free mp_remote
            tentacle.infra.connect_mpremote_if_needed()
            try:
                tentacle.infra.mcu_infra.relays(
                    relays_open=tentacle.infra.list_all_relays
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
