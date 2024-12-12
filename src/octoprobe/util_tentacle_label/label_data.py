"""
Tentacle Label Data
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class LabelData:
    serial: str = ""
    "2d2e"
    tentacle_tag: str = ""
    "ESP828266_GENERIC"
    tentacle_type: str = ""
    "MCU"
    description: str = ""
    "esp8266"
    testbed_name: str = ""
    "testbed_micropython"
    testbed_instance: str = ""
    "au_damien_1"


class LabelsData(list[LabelData]):
    pass
