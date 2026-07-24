import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from app.marketdata.massive_client import MassiveClient
from app.marketdata.price_history_provider import (
    DailyBar,
    PriceHistoryProvider,
)


class MassivePriceHistoryProvider(PriceHistoryProvider):

    DEFAULT_CACHE_DIR = Path("data/history_cache/massive")

    def __init__(
        self,
        client: MassiveClient | None = None,
        api_key: str | None = None,
        cache_dir: str | Path | None = None,
        request_interval_seconds: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client or MassiveClient(api_key=api_key)
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        configured_interval = (
            request_interval_seconds
            if request_interval_seconds is not None
            else float(
                os.getenv(
                    "MASSIVE_REQUEST_INTERVAL_SECONDS",
                    "12.5",
                )
            )
        )
        if configured_interval < 0:
            raise ValueError(
                "request_interval_seconds must not be negative"
            )
        self.request_interval_seconds = configured_interval
        self.sleep = sleep
        self.monotonic = monotonic
        self._last_request_started_at: float | None = None

    def get_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[DailyBar, ...]:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        if start_date > end_date:
            raise ValueError(
                "start_date must be before or equal to end_date"
            )

        cache_path = self._cache_path(
            symbol=normalized_symbol,
            start_date=start_date,
            end_date=end_date,
        )
        cached_payload = self._read_cache(cache_path)

        if cached_payload is not None:
            return self._parse_payload(cached_payload)

        path = (
            f"/v2/aggs/ticker/{normalized_symbol}/range/1/day/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )

        self._wait_before_request()

        payload = self.client.get(
            path=path,
            params={
                "adjusted": "false",
                "sort": "asc",
                "limit": 50_000,
            },
        )

        bars = self._parse_payload(payload)
        self._write_cache(cache_path, payload)
        return bars


    def warm_cache(
        self,
        requests: Iterable[tuple[str, date, date]],
    ) -> None:
        for symbol, start_date, end_date in requests:
            normalized_symbol = symbol.strip().upper()
            cache_path = self._cache_path(
                symbol=normalized_symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if self._read_cache(cache_path) is not None:
                continue

            self.get_daily_bars(
                symbol=normalized_symbol,
                start_date=start_date,
                end_date=end_date,
            )

    def _wait_before_request(self) -> None:
        now = self.monotonic()

        if self._last_request_started_at is not None:
            elapsed = now - self._last_request_started_at
            remaining = self.request_interval_seconds - elapsed
            if remaining > 0:
                self.sleep(remaining)
                now = self.monotonic()

        self._last_request_started_at = now

    def _cache_path(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> Path:
        filename = (
            f"{symbol}_{start_date.isoformat()}_"
            f"{end_date.isoformat()}.json"
        )
        return self.cache_dir / filename

    @staticmethod
    def _read_cache(cache_path: Path) -> dict[str, Any] | None:
        if not cache_path.exists():
            return None

        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    @staticmethod
    def _write_cache(
        cache_path: Path,
        payload: dict[str, Any],
    ) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = cache_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(cache_path)

    def _parse_payload(
        self,
        payload: dict[str, Any],
    ) -> tuple[DailyBar, ...]:
        results = payload.get("results", [])

        if not isinstance(results, list):
            raise ValueError(
                "Massive API returned invalid daily bar results"
            )

        return tuple(
            self._parse_daily_bar(item)
            for item in results
        )

    @staticmethod
    def _parse_daily_bar(
        item: dict[str, Any],
    ) -> DailyBar:
        timestamp = int(item["t"])

        bar_date = datetime.fromtimestamp(
            timestamp / 1000,
            tz=timezone.utc,
        ).date()

        return DailyBar(
            date=bar_date,
            open=float(item["o"]),
            high=float(item["h"]),
            low=float(item["l"]),
            close=float(item["c"]),
            volume=int(item["v"]),
        )
