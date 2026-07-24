from __future__ import annotations

from enum import StrEnum


class ThreatenedSide(StrEnum):
    PUT = "put"
    CALL = "call"


class ManagementAction(StrEnum):
    """Supported actions after a short strike is threatened or violated."""

    HOLD = "hold"
    CLOSE = "close"
    ROLL_CALL = "roll_call"
    BUY_STOCK_HEDGE = "buy_stock_hedge"
    HOLD_FOR_ASSIGNMENT = "hold_for_assignment"
    ROLL_PUT = "roll_put"
    ASSIGN_AND_SELL_COVERED_CALL = "assign_and_sell_covered_call"

    @classmethod
    def allowed_for_side(
        cls,
        side: ThreatenedSide,
    ) -> tuple[ManagementAction, ...]:
        if side is ThreatenedSide.CALL:
            return (
                cls.HOLD,
                cls.ROLL_CALL,
                cls.BUY_STOCK_HEDGE,
                cls.CLOSE,
            )
        return (
            cls.HOLD_FOR_ASSIGNMENT,
            cls.ROLL_PUT,
            cls.ASSIGN_AND_SELL_COVERED_CALL,
            cls.CLOSE,
        )
