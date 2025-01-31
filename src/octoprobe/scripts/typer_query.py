from __future__ import annotations

import dataclasses

from octoprobe.usb_tentacle.usb_tentacle import UsbTentacles


@dataclasses.dataclass
class Query:
    verbose: bool
    ids: set[str] = dataclasses.field(default_factory=set)

    def print(self) -> None:
        usb_tentacles = UsbTentacles.query(require_serial=False)
        for usb_tentacle in usb_tentacles:
            print(usb_tentacle.short)
