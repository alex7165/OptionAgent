from datetime import date

from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer
from app.marketdata.optionstrat_provider import OptionStratProvider
import pytest

pytest.mark.integration

def test_expected_move_from_real_option_chain():
    provider = OptionStratProvider()

    chain = provider.get_expiration_chain(
        "NVDA",
        date(2026, 7, 10),
    )

    analyzer = ExpectedMoveAnalyzer()

    move = analyzer.from_atm_straddle(
        chain,
        underlying_price=197.5,
    )

    assert move is not None
    assert move.percent > 0