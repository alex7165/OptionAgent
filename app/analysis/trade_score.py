from __future__ import annotations

from dataclasses import dataclass

from app.analysis.liquidity_rating import LiquidityRating


@dataclass(frozen=True, slots=True)
class TradeScore:
    total: int
    market_component: float
    historical_risk_component: float
    historical_sample_component: float
    liquidity_component: float


class TradeScoreCalculator:
    """Calculate a transparent 0-100 quality score without ranking trades."""

    MARKET_WEIGHT = 35.0
    HISTORICAL_RISK_WEIGHT = 25.0
    HISTORICAL_SAMPLE_WEIGHT = 10.0
    LIQUIDITY_WEIGHT = 30.0
    FULL_SAMPLE_SIZE = 40
    MAX_MARKET_CUSHION_RATIO = 1.25

    def calculate(
        self,
        *,
        expected_move_percent: float,
        used_put_target_percent: float,
        used_call_target_percent: float,
        put_reached_probability: float | None,
        call_reached_probability: float | None,
        put_finish_outside_probability: float | None,
        call_finish_outside_probability: float | None,
        historical_sample_size: int | None,
        liquidity: LiquidityRating | None,
    ) -> TradeScore:
        market_component = self._market_component(
            expected_move_percent=expected_move_percent,
            used_put_target_percent=used_put_target_percent,
            used_call_target_percent=used_call_target_percent,
        )
        historical_risk_component = self._historical_risk_component(
            put_reached_probability=put_reached_probability,
            call_reached_probability=call_reached_probability,
            put_finish_outside_probability=put_finish_outside_probability,
            call_finish_outside_probability=call_finish_outside_probability,
        )
        historical_sample_component = self._historical_sample_component(
            historical_sample_size
        )
        liquidity_component = self._liquidity_component(liquidity)

        total = round(
            market_component
            + historical_risk_component
            + historical_sample_component
            + liquidity_component
        )
        return TradeScore(
            total=max(0, min(100, total)),
            market_component=market_component,
            historical_risk_component=historical_risk_component,
            historical_sample_component=historical_sample_component,
            liquidity_component=liquidity_component,
        )

    def _market_component(
        self,
        *,
        expected_move_percent: float,
        used_put_target_percent: float,
        used_call_target_percent: float,
    ) -> float:
        if expected_move_percent <= 0:
            return 0.0

        put_ratio = abs(used_put_target_percent) / expected_move_percent
        call_ratio = abs(used_call_target_percent) / expected_move_percent
        average_ratio = (put_ratio + call_ratio) / 2
        normalized = min(average_ratio, self.MAX_MARKET_CUSHION_RATIO)
        return (
            normalized
            / self.MAX_MARKET_CUSHION_RATIO
            * self.MARKET_WEIGHT
        )

    def _historical_risk_component(
        self,
        *,
        put_reached_probability: float | None,
        call_reached_probability: float | None,
        put_finish_outside_probability: float | None,
        call_finish_outside_probability: float | None,
    ) -> float:
        probabilities = (
            put_reached_probability,
            call_reached_probability,
            put_finish_outside_probability,
            call_finish_outside_probability,
        )
        if any(value is None for value in probabilities):
            return 0.0

        put_risk = max(
            put_reached_probability or 0.0,
            put_finish_outside_probability or 0.0,
        )
        call_risk = max(
            call_reached_probability or 0.0,
            call_finish_outside_probability or 0.0,
        )
        average_risk = min(1.0, (put_risk + call_risk) / 2)
        return (1.0 - average_risk) * self.HISTORICAL_RISK_WEIGHT

    def _historical_sample_component(
        self,
        historical_sample_size: int | None,
    ) -> float:
        if historical_sample_size is None or historical_sample_size <= 0:
            return 0.0
        return (
            min(historical_sample_size / self.FULL_SAMPLE_SIZE, 1.0)
            * self.HISTORICAL_SAMPLE_WEIGHT
        )

    def _liquidity_component(
        self,
        liquidity: LiquidityRating | None,
    ) -> float:
        if liquidity is None:
            return 0.0

        checks = (
            getattr(liquidity, "has_good_spread", False),
            getattr(liquidity, "has_good_open_interest", False),
            getattr(liquidity, "has_good_volume", False),
        )
        points_per_check = self.LIQUIDITY_WEIGHT / 3
        return sum(
            points_per_check
            for passed in checks
            if passed
        )
