from __future__ import annotations

import time
import typing

from .. import util_mcu_pico
from ..usb_tentacle.usb_constants import (
    UsbPlug,
    UsbPlugs,
)
from ..usb_tentacle.usb_tentacle import UsbTentacle
from ..util_pyudev import UdevPoller

DELIM = "  "
DELIM2 = "    "


def do_bootmode(
    usb_tentacle: UsbTentacle,
    is_infra: bool,
    picotool_cmd: bool,
    print_cb: typing.Callable[[str], None] = print,
) -> util_mcu_pico.Rp2UdevBootModeEvent | None:
    if usb_tentacle.pico_infra.serial is None:
        print(
            DELIM
            + "Tentacle is already in boot mode. Please unconnect and reconnect USB."
        )
        return None

    if not is_infra:
        if usb_tentacle.pico_probe is None:
            # This is a v0.3 tentacle without a PICO_PROBE
            print(
                DELIM
                + f"SKIPPED: Tentacle {usb_tentacle.tentacle_version.version} does not have a PICO_PROBE."
            )
            return None

    print_cb(DELIM + "Press Boot Button.")
    print_cb(DELIM + "Power off PICO_INFRA and PICO_PROBE.")
    usb_tentacle.set_plugs(
        plugs=UsbPlugs(
            {
                UsbPlug.PICO_INFRA: False,
                UsbPlug.PICO_PROBE: False,
                UsbPlug.DUT: False,
                UsbPlug.BOOT: False,
            }
        )
    )

    time.sleep(0.1)

    with UdevPoller() as guard:
        print_cb(DELIM + "Power on PICO_INFRA and PICO_PROBE.")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.PICO_INFRA: True,
                    UsbPlug.PICO_PROBE: True,
                }
            )
        )
        time.sleep(0.2)
        print_cb(DELIM + "Release Boot Button.")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.BOOT: True,
                }
            )
        )

        pico = usb_tentacle.pico_infra if is_infra else usb_tentacle.pico_probe
        tag = "PICO_INFRA" if is_infra else "PICO_PROBE"
        assert pico is not None

        if picotool_cmd:
            udev_filter = util_mcu_pico.pico_udev_filter_boot_mode(
                util_mcu_pico.RPI_PICO_USB_ID.boot,
                usb_location=pico.location.short,
            )
        else:
            udev_filter = util_mcu_pico.pico_udev_filter_boot_mode2(
                util_mcu_pico.RPI_PICO_USB_ID.boot,
                usb_location=pico.location.short,
            )
        event = guard.expect_event(
            udev_filter=udev_filter,
            text_where=f"Tentacle with serial {usb_tentacle.serial}",
            text_expect=f"Expect {tag} in programming mode to become visible on udev after power on",
            timeout_s=10.0,
        )
        print_cb("")
        if picotool_cmd:
            assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent)
            picotool = util_mcu_pico.picotool_cmd(
                event=event,
                filename_firmware="firmware.uf2",
            )
            picotool_text = " ".join(picotool)
            print_cb(
                DELIM + f"Detected {tag} on port {pico.location.short}. Please flash:"
            )
            print_cb(DELIM2 + picotool_text)
            return event
        else:
            assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent2)
            print_cb(
                DELIM + f"Detected {tag} on port {pico.location.short}. Please flash:"
            )
            print_cb(DELIM2 + f"cp firmware.uf2 {event.mount_point}")
            return None
