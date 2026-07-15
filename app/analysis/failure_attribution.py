from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.analysis.backtest_outcome_analyzer import BacktestOutcome
from app.analysis.decision_report import DecisionReport
from app.analysis.historical_strike_risk_analyzer import StrikeSide


class FailureSeverity(str, Enum):
    NONE = "none"
    CRITICAL = "critical"
    FAILURE = "failure"


class FailureCause(str, Enum):
    NONE = "none"
    EXIT_PATH_RISK = "exit_path_risk"
    CURRENT_MARKET_UNDERESTIMATED = "current_market_underestimated"
    HISTORICAL_TARGET_UNDERESTIMATED = "historical_target_underestimated"
    POSSIBLE_EXTREME_OUTLIER = "possible_extreme_outlier"
    STRIKE_DISTANCE_INSUFFICIENT = "strike_distance_insufficient"


@dataclass(frozen=True, slots=True)
class SideFailureAttribution:
    side: StrikeSide
    touched: bool
    finished_outside: bool
    actual_extreme_move_percent: float
    final_strike_distance_percent: float
    used_target_percent: float
    target_basis: str
    historical_target_percent: float | None
    distance_shortfall_percent: float


@dataclass(frozen=True, slots=True)
class FailureAttribution:
    severity: FailureSeverity
    primary_cause: FailureCause
    affected_sides: tuple[SideFailureAttribution, ...]
    expected_move_percent: float
    historical_max_abs_close_move_percent: float | None
    observations: tuple[str, ...]


