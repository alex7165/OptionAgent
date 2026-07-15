from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.marketdata.models import EarningsEvent


@dataclass(frozen=True, slots=True)
class DailyTradeWindow:
    trade_date: date
    next_trading_date: date
    events: tuple[EarningsEvent, ...]


class DailyTradeWindowSelector:
    """Select AMC events today and BMO events on the next trading weekday."""

    AFTER_MARKET_CLOSE = {
        "after market close", "after market", "amc", "after close"
    }
    BEFORE_MARKET_OPEN = {
        "before market open", "before market", "bmo", "before open"
    }

    def select(
        self,
        events: list[EarningsEvent] | tuple[EarningsEvent, ...],
        trade_date: date,
    ) -> DailyTradeWindow:
        next_date = self.next_trading_weekday(trade_date)
        selected = tuple(
            sorted(
                (
                    event
                    for event in events
                    if self._is_selected(event, trade_date, next_date)
                ),
                key=lambda event: event.symbol,
            )
        )
        return DailyTradeWindow(
            trade_date=trade_date,
            next_trading_date=next_date,
            events=selected,
        )

    @staticmethod
    def next_trading_weekday(current: date) -> date:
        candidate = current + timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)
        return candidate

    def _is_selected(
        self,
        event: EarningsEvent,
        trade_date: date,
        next_date: date,
    ) -> bool:
        timing = self._normalize(event.timing)
        return (
            event.report_date == trade_date
            and timing in self.AFTER_MARKET_CLOSE
        ) or (
            event.report_date == next_date
            and timing in self.BEFORE_MARKET_OPEN
        )

    @staticmethod
    def _normalize(value: str | None) -> str:
        return " ".join((value or "").strip().lower().split())
