from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Protocol

import pandas as pd


class HistoricalEarningsDateProvider(Protocol):
    def get_report_dates(self, symbol: str) -> tuple[date, ...]: ...


EarningsDatesLoader = Callable[[str], Any]


class YahooHistoricalEarningsDateProvider:
    """Load historical earnings dates from Yahoo Finance.

    This provider is used only to identify prior earnings events for trade
    management research. It does not replace the Earnings API used by the
    entry-analysis workflow.
    """

    def __init__(
        self,
        loader: EarningsDatesLoader | None = None,
        limit: int = 40,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be at least one")
        self._loader = loader
        self.limit = limit

    def get_report_dates(self, symbol: str) -> tuple[date, ...]:
        raw = self._load(symbol.upper())
        if raw is None:
            return ()

        if isinstance(raw, pd.DataFrame):
            values = raw.index
        else:
            values = raw

        dates: set[date] = set()
        for value in values:
            parsed = self._to_date(value)
            if parsed is not None:
                dates.add(parsed)
        return tuple(sorted(dates))

    def _load(self, symbol: str) -> Any:
        if self._loader is not None:
            return self._loader(symbol)

        import yfinance as yf

        return yf.Ticker(symbol).get_earnings_dates(limit=self.limit)

    @staticmethod
    def _to_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return pd.Timestamp(value).date()
        except (TypeError, ValueError):
            return None
