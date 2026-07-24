from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.analysis.assignment_backtest import CoveredCallSale
from app.marketdata.models import ExpirationChain


class CurrentOptionChainProvider(Protocol):
    def get_expiration_dates(self, symbol: str) -> list[date]: ...

    def get_expiration_chain(
        self,
        symbol: str,
        expiration: date,
    ) -> ExpirationChain | None: ...


@dataclass(frozen=True, slots=True)
class CurrentCoveredCallOpportunity:
    symbol: str
    quote_date: date
    expiration_date: date
    strike: float
    bid_per_share: float
    ask_per_share: float | None
    delta: float
    open_interest: int | None
    volume: int | None

    def to_sale(self) -> CoveredCallSale:
        return CoveredCallSale(
            sale_date=self.quote_date,
            expiration_date=self.expiration_date,
            strike=self.strike,
            premium_per_share=self.bid_per_share,
            delta=self.delta,
        )


class CurrentCoveredCallOpportunityFinder:
    """Select a currently sellable covered call from OptionStrat data.

    The bid is used as the conservative executable premium. These quotes are a
    current decision input and must never be stored as historical premiums for
    an earlier trade date.
    """

    def __init__(self, provider: CurrentOptionChainProvider) -> None:
        self._provider = provider

    def find(
        self,
        *,
        symbol: str,
        quote_date: date,
        minimum_expiration: date,
        target_delta: float = 0.25,
        minimum_strike: float | None = None,
    ) -> CurrentCoveredCallOpportunity | None:
        if not 0 < target_delta < 1:
            raise ValueError("target_delta must be between zero and one")
        if minimum_strike is not None and minimum_strike <= 0:
            raise ValueError("minimum_strike must be greater than zero")

        expirations = sorted(
            expiration
            for expiration in self._provider.get_expiration_dates(symbol)
            if expiration >= minimum_expiration
        )
        for expiration in expirations:
            chain = self._provider.get_expiration_chain(symbol, expiration)
            if chain is None:
                continue
            candidates = [
                quote
                for quote in chain.quotes
                if quote.option_type == "call"
                and quote.bid is not None
                and quote.bid > 0
                and quote.delta is not None
                and 0 <= quote.delta <= 1
                and (minimum_strike is None or quote.strike >= minimum_strike)
            ]
            if not candidates:
                continue

            selected = min(
                candidates,
                key=lambda quote: (
                    abs((quote.delta or 0.0) - target_delta),
                    quote.bid_ask_spread_percent
                    if quote.bid_ask_spread_percent is not None
                    else float("inf"),
                    -(quote.open_interest or 0),
                    quote.strike,
                ),
            )
            return CurrentCoveredCallOpportunity(
                symbol=symbol.upper(),
                quote_date=quote_date,
                expiration_date=expiration,
                strike=selected.strike,
                bid_per_share=selected.bid or 0.0,
                ask_per_share=selected.ask,
                delta=selected.delta or 0.0,
                open_interest=selected.open_interest,
                volume=selected.volume,
            )
        return None
