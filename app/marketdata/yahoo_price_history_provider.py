from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pandas as pd

from app.marketdata.price_history_provider import DailyBar, PriceHistoryProvider


DownloadFunction = Callable[..., pd.DataFrame]


class YahooPriceHistoryProvider(PriceHistoryProvider):
    """Load historical daily OHLCV bars from Yahoo Finance.

    This provider is intentionally limited to underlying-price reviews. It
    does not provide historical option chains or option prices.
    """

    def __init__(self, downloader: DownloadFunction | None = None) -> None:
        self._downloader = downloader

    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[DailyBar, ...]:
        if end_date < start_date:
            raise ValueError("end_date must not be before start_date")

        frame = self._download(
            symbol.upper(),
            start=start_date.isoformat(),
            # yfinance treats end as exclusive.
            end=(end_date + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            progress=False,
            actions=False,
            threads=False,
        )

        if frame is None or frame.empty:
            return ()

        frame = self._normalize_columns(frame)
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(frame.columns):
            return ()

        bars: list[DailyBar] = []
        for index, row in frame.sort_index().iterrows():
            bar_date = pd.Timestamp(index).date()
            if not start_date <= bar_date <= end_date:
                continue
            if any(pd.isna(row[name]) for name in ("Open", "High", "Low", "Close")):
                continue

            volume = 0 if pd.isna(row["Volume"]) else int(row["Volume"])
            bars.append(
                DailyBar(
                    date=bar_date,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=volume,
                )
            )
        return tuple(bars)

    def _download(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        if self._downloader is not None:
            return self._downloader(*args, **kwargs)

        import yfinance as yf

        return yf.download(*args, **kwargs)

    @staticmethod
    def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(frame.columns, pd.MultiIndex):
            return frame

        normalized = frame.copy()
        price_names = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
        if set(normalized.columns.get_level_values(0)).intersection(price_names):
            normalized.columns = normalized.columns.get_level_values(0)
        else:
            normalized.columns = normalized.columns.get_level_values(-1)
        return normalized
