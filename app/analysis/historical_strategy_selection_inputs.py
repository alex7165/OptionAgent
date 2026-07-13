from dataclasses import dataclass
from typing import Protocol

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelectionPolicy,
)


@dataclass(frozen=True, slots=True)
class HistoricalStrategySelectionInputs:
    price_analyses: tuple[HistoricalEarningsPriceAnalysis, ...]
    exit_trading_day_index: int
    call_thresholds: tuple[float, ...]
    put_thresholds: tuple[float, ...]
    policy: HistoricalStrikeSelectionPolicy


class HistoricalStrategySelectionInputsLoaderProtocol(Protocol):

    def load(
        self,
        symbol: str,
    ) -> HistoricalStrategySelectionInputs | None:
        ...
