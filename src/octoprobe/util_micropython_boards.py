"""
The micropython build system knows
    * port: Example 'stm32'
    * board: Example 'PYBV11'
    * variants: Example '', 'DP', 'THREAD', 'THREAD-DP'

    Convetion in octoprobe-testbed_tentacles:
    * A board ALWAYS contains a variant. Examples
    * 'PYBV11': board 'PYBV11', variant ''
    * 'PYBV11-DP': board 'PYBV11', variant 'DP'

This python module handles this logic.
"""

from __future__ import annotations

import dataclasses

BOARDS_SEPARATOR = ":"
"""
PYBV11:PYBV11-DP:PYBV11-THREAD:PYBV11-DP_THREAD
->
PYBV11
PYBV11-DP
PYBV11-THREAD
PYBV11-DP_THREAD
"""

VARIANT_SEPARATOR = "-"
"""
PYBV11_DP_THREAD
->
board: PYBV11
variant: DP_THREAD
"""


@dataclasses.dataclass(frozen=True, repr=True, eq=True)
class BoardVariant:
    board: str
    variant: str
    """
    Example: "" for default variant
    Example: "RISCV" for variant 'RISCV'
    """

    @staticmethod
    def factory(board_variant: str) -> BoardVariant:
        """
        Example 'board_variant': PYBV11-DP
        """
        assert isinstance(board_variant, str)
        board, _, variant = board_variant.partition(VARIANT_SEPARATOR)
        return BoardVariant(board=board, variant=variant)

    @property
    def name_normalized(self) -> str:
        if self.variant == "":
            return self.board
        return f"{self.board}{VARIANT_SEPARATOR}{self.variant}"


def board_variants(boards: str) -> list[BoardVariant]:
    """
    boards are separated by a ':'

    Example boards:
      * PYBV11:PYBV11-DP:PYBV11-THREAD:PYBV11-DP_THREAD
      * PYBV11
    """
    return [BoardVariant.factory(i) for i in boards.split(BOARDS_SEPARATOR)]
