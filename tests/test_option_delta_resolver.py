from datetime import date

from app.analysis.option_delta_resolver import OptionDeltaResolver
from app.marketdata.models import OptionQuote


def test_prefers_provider_delta():
    quote = OptionQuote(
        symbol="GS", expiration=date(2026, 7, 17), strike=1095,
        option_type="call", delta=0.77, implied_volatility=0.50,
    )
    assert OptionDeltaResolver().resolve(
        quote, underlying_price=1152, days_to_expiration=1
    ) == 0.77


def test_calculates_delta_from_provider_iv_when_delta_missing():
    quote = OptionQuote(
        symbol="GS", expiration=date(2026, 7, 17), strike=1095,
        option_type="call", implied_volatility=0.50,
    )
    delta = OptionDeltaResolver().resolve(
        quote, underlying_price=1152, days_to_expiration=1
    )
    assert delta is not None
    assert 0.5 < delta < 1.0


def test_treats_nan_delta_as_missing_and_uses_provider_iv():
    quote = OptionQuote(
        symbol="GS", expiration=date(2026, 7, 17), strike=1095,
        option_type="call", delta=float("nan"), implied_volatility=0.50,
    )
    delta = OptionDeltaResolver().resolve(
        quote, underlying_price=1152, days_to_expiration=1
    )
    assert delta is not None
    assert 0.5 < delta < 1.0


def test_derives_delta_from_current_option_price_when_delta_and_iv_are_nan():
    quote = OptionQuote(
        symbol="GS", expiration=date(2026, 7, 17), strike=1095,
        option_type="call", bid=60.0, ask=63.0,
        delta=float("nan"), implied_volatility=float("nan"),
    )
    delta = OptionDeltaResolver().resolve(
        quote, underlying_price=1152.07, days_to_expiration=1
    )
    assert delta is not None
    assert 0.5 < delta <= 1.0


def test_returns_none_when_no_finite_delta_iv_or_price_exists():
    quote = OptionQuote(
        symbol="GS", expiration=date(2026, 7, 17), strike=1095,
        option_type="call", bid=float("nan"), ask=float("nan"),
        last=float("nan"), delta=float("nan"),
        implied_volatility=float("nan"),
    )
    assert OptionDeltaResolver().resolve(
        quote, underlying_price=1152.07, days_to_expiration=1
    ) is None
