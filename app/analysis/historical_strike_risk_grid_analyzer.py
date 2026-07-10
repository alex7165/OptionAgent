from dataclasses import dataclass

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRisk,
    HistoricalStrikeRiskAnalyzer,
    StrikeSide,
)


@dataclass(frozen=True, slots=True)
class HistoricalStrikeRiskGrid:
    call_risks: tuple[HistoricalStrikeRisk, ...]
    put_risks: tuple[HistoricalStrikeRisk, ...]


class HistoricalStrikeRiskGridAnalyzer:

    def __init__(
        self,
        strike_risk_analyzer: HistoricalStrikeRiskAnalyzer,
    ) -> None:
        self.strike_risk_analyzer = strike_risk_analyzer

    def analyze(
        self,
        outcomes: tuple[HistoricalOutcome, ...],
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
    ) -> HistoricalStrikeRiskGrid:
        if not outcomes:
            raise ValueError(
                "outcomes must not be empty"
            )

        self._validate_unique_thresholds(
            thresholds=call_thresholds,
            side=StrikeSide.CALL,
        )
        self._validate_unique_thresholds(
            thresholds=put_thresholds,
            side=StrikeSide.PUT,
        )

        ordered_call_thresholds = tuple(
            sorted(call_thresholds)
        )
        ordered_put_thresholds = tuple(
            sorted(
                put_thresholds,
                reverse=True,
            )
        )

        call_risks = tuple(
            self.strike_risk_analyzer.analyze(
                outcomes=outcomes,
                side=StrikeSide.CALL,
                threshold_percent=threshold,
            )
            for threshold in ordered_call_thresholds
        )

        put_risks = tuple(
            self.strike_risk_analyzer.analyze(
                outcomes=outcomes,
                side=StrikeSide.PUT,
                threshold_percent=threshold,
            )
            for threshold in ordered_put_thresholds
        )

        return HistoricalStrikeRiskGrid(
            call_risks=call_risks,
            put_risks=put_risks,
        )

    @staticmethod
    def _validate_unique_thresholds(
        thresholds: tuple[float, ...],
        side: StrikeSide,
    ) -> None:
        if len(set(thresholds)) != len(thresholds):
            raise ValueError(
                f"{side.value} thresholds must be unique"
            )