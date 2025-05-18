from __future__ import annotations

from ..lib_tentacle_infra import TentacleInfra
from ..usb_tentacle.usb_tentacle import UsbTentacle


def do_exec_infra(
    usb_tentacle: UsbTentacle,
    code: str,
) -> str:
    print(usb_tentacle)

    infra = TentacleInfra(f"ad_hoc_{usb_tentacle.label_long}", usb_tentacle)
    try:
        infra.connect_mpremote_if_needed()
        # The following command will load the base code into the infra-pico
        infra.mcu_infra.get_unique_id()
        return infra.mp_remote.exec_raw(cmd=code)
    finally:
        infra.mp_remote_close()
