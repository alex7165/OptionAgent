from dataclasses import dataclass
from typing import Protocol

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)


class ReferencePriceResolver(Protocol):

    def resolve(
        self,
        price_series: HistoricalEarningsPriceSeries,
    ) -> float:
        ...


@dataclass(frozen=True, slots=True)
class FixedReferencePriceResolver:
    reference_price: float

    def resolve(
        self,
        price_series: HistoricalEarningsPriceSeries,
    ) -> float:
        return self.reference_price