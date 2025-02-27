from __future__ import annotations

import time

from .. import util_mcu_pico
from ..usb_tentacle.usb_constants import (
    UsbPlug,
    UsbPlugs,
)
from ..usb_tentacle.usb_tentacle import UsbTentacle
from ..util_pyudev import UdevPoller

_DELIM = "  "
_DELIM2 = "    "


def bootmode(usb_tentacle: UsbTentacle, is_infra: bool, picotool_cmd: bool) -> None:
    if usb_tentacle.pico_infra.serial is None:
        print(
            _DELIM
            + "Tentacle is already in boot mode. Please unconnect and reconnect USB."
        )
        return

    print(_DELIM + "Press Boot Button.")
    print(_DELIM + "Power off PICO_INFRA and PICO_PROBE.")
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
        print(_DELIM + "Power on PICO_INFRA and PICO_PROBE.")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.PICO_INFRA: True,
                    UsbPlug.PICO_PROBE: True,
                }
            )
        )
        time.sleep(0.2)
        print(_DELIM + "Release Boot Button.")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.BOOT: True,
                }
            )
        )

        rp2 = usb_tentacle.pico_infra if is_infra else usb_tentacle.pico_probe
        tag = "PICO_INFRA" if is_infra else "PICO_PROBE"
        assert rp2 is not None

        if picotool_cmd:
            udev_filter = util_mcu_pico.pico_udev_filter_boot_mode(
                util_mcu_pico.RPI_PICO_USB_ID.boot,
                usb_location=rp2.location.short,
            )
        else:
            udev_filter = util_mcu_pico.pico_udev_filter_boot_mode2(
                util_mcu_pico.RPI_PICO_USB_ID.boot,
                usb_location=rp2.location.short,
            )
        event = guard.expect_event(
            udev_filter=udev_filter,
            text_where=f"Tentacle with serial {usb_tentacle.serial}",
            text_expect=f"Expect {tag} in programming mode to become visible on udev after power on",
            timeout_s=10.0,
        )
        print()
        if picotool_cmd:
            assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent)
            picotool = util_mcu_pico.picotool_cmd(
                event=event,
                filename_firmware="firmware.uf2",
            )
            picotool_text = " ".join(picotool)
            print(
                _DELIM + f"Detected {tag} on port {rp2.location.short}. Please flash:"
            )
            print(_DELIM2 + picotool_text)
        else:
            assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent2)
            print(
                _DELIM + f"Detected {tag} on port {rp2.location.short}. Please flash:"
            )
            print(_DELIM2 + f"cp firmware.uf2 {event.mount_point}")
