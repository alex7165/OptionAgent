from datetime import date

from app.marketdata.models import OptionChain, OptionContract, EarningsEvent
from app.marketdata.dummy_provider import DummyStockDataProvider
from app.marketdata.service import MarketDataService


def test_market_data_service_returns_stock_data():
    provider = DummyStockDataProvider()
    market_data = MarketDataService(provider)

    stock = market_data.get_stock("nvda")

    assert stock.symbol == "NVDA"
    assert stock.price == 100.0
    assert stock.currency == "USD"
    assert stock.source == "dummy"

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