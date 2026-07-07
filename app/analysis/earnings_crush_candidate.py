from dataclasses import dataclass, field

from app.analysis.option_data import OptionData
from app.marketdata.models import EarningsEvent, MarketSnapshot


@dataclass
class EarningsCrushCandidate:
    earnings_event: EarningsEvent
    snapshot: MarketSnapshot | None = None
    option_data: OptionData | None = None
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)