import os
from dataclasses import dataclass
from datetime import date

import requests


@dataclass(frozen=True, slots=True)
class EarningsReactionDay:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    price_change_percent: float


@dataclass(frozen=True, slots=True)
class HistoricalEarningsReaction:
    report_date: date
    symbol: str
    eps_surprise_percent: float | None
    eps_yoy_percent: float | None
    eps_beat: bool | None
    revenue_surprise_percent: float | None
    revenue_yoy_percent: float | None
    revenue_beat: bool | None
    reactions: tuple[EarningsReactionDay, ...]


class EarningsApiProvider:

    API_URL = "https://api.earningsapi.com/v1/earnings-reactions"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("EARNINGS_API_KEY")

        if not self.api_key:
            raise ValueError("EARNINGS_API_KEY is not configured")

    def get_historical_reactions(
        self,
        symbol: str,
    ) -> tuple[HistoricalEarningsReaction, ...]:
        response = requests.get(
            self.API_URL,
            params={
                "symbol": symbol.upper(),
                "apikey": self.api_key,
            },
            timeout=30,
        )
        response.raise_for_status()

        return tuple(
            self._parse_reaction(item)
            for item in response.json()
        )

    def _parse_reaction(
        self,
        item: dict,
    ) -> HistoricalEarningsReaction:
        eps = item.get("eps") or {}
        revenue = item.get("revenue") or {}

        return HistoricalEarningsReaction(
            report_date=date.fromisoformat(item["date"]),
            symbol=item["symbol"],
            eps_surprise_percent=eps.get("surprisePercent"),
            eps_yoy_percent=eps.get("yoy"),
            eps_beat=eps.get("beat"),
            revenue_surprise_percent=revenue.get("surprisePercent"),
            revenue_yoy_percent=revenue.get("yoy"),
            revenue_beat=revenue.get("beat"),
            reactions=tuple(
                EarningsReactionDay(
                    date=date.fromisoformat(reaction["date"]),
                    open=float(reaction["open"]),
                    high=float(reaction["high"]),
                    low=float(reaction["low"]),
                    close=float(reaction["close"]),
                    volume=int(reaction["volume"]),
                    price_change_percent=float(
                        reaction["priceChange"]
                    ),
                )
                for reaction in item.get("reactions", [])
            ),
        )