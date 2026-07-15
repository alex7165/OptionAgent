from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from datetime import date

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionResult,
)
from app.analysis.liquidity_rating import LiquidityRating
from app.analysis.option_data import OptionData
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import EarningsEvent, MarketSnapshot

if TYPE_CHECKING:
    from app.analysis.decision_report import DecisionReport


@dataclass
class EarningsCrushCandidate:
    earnings_event: EarningsEvent
    snapshot: MarketSnapshot | None = None
    option_data: OptionData | None = None
    expected_move: ExpectedMove | None = None
    liquidity: LiquidityRating | None = None
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    strike_selection: StrikeSelection | None = None
    strike_selection_before_liquidity: StrikeSelection | None = None
    strike_selection_source: StrikeSelectionSource | None = None
    historical_selection_result: HistoricalStrikeSelectionResult | None = None
    liquidity_optimization_reason: str | None = None
    expiration: date | None = None
    decision_report: "DecisionReport | None" = None
