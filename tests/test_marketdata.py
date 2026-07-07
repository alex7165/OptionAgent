from app.marketdata.dummy_earnings_provider import DummyEarningsProvider
from datetime import date

from app.marketdata.dummy_provider import DummyPriceProvider
from app.marketdata.models import (
    EarningsEvent,
    OptionChain,
    OptionContract,
)
from app.marketdata.service import MarketDataService


def test_market_data_service_returns_snapshot():
    provider = DummyPriceProvider()
    market_data = MarketDataService(provider)

    snapshot = market_data.get_snapshot("nvda")

    assert snapshot.symbol == "NVDA"
    assert snapshot.quote is not None
    assert snapshot.quote.symbol == "NVDA"
    assert snapshot.quote.price == 100.0
    assert snapshot.quote.currency == "USD"
    assert snapshot.quote.source == "dummy"


def test_option_chain_model_contains_contracts():
    expiration = date(2026, 6, 19)

    contract = OptionContract(
        symbol="NVDA",
        expiration=expiration,
        strike=150.0,
        option_type="call",
        bid=2.5,
        ask=2.8,
        implied_volatility=0.45,
    )

    chain = OptionChain(
        symbol="NVDA",
        expiration=expiration,
        contracts=[contract],
    )

    assert chain.symbol == "NVDA"
    assert len(chain.contracts) == 1
    assert chain.contracts[0].option_type == "call"


def test_earnings_event_model():
    event = EarningsEvent(
        symbol="CRWD",
        report_date=date(2026, 8, 26),
        timing="after_close",
        source="dummy",
    )

    assert event.symbol == "CRWD"
    assert event.timing == "after_close"

def test_market_data_service_returns_earnings_event():
    price_provider = DummyPriceProvider()
    earnings_provider = DummyEarningsProvider()
    market_data = MarketDataService(price_provider, earnings_provider)

    snapshot = market_data.get_snapshot("nvda")

    assert snapshot.earnings is not None
    assert snapshot.earnings.symbol == "NVDA"
    assert snapshot.earnings.timing == "after market close"
    assert snapshot.earnings.source == "dummy"