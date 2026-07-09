from dataclasses import dataclass

from app.analysis.expected_move import ExpectedMove
from app.marketdata.models import ExpirationChain, OptionQuote


@dataclass
class OptionData:
    chain: ExpirationChain | None = None
    put: OptionQuote | None = None
    call: OptionQuote | None = None
    expected_move: ExpectedMove | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None