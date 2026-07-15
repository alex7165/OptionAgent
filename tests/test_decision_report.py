from datetime import date

from app.analysis.decision_report import DecisionReportBuilder
from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_outcome_analyzer import HistoricalOutcome
from app.analysis.historical_strike_risk_analyzer import StrikeSide
from app.analysis.historical_strike_risk_grid_analyzer import HistoricalStrikeRiskGrid
from app.analysis.historical_strike_selection_service import HistoricalStrikeSelectionResult
from app.analysis.liquidity_rating import LiquidityRating
from app.analysis.historical_strike_selector import (
    HistoricalStrikeRecommendation,
    HistoricalStrikeSelection,
    HistoricalStrikeSelectionReason,
)
from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import EarningsEvent, MarketSnapshot, OptionQuote, Quote


def _option(option_type: str, strike: float) -> OptionQuote:
    return OptionQuote(
        symbol="GS",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=1.0,
        ask=1.1,
        volume=100,
        open_interest=1000,
    )


def _candidate() -> EarningsCrushCandidate:
    selection = StrikeSelection(
        put=_option("put", 94),
        call=_option("call", 107),
        put_target=94,
        call_target=107,
        strategy=Strategy.SHORT_STRANGLE,
    )
    return EarningsCrushCandidate(
        earnings_event=EarningsEvent("GS", date(2026, 7, 16)),
        snapshot=MarketSnapshot(
            symbol="GS",
            quote=Quote("GS", 100.0, "USD", "test"),
        ),
        expected_move=ExpectedMove(0.06, 106.0, 94.0),
        strike_selection=selection,
        strike_selection_before_liquidity=selection,
        strike_selection_source=StrikeSelectionSource.EXPECTED_MOVE,
    )


def _recommendation(side: StrikeSide, threshold: float):
    return HistoricalStrikeRecommendation(
        side=side,
        recommended_threshold_percent=threshold,
        expected_move_threshold_percent=(6.0 if side is StrikeSide.CALL else -6.0),
        adjustment_from_expected_move=(threshold - 6.0 if side is StrikeSide.CALL else threshold + 6.0),
        finish_outside_probability=0.05,
        reached_probability=0.10,
        exit_trading_day_index=2,
        observation_count=3,
        reason=HistoricalStrikeSelectionReason.ADJUSTED_OUTWARD,
    )


def test_builds_expected_move_fallback_report():
    report = DecisionReportBuilder().build(_candidate())

    assert report is not None
    assert report.expected_move_percent == 6.0
    assert report.put_target_basis == "Expected Move"
    assert report.call_target_basis == "Expected Move"
    assert report.historical_sample_size is None


def test_compares_current_expected_move_with_historical_moves():
    candidate = _candidate()
    candidate.strike_selection_source = StrikeSelectionSource.HISTORICAL
    candidate.historical_selection_result = HistoricalStrikeSelectionResult(
        outcomes=(
            HistoricalOutcome(2, date(2026, 1, 2), 4.0, 5.0, -2.0, 2),
            HistoricalOutcome(2, date(2026, 4, 2), -8.0, 3.0, -9.0, 2),
            HistoricalOutcome(2, date(2026, 7, 2), 2.0, 4.0, -1.0, 2),
        ),
        risk_grid=HistoricalStrikeRiskGrid(call_risks=(), put_risks=()),
        selection=HistoricalStrikeSelection(
            expected_move_percent=6.0,
            call_recommendation=_recommendation(StrikeSide.CALL, 7.0),
            put_recommendation=_recommendation(StrikeSide.PUT, -6.0),
        ),
    )

    report = DecisionReportBuilder().build(candidate)

    assert report is not None
    assert report.historical_average_abs_close_move_percent == 14 / 3
    assert report.historical_median_abs_close_move_percent == 4.0
    assert report.historical_max_abs_close_move_percent == 8.0
    assert report.call_target_basis == "Historie"
    assert report.put_target_basis == "Expected Move"
    assert report.exit_trading_day_index == 2


def test_trade_score_uses_market_history_sample_and_liquidity():
    candidate = _candidate()
    candidate.strike_selection_source = StrikeSelectionSource.HISTORICAL
    candidate.liquidity = LiquidityRating(
        spread_percent=0.05,
        open_interest=1200,
        volume=200,
    )
    candidate.historical_selection_result = HistoricalStrikeSelectionResult(
        outcomes=(
            HistoricalOutcome(2, date(2026, 1, 2), 4.0, 5.0, -2.0, 2),
            HistoricalOutcome(2, date(2026, 4, 2), -8.0, 3.0, -9.0, 2),
            HistoricalOutcome(2, date(2026, 7, 2), 2.0, 4.0, -1.0, 2),
        ),
        risk_grid=HistoricalStrikeRiskGrid(call_risks=(), put_risks=()),
        selection=HistoricalStrikeSelection(
            expected_move_percent=6.0,
            call_recommendation=_recommendation(StrikeSide.CALL, 7.0),
            put_recommendation=_recommendation(StrikeSide.PUT, -6.0),
        ),
    )

    report = DecisionReportBuilder().build(candidate)

    assert report is not None
    assert 0 <= report.trade_score.total <= 100
    assert report.trade_score.market_component > 0
    assert report.trade_score.historical_risk_component > 0
    assert report.trade_score.historical_sample_component > 0
    assert report.trade_score.liquidity_component == 30.0
