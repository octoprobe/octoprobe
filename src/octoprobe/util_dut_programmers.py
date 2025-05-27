from __future__ import annotations

import logging
import typing

from .util_baseclasses import PropertyString
from .util_constants import TAG_PROGRAMMER
from .util_dut_programmer_abc import DutProgrammerABC

if typing.TYPE_CHECKING:
    pass


logger = logging.getLogger(__file__)


def _get_programmers() -> list[type[DutProgrammerABC]]:
    # pylint: disable=import-outside-toplevel
    from .util_mcu_esp import DutProgrammerEsptool
    from .util_mcu_mimxrt import DutProgrammerTeensyLoaderCli
    from .util_mcu_nrf import DutProgrammerBossac
    from .util_mcu_pico import DutProgrammerPicotool
    from .util_mcu_pyboard import DutProgrammerDfuUtil
    from .util_mcu_samd import (
        DutProgrammerSamdBossac,
        DutProgrammerSamdMountPointObsolete,
    )

    return [
        DutProgrammerBossac,
        DutProgrammerDfuUtil,
        DutProgrammerEsptool,
        DutProgrammerPicotool,
        DutProgrammerSamdMountPointObsolete,
        DutProgrammerSamdBossac,
        DutProgrammerTeensyLoaderCli,
    ]


def get_dict_programmers() -> dict[str, type[DutProgrammerABC]]:
    return {cls.LABEL: cls for cls in _get_programmers()}


def dut_programmer_factory(tags: str) -> DutProgrammerABC:
    """
    Example 'tags': programmer=picotool,xy=5
    """
    programmer = PropertyString(tags).get_tag_mandatory(TAG_PROGRAMMER)
    try:
        cls_programmer = get_dict_programmers()[programmer]
        return cls_programmer()
    except KeyError as e:
        raise ValueError(f"Unknown '{programmer}' in '{tags}'!") from e
