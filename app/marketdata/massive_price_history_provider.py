from datetime import date, datetime, timezone
from typing import Any

from app.marketdata.massive_client import MassiveClient
from app.marketdata.price_history_provider import (
    DailyBar,
    PriceHistoryProvider,
)


class MassivePriceHistoryProvider(PriceHistoryProvider):

    def __init__(
        self,
        client: MassiveClient | None = None,
        api_key: str | None = None,
    ) -> None:
        self.client = client or MassiveClient(api_key=api_key)

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

        path = (
            f"/v2/aggs/ticker/{normalized_symbol}/range/1/day/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )

        payload = self.client.get(
            path=path,
            params={
                "adjusted": "false",
                "sort": "asc",
                "limit": 50_000,
            },
        )

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