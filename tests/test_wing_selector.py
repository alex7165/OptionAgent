from datetime import date

from app.analysis.wing_selector import WingSelector
from app.marketdata.models import ExpirationChain, OptionQuote


def test_select_long_put_by_width():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=160,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=165,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=170,
                option_type="put",
            ),
        ],
    )

    short_put = OptionQuote(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        strike=170,
        option_type="put",
    )

    selector = WingSelector()

    long_put = selector.select_long_put(
        chain,
        short_put,
        width=5,
    )

    assert long_put.strike == 165


def test_select_long_call_by_width():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=215,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=220,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=225,
                option_type="call",
            ),
        ],
    )

    short_call = OptionQuote(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        strike=215,
        option_type="call",
    )

    selector = WingSelector()

    long_call = selector.select_long_call(
        chain,
        short_call,
        width=5,
    )

    assert long_call.strike == 220

def test_width_for_price():
    selector = WingSelector()

    assert selector.width_for_price(40) == 2.5
    assert selector.width_for_price(100) == 5
    assert selector.width_for_price(200) == 10
    assert selector.width_for_price(400) == 20