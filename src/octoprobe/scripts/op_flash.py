from __future__ import annotations

import pathlib
import time

import typer

from .. import util_mcu_pico
from ..usb_tentacle.usb_constants import (
    UsbPlug,
    UsbPlugs,
)
from ..usb_tentacle.usb_tentacle import UsbTentacle
from ..util_mcu_pico import picotool_flash_micropython
from .op_bootmode import DELIM, do_bootmode


def do_flash(usb_tentacle: UsbTentacle, is_infra: bool, firmware: pathlib.Path) -> None:
    assert isinstance(usb_tentacle, UsbTentacle)
    assert isinstance(firmware, pathlib.Path)
    assert isinstance(is_infra, bool)
    if not firmware.is_file():
        print(f"Firmware does not exist: {firmware}")
        raise typer.Exit()

    if not is_infra:
        if usb_tentacle.pico_probe is None:
            # This is a v0.3 tentacle without a PICO_PROBE
            print(
                DELIM
                + f"SKIPPED: Tentacle {usb_tentacle.tentacle_version.version} does not have a PICO_PROBE."
            )
            return

    event = do_bootmode(
        usb_tentacle=usb_tentacle,
        is_infra=is_infra,
        picotool_cmd=True,
        print_cb=lambda msg: None,
    )
    if event is None:
        return

    assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent)
    picotool_flash_micropython(
        event=event,
        directory_logs=pathlib.Path("/tmp"),
        filename_firmware=firmware,
    )

    if usb_tentacle.pico_probe is None:
        # This is a v0.3 tentacle without a PICO_PROBE
        return

    # This is a v0.4 tentacle. The other PICO is still in programming mode
    # and therefore both processors have to be restarted.

    # Powercycle
    usb_tentacle.switches.infra = False
    usb_tentacle.switches.infraboot = True
    usb_tentacle.switches.dut = False

    time.sleep(0.1)

    usb_tentacle.switches.infra = True