class FailureAttributionAnalyzer:
    """Explain why an earnings trade became critical or failed.

    The result is an attribution based on the underlying path. It does not
    estimate option P&L or claim that one factor is the unique economic cause.
    """

    def analyze(
        self,
        report: DecisionReport,
        outcome: BacktestOutcome,
        reference_price: float,
    ) -> FailureAttribution:
        if reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")

        sides = self._affected_sides(
            report=report,
            outcome=outcome,
            reference_price=reference_price,
        )

        if not sides:
            return FailureAttribution(
                severity=FailureSeverity.NONE,
                primary_cause=FailureCause.NONE,
                affected_sides=(),
                expected_move_percent=report.expected_move_percent,
                historical_max_abs_close_move_percent=(
                    report.historical_max_abs_close_move_percent
                ),
                observations=(
                    "Kein Short-Strike wurde bis zum gewählten Exit berührt "
                    "oder verletzt.",
                ),
            )

        severity = (
            FailureSeverity.FAILURE
            if any(side.finished_outside for side in sides)
            else FailureSeverity.CRITICAL
        )
        primary_cause = self._primary_cause(report, sides, severity)

        return FailureAttribution(
            severity=severity,
            primary_cause=primary_cause,
            affected_sides=sides,
            expected_move_percent=report.expected_move_percent,
            historical_max_abs_close_move_percent=(
                report.historical_max_abs_close_move_percent
            ),
            observations=self._observations(
                report=report,
                sides=sides,
                severity=severity,
                primary_cause=primary_cause,
            ),
        )

    @staticmethod
    def _affected_sides(
        report: DecisionReport,
        outcome: BacktestOutcome,
        reference_price: float,
    ) -> tuple[SideFailureAttribution, ...]:
        affected: list[SideFailureAttribution] = []

        if outcome.put_touched or outcome.put_finished_outside:
            final_distance = (
                outcome.short_put_strike / reference_price - 1
            ) * 100
            actual_move = outcome.max_adverse_move_percent
            affected.append(
                SideFailureAttribution(
                    side=StrikeSide.PUT,
                    touched=outcome.put_touched,
                    finished_outside=outcome.put_finished_outside,
                    actual_extreme_move_percent=actual_move,
                    final_strike_distance_percent=final_distance,
                    used_target_percent=report.used_put_target_percent,
                    target_basis=report.put_target_basis,
                    historical_target_percent=(
                        report.historical_put_target_percent
                    ),
                    distance_shortfall_percent=round(
                        max(0.0, abs(actual_move) - abs(final_distance)),
                        6,
                    ),
                )
            )

        if outcome.call_touched or outcome.call_finished_outside:
            final_distance = (
                outcome.short_call_strike / reference_price - 1
            ) * 100
            actual_move = outcome.max_favorable_move_percent
            affected.append(
                SideFailureAttribution(
                    side=StrikeSide.CALL,
                    touched=outcome.call_touched,
                    finished_outside=outcome.call_finished_outside,
                    actual_extreme_move_percent=actual_move,
                    final_strike_distance_percent=final_distance,
                    used_target_percent=report.used_call_target_percent,
                    target_basis=report.call_target_basis,
                    historical_target_percent=(
                        report.historical_call_target_percent
                    ),
                    distance_shortfall_percent=round(
                        max(0.0, abs(actual_move) - abs(final_distance)),
                        6,
                    ),
                )
            )

        return tuple(affected)

    @staticmethod
    def _primary_cause(
        report: DecisionReport,
        sides: tuple[SideFailureAttribution, ...],
        severity: FailureSeverity,
    ) -> FailureCause:
        if severity is FailureSeverity.CRITICAL:
            return FailureCause.EXIT_PATH_RISK

        largest_move = max(
            abs(side.actual_extreme_move_percent) for side in sides
        )
        historical_max = report.historical_max_abs_close_move_percent
        if (
            historical_max is not None
            and largest_move > historical_max
            and largest_move > report.expected_move_percent
        ):
            return FailureCause.POSSIBLE_EXTREME_OUTLIER

        if any(
            side.target_basis == "Expected Move"
            and abs(side.actual_extreme_move_percent)
            > report.expected_move_percent
            for side in sides
        ):
            return FailureCause.CURRENT_MARKET_UNDERESTIMATED

        if any(
            side.target_basis == "Historie"
            and side.historical_target_percent is not None
            and abs(side.actual_extreme_move_percent)
            > abs(side.historical_target_percent)
            for side in sides
        ):
            return FailureCause.HISTORICAL_TARGET_UNDERESTIMATED

        return FailureCause.STRIKE_DISTANCE_INSUFFICIENT

    @staticmethod
    def _observations(
        report: DecisionReport,
        sides: tuple[SideFailureAttribution, ...],
        severity: FailureSeverity,
        primary_cause: FailureCause,
    ) -> tuple[str, ...]:
        observations: list[str] = []

        for side in sides:
            label = "Put" if side.side is StrikeSide.PUT else "Call"
            state = "am Exit verletzt" if side.finished_outside else "berührt"
            observations.append(
                f"{label}-Seite {state}: tatsächliche Extrembewegung "
                f"{side.actual_extreme_move_percent:.2f} %, finaler "
                f"Strike-Abstand {side.final_strike_distance_percent:.2f} %."
            )

        if primary_cause is FailureCause.EXIT_PATH_RISK:
            observations.append(
                "Der Trade schloss innerhalb der Short-Strikes; das Problem "
                "war der zwischenzeitliche Kursweg, nicht der Exit-Schlusskurs."
            )
        elif primary_cause is FailureCause.CURRENT_MARKET_UNDERESTIMATED:
            observations.append(
                "Der aktuelle Expected Move war für die beobachtete "
                "Bewegung zu klein."
            )
        elif primary_cause is FailureCause.HISTORICAL_TARGET_UNDERESTIMATED:
            observations.append(
                "Das historisch maßgebliche Ziel war für die beobachtete "
                "Bewegung zu eng."
            )
        elif primary_cause is FailureCause.POSSIBLE_EXTREME_OUTLIER:
            observations.append(
                "Die Extrembewegung lag sowohl über dem aktuellen Expected "
                "Move als auch über der größten historischen Schlussbewegung."
            )
            observations.append(
                "Der Ausreißerhinweis ist vorsichtig zu interpretieren, weil "
                "eine Intraday-Extrembewegung mit historischen Schlusskursen "
                "verglichen wird."
            )
        elif primary_cause is FailureCause.STRIKE_DISTANCE_INSUFFICIENT:
            observations.append(
                "Der endgültige Strike-Abstand reichte für die beobachtete "
                "Bewegung nicht aus, ohne dass Expected Move oder Historie "
                "eindeutig als alleinige Ursache identifiziert werden können."
            )

        if severity is FailureSeverity.FAILURE:
            observations.append(
                "Mindestens ein Short-Strike lag am gewählten Exit außerhalb."
            )

        return tuple(observations)
