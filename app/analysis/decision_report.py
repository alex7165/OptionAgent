from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.trade_score import TradeScore, TradeScoreCalculator


@dataclass(frozen=True, slots=True)
class DecisionReport:
    selection_source: StrikeSelectionSource
    expected_move_percent: float
    iv_rank: float | None
    iv_percentile: float | None
    historical_sample_size: int | None
    exit_trading_day_index: int | None
    historical_average_abs_close_move_percent: float | None
    historical_median_abs_close_move_percent: float | None
    historical_max_abs_close_move_percent: float | None
    historical_put_target_percent: float | None
    historical_call_target_percent: float | None
    used_put_target_percent: float
    used_call_target_percent: float
    put_target_basis: str
    call_target_basis: str
    put_finish_outside_probability: float | None
    call_finish_outside_probability: float | None
    put_reached_probability: float | None
    call_reached_probability: float | None
    average_low_percent_until_exit: float | None
    average_high_percent_until_exit: float | None
    initial_put_strike: float | None
    initial_call_strike: float | None
    final_put_strike: float | None
    final_call_strike: float | None
    liquidity_optimization_reason: str | None
    trade_score: TradeScore


class DecisionReportBuilder:

    def __init__(self, score_calculator: TradeScoreCalculator | None = None) -> None:
        self.score_calculator = score_calculator or TradeScoreCalculator()

    def build(self, candidate: EarningsCrushCandidate) -> DecisionReport | None:
        if (
            candidate.expected_move is None
            or candidate.snapshot is None
            or candidate.snapshot.quote is None
            or candidate.strike_selection is None
            or candidate.strike_selection_source is None
        ):
            return None

        price = candidate.snapshot.quote.price
        before = (
            candidate.strike_selection_before_liquidity
            or candidate.strike_selection
        )
        after = candidate.strike_selection
        expected_move_percent = candidate.expected_move.percent * 100

        used_put_target_percent = (before.put_target / price - 1) * 100
        used_call_target_percent = (before.call_target / price - 1) * 100

        historical = candidate.historical_selection_result
        if historical is None:
            score = self.score_calculator.calculate(
                expected_move_percent=expected_move_percent,
                used_put_target_percent=used_put_target_percent,
                used_call_target_percent=used_call_target_percent,
                put_reached_probability=None,
                call_reached_probability=None,
                put_finish_outside_probability=None,
                call_finish_outside_probability=None,
                historical_sample_size=None,
                liquidity=candidate.liquidity,
            )
            return DecisionReport(
                selection_source=candidate.strike_selection_source,
                expected_move_percent=expected_move_percent,
                iv_rank=(
                    candidate.option_data.iv_rank
                    if candidate.option_data
                    else None
                ),
                iv_percentile=(
                    candidate.option_data.iv_percentile
                    if candidate.option_data
                    else None
                ),
                historical_sample_size=None,
                exit_trading_day_index=None,
                historical_average_abs_close_move_percent=None,
                historical_median_abs_close_move_percent=None,
                historical_max_abs_close_move_percent=None,
                historical_put_target_percent=None,
                historical_call_target_percent=None,
                used_put_target_percent=used_put_target_percent,
                used_call_target_percent=used_call_target_percent,
                put_target_basis="Expected Move",
                call_target_basis="Expected Move",
                put_finish_outside_probability=None,
                call_finish_outside_probability=None,
                put_reached_probability=None,
                call_reached_probability=None,
                average_low_percent_until_exit=None,
                average_high_percent_until_exit=None,
                initial_put_strike=self._strike(before.put),
                initial_call_strike=self._strike(before.call),
                final_put_strike=self._strike(after.put),
                final_call_strike=self._strike(after.call),
                liquidity_optimization_reason=(
                    candidate.liquidity_optimization_reason
                ),
                trade_score=score,
            )

        call = historical.selection.call_recommendation
        put = historical.selection.put_recommendation
        if call is None or put is None or not historical.outcomes:
            return None

        absolute_close_moves = tuple(
            abs(outcome.exit_close_percent)
            for outcome in historical.outcomes
        )
        average_low = sum(
            outcome.lowest_percent_until_exit
            for outcome in historical.outcomes
        ) / len(historical.outcomes)
        average_high = sum(
            outcome.highest_percent_until_exit
            for outcome in historical.outcomes
        ) / len(historical.outcomes)

        score = self.score_calculator.calculate(
            expected_move_percent=expected_move_percent,
            used_put_target_percent=used_put_target_percent,
            used_call_target_percent=used_call_target_percent,
            put_reached_probability=put.reached_probability,
            call_reached_probability=call.reached_probability,
            put_finish_outside_probability=put.finish_outside_probability,
            call_finish_outside_probability=call.finish_outside_probability,
            historical_sample_size=call.observation_count,
            liquidity=candidate.liquidity,
        )

        return DecisionReport(
            selection_source=candidate.strike_selection_source,
            expected_move_percent=expected_move_percent,
            iv_rank=(
                candidate.option_data.iv_rank
                if candidate.option_data
                else None
            ),
            iv_percentile=(
                candidate.option_data.iv_percentile
                if candidate.option_data
                else None
            ),
            historical_sample_size=call.observation_count,
            exit_trading_day_index=call.exit_trading_day_index,
            historical_average_abs_close_move_percent=(
                sum(absolute_close_moves) / len(absolute_close_moves)
            ),
            historical_median_abs_close_move_percent=median(
                absolute_close_moves
            ),
            historical_max_abs_close_move_percent=max(
                absolute_close_moves
            ),
            historical_put_target_percent=(
                put.recommended_threshold_percent
            ),
            historical_call_target_percent=(
                call.recommended_threshold_percent
            ),
            used_put_target_percent=used_put_target_percent,
            used_call_target_percent=used_call_target_percent,
            put_target_basis=(
                "Historie"
                if abs(put.recommended_threshold_percent)
                > expected_move_percent
                else "Expected Move"
            ),
            call_target_basis=(
                "Historie"
                if call.recommended_threshold_percent
                > expected_move_percent
                else "Expected Move"
            ),
            put_finish_outside_probability=(
                put.finish_outside_probability
            ),
            call_finish_outside_probability=(
                call.finish_outside_probability
            ),
            put_reached_probability=put.reached_probability,
            call_reached_probability=call.reached_probability,
            average_low_percent_until_exit=average_low,
            average_high_percent_until_exit=average_high,
            initial_put_strike=self._strike(before.put),
            initial_call_strike=self._strike(before.call),
            final_put_strike=self._strike(after.put),
            final_call_strike=self._strike(after.call),
            liquidity_optimization_reason=(
                candidate.liquidity_optimization_reason
            ),
            trade_score=score,
        )

    @staticmethod
    def _strike(option) -> float | None:
        return option.strike if option is not None else None
