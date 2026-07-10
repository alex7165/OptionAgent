from datetime import date

from app.analysis.historical_earnings_move_analyzer import (
    HistoricalEarningsMoveAnalyzer,
)
from app.marketdata.earnings_api_provider import (
    EarningsReactionDay,
    HistoricalEarningsReaction,
)


def test_creates_history_from_move_list():
    analyzer = HistoricalEarningsMoveAnalyzer()

    history = analyzer.analyze(
        [8.0, -6.0, 34.0, -12.0]
    )

    assert len(history.moves) == 4
    assert history.maximum_up_move_percent == 34.0
    assert history.maximum_down_move_percent == -12.0
    assert history.moves_over_30_percent == 1


def test_uses_first_reaction_day_as_earnings_move():
    analyzer = HistoricalEarningsMoveAnalyzer()

    reactions = (
        HistoricalEarningsReaction(
            report_date=date(2026, 4, 16),
            symbol="NFLX",
            eps_surprise_percent=-7.9,
            eps_yoy_percent=-89.4,
            eps_beat=False,
            revenue_surprise_percent=0.6,
            revenue_yoy_percent=16.2,
            revenue_beat=True,
            reactions=(
                EarningsReactionDay(
                    date=date(2026, 4, 17),
                    open=96.37,
                    high=98.74,
                    low=95.10,
                    close=97.31,
                    volume=125958732,
                    price_change_percent=-9.72,
                ),
                EarningsReactionDay(
                    date=date(2026, 4, 20),
                    open=97.14,
                    high=97.60,
                    low=93.54,
                    close=94.83,
                    volume=63298300,
                    price_change_percent=-2.55,
                ),
            ),
        ),
    )

    history = analyzer.analyze_reactions(reactions)

    assert len(history.moves) == 1
    assert history.moves[0].move_percent == -9.72