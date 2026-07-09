from datetime import date

from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer
from app.marketdata.models import ExpirationChain, OptionQuote


def test_skips_nan_quotes_when_calculating_expected_move():
    chain = ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 10),
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="call",
                bid="NaN",
                ask="NaN",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=195,
                option_type="put",
                bid="NaN",
                ask="NaN",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="call",
                bid=2.0,
                ask=2.2,
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=date(2026, 7, 10),
                strike=200,
                option_type="put",
                bid=1.8,
                ask=2.0,
            ),
        ],
    )

    move = ExpectedMoveAnalyzer().from_atm_straddle(
        chain,
        underlying_price=198,
    )

    assert move is not None
    assert round(move.percent, 4) == round((2.1 + 1.9) / 198, 4)