from __future__ import annotations

from collections.abc import Mapping

from app.analysis.management_action import ManagementAction
from app.analysis.management_action_training_dataset import (
    ManagementActionTrainingDataset,
)
from app.analysis.management_action_training_example import (
    ManagementActionTrainingExample,
)
from app.analysis.management_decision_context import ManagementDecisionContext
from app.analysis.management_outcome_collector import CollectedManagementOutcomes


class ManagementActionTrainingDatasetBuilder:
    """Convert collected alternatives into action-specific training rows."""

    def build(
        self,
        collected: CollectedManagementOutcomes,
        contexts: Mapping[ManagementAction, ManagementDecisionContext],
    ) -> ManagementActionTrainingDataset:
        rows: list[ManagementActionTrainingExample] = []

        for outcome in collected.outcomes:
            try:
                context = contexts[outcome.action]
            except KeyError as exc:
                raise ValueError(
                    f"missing decision context for action {outcome.action.value}"
                ) from exc

            if context.action is not outcome.action:
                raise ValueError("context action must match outcome action")
            if context.decision_date != collected.decision_date:
                raise ValueError("context decision_date must match collection")
            if context.threatened_side is not collected.threatened_side:
                raise ValueError("context threatened_side must match collection")

            strike_distance_percent = (
                (context.underlying_price / context.short_strike) - 1.0
            ) * 100.0

            is_best_action: bool | None
            if outcome.complete_profit_loss:
                is_best_action = outcome.action is collected.best_action
            else:
                is_best_action = None

            rows.append(
                ManagementActionTrainingExample(
                    symbol=collected.symbol,
                    decision_date=collected.decision_date,
                    threatened_side=collected.threatened_side,
                    action=outcome.action,
                    trading_day_index=context.trading_day_index,
                    underlying_price=context.underlying_price,
                    short_strike=context.short_strike,
                    strike_distance_percent=strike_distance_percent,
                    days_to_expiration=context.days_to_expiration,
                    short_option_delta=context.short_option_delta,
                    expected_move_percent=context.expected_move_percent,
                    iv_rank=context.iv_rank,
                    iv_percentile=context.iv_percentile,
                    entry_strategy=context.entry_strategy,
                    capital_required=outcome.capital_required,
                    maximum_drawdown=outcome.maximum_drawdown,
                    total_profit_loss=outcome.total_profit_loss,
                    complete_profit_loss=outcome.complete_profit_loss,
                    is_best_action=is_best_action,
                )
            )

        return ManagementActionTrainingDataset(examples=tuple(rows))
