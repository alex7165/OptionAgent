from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.analysis.failure_attribution import (
    FailureAttribution,
    FailureCause,
    FailureSeverity,
)
from app.analysis.historical_strike_risk_analyzer import StrikeSide
from app.analysis.trade_review import TradeReview


class PolicyRecommendationType(str, Enum):
    NO_CHANGE = "no_change"
    WIDEN_PUT_DISTANCE = "widen_put_distance"
    WIDEN_CALL_DISTANCE = "widen_call_distance"
    EXIT_EARLIER = "exit_earlier"
    REVIEW_OUTLIER_HANDLING = "review_outlier_handling"


@dataclass(frozen=True, slots=True)
class PolicyRecommendation:
    recommendation_type: PolicyRecommendationType
    confidence: float
    affected_observations: int
    total_observations: int
    suggested_change_percent: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PolicyRecommendationReport:
    observation_count: int
    recommendations: tuple[PolicyRecommendation, ...]


class PolicyRecommendationAnalyzer:
    """Recommend policy changes from repeated observed patterns.

    The analyzer never mutates a policy. It only emits transparent suggestions
    when a minimum number of observations and a minimum pattern rate are met.
    """

    def __init__(
        self,
        minimum_observations: int = 8,
        side_failure_rate_threshold: float = 0.20,
        earlier_exit_rate_threshold: float = 0.35,
        outlier_rate_threshold: float = 0.20,
        distance_buffer_percent: float = 0.5,
    ) -> None:
        if minimum_observations <= 0:
            raise ValueError("minimum_observations must be greater than zero")
        for name, value in (
            ("side_failure_rate_threshold", side_failure_rate_threshold),
            ("earlier_exit_rate_threshold", earlier_exit_rate_threshold),
            ("outlier_rate_threshold", outlier_rate_threshold),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")
        if distance_buffer_percent <= 0:
            raise ValueError("distance_buffer_percent must be greater than zero")

        self.minimum_observations = minimum_observations
        self.side_failure_rate_threshold = side_failure_rate_threshold
        self.earlier_exit_rate_threshold = earlier_exit_rate_threshold
        self.outlier_rate_threshold = outlier_rate_threshold
        self.distance_buffer_percent = distance_buffer_percent

    def analyze(
        self,
        attributions: tuple[FailureAttribution, ...],
        reviews: tuple[TradeReview, ...],
    ) -> PolicyRecommendationReport:
        if len(attributions) != len(reviews):
            raise ValueError("attributions and reviews must have equal length")
        if not attributions:
            raise ValueError("attributions and reviews must not be empty")

        count = len(attributions)
        if count < self.minimum_observations:
            return PolicyRecommendationReport(
                observation_count=count,
                recommendations=(
                    PolicyRecommendation(
                        recommendation_type=PolicyRecommendationType.NO_CHANGE,
                        confidence=count / self.minimum_observations,
                        affected_observations=0,
                        total_observations=count,
                        suggested_change_percent=None,
                        reasons=(
                            "Keine Policy-Änderung empfohlen: Die Stichprobe ist "
                            f"mit {count} Beobachtungen kleiner als das Minimum "
                            f"von {self.minimum_observations}.",
                        ),
                    ),
                ),
            )

        recommendations: list[PolicyRecommendation] = []
        recommendations.extend(
            self._side_recommendations(attributions, count)
        )

        earlier_safe_count = sum(
            self._has_earlier_safe_exit(review) for review in reviews
        )
        earlier_safe_rate = earlier_safe_count / count
        if earlier_safe_rate >= self.earlier_exit_rate_threshold:
            recommendations.append(
                PolicyRecommendation(
                    recommendation_type=PolicyRecommendationType.EXIT_EARLIER,
                    confidence=earlier_safe_rate,
                    affected_observations=earlier_safe_count,
                    total_observations=count,
                    suggested_change_percent=None,
                    reasons=(
                        f"In {earlier_safe_count} von {count} Fällen "
                        "war ein früherer Exit bereits innerhalb beider "
                        "Short-Strikes und ohne Touch möglich.",
                        "Die flexible Exit-Policy sollte frühere sichere "
                        "Ausstiege stärker gewichten.",
                    ),
                )
            )

        outlier_count = sum(
            attribution.primary_cause
            is FailureCause.POSSIBLE_EXTREME_OUTLIER
            for attribution in attributions
        )
        outlier_rate = outlier_count / count
        if outlier_rate >= self.outlier_rate_threshold:
            recommendations.append(
                PolicyRecommendation(
                    recommendation_type=(
                        PolicyRecommendationType.REVIEW_OUTLIER_HANDLING
                    ),
                    confidence=outlier_rate,
                    affected_observations=outlier_count,
                    total_observations=count,
                    suggested_change_percent=None,
                    reasons=(
                        f"{outlier_count} von {count} Fällen wurden als "
                        "mögliche außergewöhnliche Ausreißer eingeordnet.",
                        "Vor pauschal größeren Strike-Abständen sollte geprüft "
                        "werden, ob ein separates Ausreißer- oder Event-Regime "
                        "sinnvoll ist.",
                    ),
                )
            )

        if not recommendations:
            recommendations.append(
                PolicyRecommendation(
                    recommendation_type=PolicyRecommendationType.NO_CHANGE,
                    confidence=1.0,
                    affected_observations=0,
                    total_observations=count,
                    suggested_change_percent=None,
                    reasons=(
                        "Keine wiederkehrende Fehlerursache überschreitet die "
                        "konfigurierten Schwellenwerte.",
                    ),
                )
            )

        return PolicyRecommendationReport(
            observation_count=count,
            recommendations=tuple(recommendations),
        )

    def _side_recommendations(
        self,
        attributions: tuple[FailureAttribution, ...],
        count: int,
    ) -> tuple[PolicyRecommendation, ...]:
        recommendations: list[PolicyRecommendation] = []

        for side, recommendation_type, label in (
            (
                StrikeSide.PUT,
                PolicyRecommendationType.WIDEN_PUT_DISTANCE,
                "Put",
            ),
            (
                StrikeSide.CALL,
                PolicyRecommendationType.WIDEN_CALL_DISTANCE,
                "Call",
            ),
        ):
            affected = [
                side_attribution
                for attribution in attributions
                if attribution.severity is FailureSeverity.FAILURE
                and attribution.primary_cause
                in {
                    FailureCause.CURRENT_MARKET_UNDERESTIMATED,
                    FailureCause.HISTORICAL_TARGET_UNDERESTIMATED,
                    FailureCause.STRIKE_DISTANCE_INSUFFICIENT,
                }
                for side_attribution in attribution.affected_sides
                if side_attribution.side is side
                and side_attribution.finished_outside
            ]
            rate = len(affected) / count
            if rate < self.side_failure_rate_threshold:
                continue

            average_shortfall = (
                sum(item.distance_shortfall_percent for item in affected)
                / len(affected)
            )
            suggested_change = max(
                self.distance_buffer_percent,
                round(average_shortfall, 2),
            )
            recommendations.append(
                PolicyRecommendation(
                    recommendation_type=recommendation_type,
                    confidence=rate,
                    affected_observations=len(affected),
                    total_observations=count,
                    suggested_change_percent=suggested_change,
                    reasons=(
                        f"Die {label}-Seite schloss in {len(affected)} von "
                        f"{count} Fällen außerhalb des Short-Strikes.",
                        f"Der durchschnittlich fehlende Abstand betrug "
                        f"{average_shortfall:.2f} Prozentpunkte.",
                        f"Empfohlen wird zunächst ein zusätzlicher "
                        f"Sicherheitsabstand von {suggested_change:.2f} "
                        "Prozentpunkten zur manuellen Prüfung.",
                    ),
                )
            )

        return tuple(recommendations)

    @staticmethod
    def _has_earlier_safe_exit(review: TradeReview) -> bool:
        selected_day = review.selected_exit.trading_day_index
        return any(
            alternative.trading_day_index < selected_day
            and alternative.finished_inside_short_strikes
            and not alternative.put_touched
            and not alternative.call_touched
            for alternative in review.alternative_exits
        )
