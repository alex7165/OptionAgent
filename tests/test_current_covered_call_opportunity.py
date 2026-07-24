from datetime import date

from app.analysis.current_covered_call_opportunity import (
    CurrentCoveredCallOpportunityFinder,
)
from app.marketdata.models import ExpirationChain, OptionQuote


class FakeOptionStratProvider:
    def get_expiration_dates(self, symbol: str) -> list[date]:
        return [date(2026, 7, 31), date(2026, 8, 7)]

    def get_expiration_chain(
        self,
        symbol: str,
        expiration: date,
    ) -> ExpirationChain | None:
        return ExpirationChain(
            symbol=symbol,
            expiration=expiration,
            quotes=[
                OptionQuote(
                    symbol=symbol,
                    expiration=expiration,
                    strike=13.0,
                    option_type="call",
                    bid=0.42,
                    ask=0.48,
                    delta=0.31,
                    open_interest=500,
                ),
                OptionQuote(
                    symbol=symbol,
                    expiration=expiration,
                    strike=13.5,
                    option_type="call",
                    bid=0.30,
                    ask=0.35,
                    delta=0.24,
                    open_interest=300,
                ),
            ],
        )


def test_selects_current_bid_nearest_target_delta() -> None:
    opportunity = CurrentCoveredCallOpportunityFinder(
        FakeOptionStratProvider()
    ).find(
        symbol="aci",
        quote_date=date(2026, 7, 27),
        minimum_expiration=date(2026, 7, 31),
        target_delta=0.25,
        minimum_strike=12.95,
    )

    assert opportunity is not None
    assert opportunity.symbol == "ACI"
    assert opportunity.strike == 13.5
    assert opportunity.bid_per_share == 0.30
    assert opportunity.delta == 0.24
    assert opportunity.to_sale().premium_per_share == 0.30


def test_returns_none_without_positive_bid() -> None:
    class NoBidProvider(FakeOptionStratProvider):
        def get_expiration_chain(self, symbol, expiration):
            return ExpirationChain(
                symbol=symbol,
                expiration=expiration,
                quotes=[
                    OptionQuote(
                        symbol=symbol,
                        expiration=expiration,
                        strike=13.5,
                        option_type="call",
                        bid=0.0,
                        ask=0.35,
                        delta=0.24,
                    )
                ],
            )

    opportunity = CurrentCoveredCallOpportunityFinder(NoBidProvider()).find(
        symbol="ACI",
        quote_date=date(2026, 7, 27),
        minimum_expiration=date(2026, 7, 31),
    )

    assert opportunity is None
