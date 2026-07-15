from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.analysis.strike_selection import StrikeSelection
from app.marketdata.price_history_provider import DailyBar


class RepairSide(str, Enum):
    PUT = "put"
    CALL = "call"


@dataclass(frozen=True, slots=True)
class RepairStrategyOutcome:
    triggered: bool
    trigger_day_index: int | None
    trigger_date: date | None
    threatened_side: RepairSide | None
    original_strike: float | None
    repaired_strike: float | None
    repaired_strike_touched: bool | None
    repaired_strike_finished_outside: bool | None
    observations: tuple[str, ...]


class RepairStrategyBacktestAnalyzer:
    """Underlying-only repair simulation without invented option P&L.

    At the first touch, the threatened short strike is shifted outward by a
    configurable percentage of the pre-earnings reference price. The result
    only states whether that hypothetical outer level later held.
    """

    def __init__(self, outward_buffer_percent: float = 2.5) -> None:
        if outward_buffer_percent <= 0:
            raise ValueError("outward_buffer_percent must be greater than zero")
        self.outward_buffer_percent = outward_buffer_percent

    def analyze(
        self,
        selection: StrikeSelection,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
    ) -> RepairStrategyOutcome:
        if reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")
        if selection.put is None or selection.call is None:
            raise ValueError("selection must contain short put and short call")

        trigger = self._first_touch(selection, daily_bars)
        if trigger is None:
            return RepairStrategyOutcome(
                triggered=False,
                trigger_day_index=None,
                trigger_date=None,
                threatened_side=None,
                original_strike=None,
                repaired_strike=None,
                repaired_strike_touched=None,
                repaired_strike_finished_outside=None,
                observations=("Keine Reparatur ausgelöst: kein Short-Strike berührt.",),
            )

        index, side = trigger
        original = selection.put.strike if side is RepairSide.PUT else selection.call.strike
        shift = reference_price * self.outward_buffer_percent / 100
        repaired = original - shift if side is RepairSide.PUT else original + shift
        remaining = daily_bars[index:]
        if side is RepairSide.PUT:
            touched = any(bar.low <= repaired for bar in remaining)
            outside = remaining[-1].close < repaired
        else:
            touched = any(bar.high >= repaired for bar in remaining)
            outside = remaining[-1].close > repaired

        return RepairStrategyOutcome(
            triggered=True,
            trigger_day_index=index + 1,
            trigger_date=daily_bars[index].date,
            threatened_side=side,
            original_strike=original,
            repaired_strike=repaired,
            repaired_strike_touched=touched,
            repaired_strike_finished_outside=outside,
            observations=(
                "Reparatur ist eine Underlying-Simulation ohne Options-P&L.",
                f"Bedrohte {side.value}-Seite wurde um {self.outward_buffer_percent:.2f} % des Referenzkurses nach außen verschoben.",
            ),
        )

    @staticmethod
    def _first_touch(
        selection: StrikeSelection,
        bars: tuple[DailyBar, ...],
    ) -> tuple[int, RepairSide] | None:
        for index, bar in enumerate(bars):
            put_touch = bar.low <= selection.put.strike
            call_touch = bar.high >= selection.call.strike
            if put_touch and call_touch:
                put_distance = selection.put.strike - bar.low
                call_distance = bar.high - selection.call.strike
                return (index, RepairSide.PUT if put_distance >= call_distance else RepairSide.CALL)
            if put_touch:
                return index, RepairSide.PUT
            if call_touch:
                return index, RepairSide.CALL
        return None
