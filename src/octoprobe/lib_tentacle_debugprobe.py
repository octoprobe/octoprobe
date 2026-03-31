from __future__ import annotations

import logging
import typing

from .usb_tentacle.usb_constants import Switch
from .util_pyudev import UdevPoller

logger = logging.getLogger(__file__)

if typing.TYPE_CHECKING:
    from .lib_tentacle import TentacleBase


class TentacleDebugprobe:
    """
    The PROBE side of a tentacle PCB.
    Only valid if the DUT contains a MCU.

    * Allows to program the MCU
    * Allows to run micropython code on the MCU.
    """

    TAG = "debugprobe"

    def __init__(self, label: str, tentacle: TentacleBase) -> None:
        # pylint: disable=import-outside-toplevel
        from .lib_tentacle import TentacleBase

        assert isinstance(label, str)
        assert isinstance(tentacle, TentacleBase)

        self._tentacle = tentacle
        self.label = label

        self._tty: str | None = None

    @property
    def tty(self) -> str:
        assert self._tty is not None, "Need to call 'power_on()' first!"
        return self._tty

    def power_on(self, udev: UdevPoller) -> None:
        """
        Power on PICO_PROBE.
        As a side effect self._tty will be set.
        We are only allowed to call this once!
        """
        # pylint: disable=import-outside-toplevel
        from . import util_mcu, util_mcu_debugprobe

        assert isinstance(udev, UdevPoller)

        with udev.guard as guard:
            assert self._tty is None

            # Power on
            changed = self._tentacle.switches[Switch.PICO_PROBE_RUN].set(on=True)
            assert changed

            udev_filter = util_mcu.udev_filter_application_mode(
                usb_id=util_mcu_debugprobe.RPI_DEBUGPROBE_USB_ID.application,
                usb_location=self._tentacle.infra.usb_location_probe,
            )

            event = guard.expect_event(
                udev_filter=udev_filter,
                text_where=self.label,
                text_expect="Expect INFRA_PROBE to become visible on udev after power on",
                timeout_s=2.0,
            )
            assert isinstance(event, util_mcu.UdevApplicationModeEvent)
            self._tty = event.tty
            assert self._tty is not None
