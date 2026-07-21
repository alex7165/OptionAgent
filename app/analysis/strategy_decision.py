from dataclasses import dataclass

from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionResult,
)
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection


@dataclass(frozen=True, slots=True)
class StrategyDecisionPolicy:
    extreme_move_threshold_percent: float = 30.0
    minimum_iron_condor_credit_retention: float = 0.50

    def __post_init__(self) -> None:
        if self.extreme_move_threshold_percent <= 0:
            raise ValueError(
                "extreme_move_threshold_percent must be greater than zero"
            )
        if not 0 <= self.minimum_iron_condor_credit_retention <= 1:
            raise ValueError(
                "minimum_iron_condor_credit_retention must be between 0 and 1"
            )


class StrategyDecisionService:
    def __init__(
        self,
        policy: StrategyDecisionPolicy | None = None,
    ) -> None:
        self.policy = policy or StrategyDecisionPolicy()

    def select(
        self,
        short_strangle: StrikeSelection,
        iron_condor: StrikeSelection,
        historical_result: HistoricalStrikeSelectionResult | None,
    ) -> Strategy:
        if historical_result is None or not historical_result.outcomes:
            return Strategy.SHORT_STRANGLE

        maximum_move = max(
            max(
                abs(outcome.highest_percent_until_exit),
                abs(outcome.lowest_percent_until_exit),
            )
            for outcome in historical_result.outcomes
        )
        if maximum_move < self.policy.extreme_move_threshold_percent:
            return Strategy.SHORT_STRANGLE

        strangle_credit = self._short_credit(short_strangle)
        condor_credit = self._iron_condor_credit(iron_condor)
        if (
            strangle_credit is None
            or strangle_credit <= 0
            or condor_credit is None
            or condor_credit <= 0
        ):
            return Strategy.SHORT_STRANGLE

        retention = condor_credit / strangle_credit
        if retention >= self.policy.minimum_iron_condor_credit_retention:
            return Strategy.IRON_CONDOR

        return Strategy.SHORT_STRANGLE

    @staticmethod
    def _short_credit(selection: StrikeSelection) -> float | None:
        if selection.put is None or selection.call is None:
            return None
        if selection.put.bid is None or selection.call.bid is None:
            return None
        return selection.put.bid + selection.call.bid

    @classmethod
    def _iron_condor_credit(
        cls,
        selection: StrikeSelection,
    ) -> float | None:
        short_credit = cls._short_credit(selection)
        if short_credit is None:
            return None
        if selection.long_put is None or selection.long_call is None:
            return None
        if selection.long_put.ask is None or selection.long_call.ask is None:
            return None
        return short_credit - selection.long_put.ask - selection.long_call.ask
