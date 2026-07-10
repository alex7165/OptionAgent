from app.analysis.historical_earnings_moves import (
    HistoricalEarningsMove,
    HistoricalEarningsMoves,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


class HistoricalEarningsMoveAnalyzer:

    def analyze(
        self,
        move_percents: list[float],
    ) -> HistoricalEarningsMoves:
        return HistoricalEarningsMoves(
            moves=tuple(
                HistoricalEarningsMove(move_percent=move)
                for move in move_percents
            )
        )

    def analyze_reactions(
        self,
        reactions: tuple[HistoricalEarningsReaction, ...],
    ) -> HistoricalEarningsMoves:
        first_day_moves = [
            earnings.reactions[0].price_change_percent
            for earnings in reactions
            if earnings.reactions
        ]

        return self.analyze(first_day_moves)