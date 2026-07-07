from dataclasses import dataclass

from app.marketdata.models import OptionChain


@dataclass
class OptionData:
    chain: OptionChain | None = None
    expected_move: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None