import pytest

from app.marketdata.yahoo_provider import YahooPriceProvider


@pytest.mark.integration
def test_yahoo_price_provider_returns_quote():
    provider = YahooPriceProvider()

    quote = provider.get_quote("NVDA")

    assert quote.symbol == "NVDA"
    assert quote.price > 0
    assert quote.currency == "USD"
    assert quote.source == "yahoo"