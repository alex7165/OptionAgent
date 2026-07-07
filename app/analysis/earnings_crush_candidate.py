from dataclasses import dataclass, field

from app.marketdata.models import EarningsEvent, MarketSnapshot, OptionChain


@dataclass
class EarningsCrushCandidate:
    earnings_event: EarningsEvent
    snapshot: MarketSnapshot | None = None
    option_chain: OptionChain | None = None
    expected_move: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None
    historical_moves: list[float] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)