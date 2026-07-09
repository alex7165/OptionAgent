from datetime import date

from app.analysis.strike_selector import StrikeSelector
from app.marketdata.models import ExpirationChain, OptionQuote
from app.analysis.expected_move import ExpectedMove


def test_select_by_percent():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=170,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=175,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=210,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=215,
                option_type="call",
            ),
        ],
    )

    selector = StrikeSelector()

    selection = selector.select_by_percent(
        chain,
        underlying_price=192,
        percent=0.10,
    )

    assert selection.put.strike == 170
    assert selection.call.strike == 215

def test_select_by_expected_move():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=190,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=205,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=210,
                option_type="call",
            ),
        ],
    )

    expected_move = ExpectedMove(
        percent=0.03,
        down_price=193.5,
        up_price=206.5,
    )

    selector = StrikeSelector()

    selection = selector.select_by_expected_move(
        chain,
        expected_move,
    )

    assert selection.put.strike == 190
    assert selection.call.strike == 210