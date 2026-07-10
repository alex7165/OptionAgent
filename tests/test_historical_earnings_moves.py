from app.analysis.historical_earnings_moves import (
    HistoricalEarningsMove,
    HistoricalEarningsMoves,
)


def test_calculates_historical_earnings_statistics():
    history = HistoricalEarningsMoves(
        moves=(
            HistoricalEarningsMove(move_percent=8.0),
            HistoricalEarningsMove(move_percent=-6.0),
            HistoricalEarningsMove(move_percent=34.0),
            HistoricalEarningsMove(move_percent=-12.0),
        )
    )

    assert history.average_absolute_move_percent == 15.0
    assert history.median_absolute_move_percent == 10.0
    assert history.maximum_up_move_percent == 34.0
    assert history.maximum_down_move_percent == -12.0
    assert history.maximum_absolute_move_percent == 34.0
    assert history.moves_over_20_percent == 1
    assert history.moves_over_30_percent == 1
    assert history.is_upside_skewed is True
    assert history.is_downside_skewed is False


def test_detects_downside_skew():
    history = HistoricalEarningsMoves(
        moves=(
            HistoricalEarningsMove(move_percent=11.0),
            HistoricalEarningsMove(move_percent=-31.0),
            HistoricalEarningsMove(move_percent=-7.0),
        )
    )

    assert history.maximum_up_move_percent == 11.0
    assert history.maximum_down_move_percent == -31.0
    assert history.is_upside_skewed is False
    assert history.is_downside_skewed is True


def test_handles_empty_history():
    history = HistoricalEarningsMoves(moves=())

    assert history.maximum_up_move_percent == 0.0
    assert history.maximum_down_move_percent == 0.0
    assert history.maximum_absolute_move_percent == 0.0
    assert history.moves_over_20_percent == 0
    assert history.moves_over_30_percent == 0