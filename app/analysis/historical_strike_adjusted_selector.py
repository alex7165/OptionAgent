from dataclasses import dataclass

from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelection,
)
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.analysis.strike_selector import StrikeSelector
from app.marketdata.models import ExpirationChain


@dataclass(frozen=True, slots=True)
class HistoricalStrikeAdjustment:
    expected_move_percent: float
    put_percent: float
    call_percent: float
    put_was_adjusted: bool
    call_was_adjusted: bool


@dataclass(frozen=True, slots=True)
class HistoricalStrikeAdjustedSelection:
    adjustment: HistoricalStrikeAdjustment
    strike_selection: StrikeSelection


class HistoricalStrikeAdjustedSelector:

    def __init__(
        self,
        strike_selector: StrikeSelector,
    ) -> None:
        self.strike_selector = strike_selector

    def select(
        self,
        chain: ExpirationChain,
        underlying_price: float,
        historical_selection: HistoricalStrikeSelection,
        strategy: Strategy = Strategy.IRON_CONDOR,
    ) -> HistoricalStrikeAdjustedSelection:
        adjustment = self._build_adjustment(
            historical_selection
        )

        strike_selection = (
            self.strike_selector
            .select_by_asymmetric_percent(
                chain=chain,
                underlying_price=underlying_price,
                put_percent=adjustment.put_percent,
                call_percent=adjustment.call_percent,
                strategy=strategy,
            )
        )

        return HistoricalStrikeAdjustedSelection(
            adjustment=adjustment,
            strike_selection=strike_selection,
        )

    @staticmethod
    def _build_adjustment(
        historical_selection: HistoricalStrikeSelection,
    ) -> HistoricalStrikeAdjustment:
        expected_move_percent = (
            historical_selection.expected_move_percent
        )

        if expected_move_percent <= 0:
            raise ValueError(
                "expected_move_percent must be greater than zero"
            )

        call_recommendation = (
            historical_selection.call_recommendation
        )
        put_recommendation = (
            historical_selection.put_recommendation
        )

        historical_call_percent = (
            call_recommendation.recommended_threshold_percent
            if call_recommendation is not None
            else expected_move_percent
        )
        historical_put_percent = abs(
            put_recommendation.recommended_threshold_percent
            if put_recommendation is not None
            else -expected_move_percent
        )

        if historical_call_percent <= 0:
            raise ValueError(
                "Call threshold must be greater than zero"
            )

        if historical_put_percent <= 0:
            raise ValueError(
                "Put threshold distance must be greater than zero"
            )

        call_percent = max(
            expected_move_percent,
            historical_call_percent,
        )
        put_percent = max(
            expected_move_percent,
            historical_put_percent,
        )

        return HistoricalStrikeAdjustment(
            expected_move_percent=expected_move_percent,
            put_percent=put_percent / 100,
            call_percent=call_percent / 100,
            put_was_adjusted=(
                put_recommendation is not None
                and historical_put_percent > expected_move_percent
            ),
            call_was_adjusted=(
                call_recommendation is not None
                and historical_call_percent > expected_move_percent
            ),
        )
