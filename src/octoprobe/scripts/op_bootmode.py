from __future__ import annotations

import time
import typing

from .. import util_mcu_pico
from ..lib_tentacle_infra import TentacleInfra
from ..usb_tentacle.usb_constants import HwVersion
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
    tag = "PICO_INFRA" if is_infra else "PICO_PROBE"
    tentacle_infra = TentacleInfra.factory_usb_tentacle(usb_tentacle=usb_tentacle)

    if usb_tentacle.pico_infra.serial is None:
        print(
            DELIM
            + "Tentacle is already in boot mode.\n"
            + DELIM
            + "Please unconnect and reconnect USB.\n"
            + DELIM
            + "Or add the command line parameter: --poweron"
        )
        return None

    if not is_infra:
        tentacle_infra.connect_mpremote_if_needed()
        hw_version = tentacle_infra.mcu_infra.hw_version
        if hw_version == HwVersion.V03:
            # This is a v0.3 tentacle without a PICO_PROBE
            print(DELIM + f"SKIPPED: Tentacle {hw_version} does not have a PICO_PROBE.")
            return None

    print_cb(DELIM + f"{tag}: Power off.")
    print_cb(DELIM + f"{tag}: Press Boot Button.")
    if is_infra:
        usb_tentacle.switches.infra = False
        # boot on rp_infra is invers (False: pressed)
        usb_tentacle.switches.infraboot = False
    else:
        assert tentacle_infra is not None
        # boot on rp_probe is invers (False: pressed)
        tentacle_infra.switches.proberun = False
        tentacle_infra.switches.probeboot = False

    time.sleep(0.1)

    with UdevPoller() as guard:
        print_cb(DELIM + f"{tag}: Power on.")
        if is_infra:
            usb_tentacle.switches.infra = True
        else:
            tentacle_infra.switches.proberun = True

        time.sleep(0.2)
        print_cb(DELIM + f"{tag}: Release Boot Button.")
        if is_infra:
            usb_tentacle.switches.infraboot = True
        else:
            # probe
            assert tentacle_infra is not None
            assert HwVersion.is_V05or_newer(tentacle_infra.mcu_infra.hw_version)
            tentacle_infra.switches.probeboot = True

        pico = usb_tentacle.pico_infra if is_infra else usb_tentacle.pico_probe
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
                DELIM + f"{tag}: Detected on port {pico.location.short}. Please flash:"
            )
            print_cb(DELIM2 + picotool_text)
            return event

        assert isinstance(event, util_mcu_pico.Rp2UdevBootModeEvent2)
        print_cb(
            DELIM + f"{tag}: Detected on port {pico.location.short}. Please flash:"
        )
        print_cb(DELIM2 + f"cp firmware.uf2 {event.mount_point}")
        return None
