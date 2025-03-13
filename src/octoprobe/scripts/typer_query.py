from __future__ import annotations

import dataclasses

from octoprobe.usb_tentacle.usb_tentacle import UsbTentacles


@dataclasses.dataclass
class Query:
    poweron: bool
    ids: set[str] = dataclasses.field(default_factory=set)

    def print(self) -> None:
        usb_tentacles = UsbTentacles.query(poweron=self.poweron)
        for usb_tentacle in usb_tentacles:
            print(usb_tentacle.short)
