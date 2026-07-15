from app.analysis.liquidity_rating import LiquidityRating
from app.analysis.trade_score import TradeScoreCalculator


def test_full_liquidity_receives_all_liquidity_points():
    score = TradeScoreCalculator().calculate(
        expected_move_percent=6.0,
        used_put_target_percent=-7.5,
        used_call_target_percent=7.5,
        put_reached_probability=0.10,
        call_reached_probability=0.10,
        put_finish_outside_probability=0.05,
        call_finish_outside_probability=0.05,
        historical_sample_size=40,
        liquidity=LiquidityRating(0.05, 1000, 100),
    )

    assert score.total == 98
    assert score.market_component == 35.0
    assert score.historical_risk_component == 22.5
    assert score.historical_sample_component == 10.0
    assert score.liquidity_component == 30.0


def test_missing_history_does_not_invent_historical_points():
    score = TradeScoreCalculator().calculate(
        expected_move_percent=5.0,
        used_put_target_percent=-5.0,
        used_call_target_percent=5.0,
        put_reached_probability=None,
        call_reached_probability=None,
        put_finish_outside_probability=None,
        call_finish_outside_probability=None,
        historical_sample_size=None,
        liquidity=LiquidityRating(0.05, 1000, 100),
    )

    assert score.historical_risk_component == 0.0
    assert score.historical_sample_component == 0.0
    assert score.total == 58


def test_partial_liquidity_scores_only_passed_checks():
    score = TradeScoreCalculator().calculate(
        expected_move_percent=5.0,
        used_put_target_percent=-5.0,
        used_call_target_percent=5.0,
        put_reached_probability=0.20,
        call_reached_probability=0.20,
        put_finish_outside_probability=0.10,
        call_finish_outside_probability=0.10,
        historical_sample_size=20,
        liquidity=LiquidityRating(0.20, 600, 10),
    )

    assert score.liquidity_component == 10.0
