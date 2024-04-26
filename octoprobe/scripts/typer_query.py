from __future__ import annotations

import dataclasses

from octoprobe import util_usb_serial


@dataclasses.dataclass
class Query:
    verbose: bool
    ids: set[str] = dataclasses.field(default_factory=set)

    def print(self) -> None:
        result = util_usb_serial.QueryResultTentacle.query(verbose=self.verbose)
        for r in result:
            print(r.short)
