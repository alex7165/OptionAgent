from __future__ import annotations

from collections.abc import Sequence

from app.analysis.management_outcome import ManagementOutcome


class BestManagementStrategySelector:
    """Selects the strongest scored outcome for one historical case."""

    def select_best(
        self,
        outcomes: Sequence[ManagementOutcome],
    ) -> ManagementOutcome:
        if not outcomes:
            raise ValueError("outcomes must not be empty")

        unscored_strategies = [
            outcome.strategy_name
            for outcome in outcomes
            if outcome.score is None
        ]
        if unscored_strategies:
            names = ", ".join(unscored_strategies)
            raise ValueError(f"all outcomes must be scored: {names}")

        return max(
            outcomes,
            key=lambda outcome: (
                outcome.score.overall_score,
                -outcome.score.risk_score,
                -outcome.exit_day,
            ),
        )
