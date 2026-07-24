from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_outcome import ManagementActionOutcome


@dataclass(frozen=True, slots=True)
class CollectedManagementOutcomes:
    symbol: str
    decision_date: date
    threatened_side: ThreatenedSide
    outcomes: tuple[ManagementActionOutcome, ...]
    best_action: ManagementAction | None
    best_action_profit_loss: float | None
    incomplete_actions: tuple[ManagementAction, ...]


class ManagementOutcomeCollector:
    """Collect and label alternative management actions without false P/L.

    Only outcomes with complete total P/L participate in the best-action label.
    Actions for which only a stock leg or an underlying path is known remain in
    the collection and are exposed through ``incomplete_actions``.
    """

    def collect(
        self,
        *,
        symbol: str,
        decision_date: date,
        threatened_side: ThreatenedSide,
        outcomes: Iterable[ManagementActionOutcome],
    ) -> CollectedManagementOutcomes:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        collected = tuple(outcomes)
        if not collected:
            raise ValueError("outcomes must not be empty")

        seen_actions: set[ManagementAction] = set()
        for outcome in collected:
            if outcome.decision_date != decision_date:
                raise ValueError("all outcomes must use the same decision_date")
            if outcome.threatened_side is not threatened_side:
                raise ValueError("all outcomes must use the threatened_side")
            if outcome.action in seen_actions:
                raise ValueError(
                    f"duplicate outcome for action {outcome.action.value}"
                )
            seen_actions.add(outcome.action)

        complete = tuple(
            outcome for outcome in collected if outcome.complete_profit_loss
        )
        best = (
            max(
                complete,
                key=lambda outcome: (
                    outcome.total_profit_loss,
                    outcome.maximum_drawdown,
                    -outcome.capital_required,
                    outcome.action.value,
                ),
            )
            if complete
            else None
        )
        incomplete = tuple(
            outcome.action
            for outcome in collected
            if not outcome.complete_profit_loss
        )

        return CollectedManagementOutcomes(
            symbol=normalized_symbol,
            decision_date=decision_date,
            threatened_side=threatened_side,
            outcomes=collected,
            best_action=best.action if best else None,
            best_action_profit_loss=(best.total_profit_loss if best else None),
            incomplete_actions=incomplete,
        )
