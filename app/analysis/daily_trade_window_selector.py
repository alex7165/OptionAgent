from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
import re

from app.marketdata.models import EarningsEvent


@dataclass(frozen=True, slots=True)
class DailyTradeWindow:
    trade_date: date
    next_trading_date: date
    events: tuple[EarningsEvent, ...]


class DailyTradeWindowSelector:
    """Select today's AMC events and the next trading day's BMO events."""

    AFTER_MARKET_CLOSE = {
        "after market close",
        "after market",
        "after close",
        "after hours",
        "post market",
        "postmarket",
        "amc",
    }
    BEFORE_MARKET_OPEN = {
        "before market open",
        "before market",
        "before open",
        "pre market",
        "premarket",
        "bmo",
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
        normalized_timing = self._normalize(event.timing)
        reported_time = self._parse_time(event.timing)

        is_after_market_close = (
            normalized_timing in self.AFTER_MARKET_CLOSE
            or (reported_time is not None and reported_time >= time(16, 0))
        )
        is_before_market_open = (
            normalized_timing in self.BEFORE_MARKET_OPEN
            or (reported_time is not None and reported_time < time(9, 30))
        )

        return (
            event.report_date == trade_date and is_after_market_close
        ) or (
            event.report_date == next_date and is_before_market_open
        )

    @staticmethod
    def _normalize(value: str | None) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower())
        return " ".join(normalized.split())

    @staticmethod
    def _parse_time(value: str | None) -> time | None:
        raw = (value or "").strip()
        if not raw:
            return None

        for format_string in ("%H:%M:%S", "%H:%M"):
            try:
                from datetime import datetime

                return datetime.strptime(raw, format_string).time()
            except ValueError:
                continue

        return None
