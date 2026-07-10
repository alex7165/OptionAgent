from dataclasses import dataclass
from datetime import date

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcome:
    exit_trading_day_index: int
    exit_date: date
    exit_close_percent: float
    highest_percent_until_exit: float
    lowest_percent_until_exit: float
    trading_days_observed: int


class HistoricalOutcomeAnalyzer:

    def analyze(
        self,
        price_analysis: HistoricalEarningsPriceAnalysis,
        exit_trading_day_index: int,
    ) -> HistoricalOutcome:
        if exit_trading_day_index < 1:
            raise ValueError(
                "exit_trading_day_index must be at least 1"
            )

        if not price_analysis.daily_moves:
            raise ValueError(
                "price_analysis must contain daily moves"
            )

        selected_moves = tuple(
            move
            for move in price_analysis.daily_moves
            if move.trading_day_index
            <= exit_trading_day_index
        )

        exit_moves = tuple(
            move
            for move in selected_moves
            if move.trading_day_index
            == exit_trading_day_index
        )

        if not exit_moves:
            raise ValueError(
                "No daily move found for exit trading day "
                f"{exit_trading_day_index}"
            )

        if len(exit_moves) > 1:
            raise ValueError(
                "Multiple daily moves found for exit trading day "
                f"{exit_trading_day_index}"
            )

        exit_move = exit_moves[0]

        return HistoricalOutcome(
            exit_trading_day_index=exit_trading_day_index,
            exit_date=exit_move.date,
            exit_close_percent=exit_move.close_percent,
            highest_percent_until_exit=max(
                move.high_percent
                for move in selected_moves
            ),
            lowest_percent_until_exit=min(
                move.low_percent
                for move in selected_moves
            ),
            trading_days_observed=len(selected_moves),
        )